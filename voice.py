from __future__ import annotations

import json
import os
import queue
import re
import threading
import time
import wave
from collections import deque
from pathlib import Path

import numpy as np
import sounddevice as sd
from pywhispercpp.model import Model
from piper import PiperVoice

ROOT = Path(__file__).resolve().parent
WHISPER_DATA_DIR = ROOT / "voice_models" / "whispercpp_data"
WHISPER_MODELS_DIR = WHISPER_DATA_DIR / "models"

os.environ.setdefault("XDG_DATA_HOME", str(WHISPER_DATA_DIR))

# tiny.en is substantially lighter than base.en and is better suited to the i7-4770T.
WHISPER_MODEL_NAME = os.getenv("ULTRON_STT_MODEL", "tiny.en")
WHISPER_THREADS = max(2, min(4, os.cpu_count() or 4))
PIPER_MODEL = ROOT / "voice_models" / "piper" / "en_US-ryan-high.onnx"
DEVICE_FILE = ROOT / "memory" / "audio_device.json"
TEMP_DIR = ROOT / "memory" / "voice_temp"

if not PIPER_MODEL.exists():
    raise FileNotFoundError(
        f"Piper voice not found at {PIPER_MODEL}. Run: uv run scripts/setup_piper_voice.py"
    )

WHISPER_MODELS_DIR.mkdir(parents=True, exist_ok=True)
stt_model: Model | None = None
speech_model: PiperVoice | None = None
audio_queue: queue.Queue[np.ndarray] = queue.Queue()
_speech_lock = threading.Lock()


def load_voice_models() -> tuple[str, str]:
    """Load Whisper and Piper exactly once, on demand."""
    global stt_model, speech_model

    if stt_model is None:
        stt_model = Model(
            WHISPER_MODEL_NAME,
            models_dir=str(WHISPER_MODELS_DIR),
            print_progress=False,
            print_realtime=False,
            n_threads=WHISPER_THREADS,
        )

    if speech_model is None:
        speech_model = PiperVoice.load(str(PIPER_MODEL))

    return WHISPER_MODEL_NAME, PIPER_MODEL.name


def _callback(indata, frames, time_info, status) -> None:
    audio_queue.put(indata[:, 0].copy())


def list_microphones() -> list[tuple[int, str]]:
    devices = sd.query_devices()
    return [
        (index, str(info["name"]))
        for index, info in enumerate(devices)
        if info.get("max_input_channels", 0) > 0
    ]


def get_saved_device() -> int | None:
    try:
        data = json.loads(DEVICE_FILE.read_text(encoding="utf-8"))
        value = data.get("device")
        return int(value) if value is not None else None
    except (FileNotFoundError, ValueError, TypeError, OSError):
        return None


def save_device(device: int) -> None:
    DEVICE_FILE.parent.mkdir(parents=True, exist_ok=True)
    DEVICE_FILE.write_text(
        json.dumps({"device": int(device)}, indent=2),
        encoding="utf-8",
    )


def choose_microphone() -> int:
    saved = get_saved_device()
    available = dict(list_microphones())
    if saved in available:
        return saved

    print("\nULTRON microphone selection")
    for index, name in available.items():
        print(f"  [{index}] {name}")

    while True:
        try:
            selected = int(input("Select microphone number: ").strip())
        except ValueError:
            continue
        if selected in available:
            save_device(selected)
            return selected


def _write_wav(samples: np.ndarray, noise_floor: float = 0.0) -> Path:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    samples = np.asarray(samples, dtype=np.float32)
    samples = samples - float(np.mean(samples))
    if noise_floor > 0:
        # Gentle adaptive noise gate: reduce constant low-level room noise
        # without deleting the quiet parts of speech.
        gate = max(0.0012, min(0.01, noise_floor * 1.25))
        magnitude = np.abs(samples)
        soft = np.clip((magnitude - gate) / max(gate, 1e-5), 0.0, 1.0)
        gain = 0.18 + 0.82 * soft
        samples = samples * gain
    path = TEMP_DIR / f"utterance_{int(time.time() * 1000)}.wav"
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(pcm.tobytes())
    return path


def _transcribe(path: Path) -> str:
    if stt_model is None:
        load_voice_models()

    segments = stt_model.transcribe(
        str(path),
        language="en",
        print_progress=False,
        print_realtime=False,
        no_context=True,
    )
    parts = []
    for segment in segments:
        text = getattr(segment, "text", str(segment)).strip()
        if text:
            parts.append(text)
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def _noise_floor(chunks: list[np.ndarray]) -> float:
    if not chunks:
        return 0.005

    rms_values = [
        float(np.sqrt(np.mean(np.square(chunk))) + 1e-9)
        for chunk in chunks
    ]
    return float(np.median(rms_values))


def listen_once(
    device: int | None = None,
    stop_event: threading.Event | None = None,
) -> str:
    selected = get_saved_device() if device is None else device
    if selected is None:
        selected = choose_microphone()

    while not audio_queue.empty():
        try:
            audio_queue.get_nowait()
        except queue.Empty:
            break

    sample_rate = 16000
    silence_seconds = 0.72
    max_seconds = 10.0

    # Learn the room tone first so constant fan/AC/PC noise does not trigger
    # the microphone gate.
    calibration_seconds = 0.22
    calibration_samples = int(calibration_seconds * sample_rate)
    calibration_chunks: list[np.ndarray] = []
    calibration_total = 0

    started = False
    silence_started: float | None = None
    chunks: list[np.ndarray] = []
    pre_roll: deque[np.ndarray] = deque(maxlen=6)
    total_samples = 0
    voiced_chunks = 0

    with sd.InputStream(
        samplerate=sample_rate,
        blocksize=1024,
        channels=1,
        dtype="float32",
        callback=_callback,
        device=selected,
        latency="low",
    ):
        while calibration_total < calibration_samples:
            if stop_event and stop_event.is_set():
                return ""
            try:
                chunk = audio_queue.get(timeout=0.12)
            except queue.Empty:
                continue
            calibration_chunks.append(chunk)
            calibration_total += len(chunk)

        floor = _noise_floor(calibration_chunks)

        # Speech must rise well above the measured room floor.
        # The lower release threshold avoids chopping quiet words.
        onset_threshold = max(0.0032, floor * 1.55)
        release_threshold = max(0.0022, floor * 1.20)

        while True:
            if stop_event and stop_event.is_set():
                return ""

            try:
                chunk = audio_queue.get(timeout=0.12)
            except queue.Empty:
                continue

            rms = float(np.sqrt(np.mean(np.square(chunk))) + 1e-9)
            now = time.monotonic()

            if not started:
                pre_roll.append(chunk)

                # Require a brief sustained voice onset instead of one noisy
                # microphone block.
                if rms >= onset_threshold:
                    voiced_chunks += 1
                else:
                    voiced_chunks = 0

                if voiced_chunks >= 2:
                    started = True
                    chunks.extend(list(pre_roll))
                    total_samples += sum(len(item) for item in pre_roll)
                continue

            chunks.append(chunk)
            total_samples += len(chunk)

            if rms < release_threshold:
                if silence_started is None:
                    silence_started = now
                elif now - silence_started >= silence_seconds:
                    break
            else:
                silence_started = None

            if total_samples >= int(max_seconds * sample_rate):
                break

    if not chunks:
        return ""

    path = _write_wav(np.concatenate(chunks), noise_floor=floor)
    try:
        return _transcribe(path)
    finally:
        try:
            path.unlink()
        except OSError:
            pass

def _speech_chunks(text: str) -> list[str]:
    clean = re.sub(chr(96) * 3 + r".*?" + chr(96) * 3, " ", text, flags=re.S)
    clean = clean.replace(chr(96), "")
    clean = re.sub(r"[#*_>]", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    if not clean:
        return []
    return [
        chunk.strip()
        for chunk in re.split(r"(?<=[.!?])\s+", clean)
        if chunk.strip()
    ]


def speak(text: str, stop_event: threading.Event | None = None) -> None:
    chunks = _speech_chunks(text)
    if not chunks:
        return

    if speech_model is None:
        load_voice_models()

    with _speech_lock:
        stream = sd.RawOutputStream(
            samplerate=speech_model.config.sample_rate,
            channels=1,
            dtype="int16",
            latency="low",
        )
        stream.start()
        try:
            for chunk_text in chunks:
                if stop_event and stop_event.is_set():
                    break
                for audio in speech_model.synthesize(chunk_text):
                    if stop_event and stop_event.is_set():
                        break
                    stream.write(audio.audio_int16_bytes)
                if stop_event and stop_event.is_set():
                    break
        finally:
            stream.stop()
            stream.close()


def speak_streaming(
    incoming: queue.Queue[str | None],
    stop_event: threading.Event,
    started_callback=None,
) -> None:
    """Speak complete sentences as they arrive from the streaming LLM."""
    buffer = ""

    if speech_model is None:
        load_voice_models()

    def emit_sentence(sentence: str) -> None:
        clean = sentence.strip()
        if not clean or stop_event.is_set():
            return
        if started_callback is not None:
            started_callback()
        for audio in speech_model.synthesize(clean):
            if stop_event.is_set():
                return
            stream.write(audio.audio_int16_bytes)

    with _speech_lock:
        stream = sd.RawOutputStream(
            samplerate=speech_model.config.sample_rate,
            channels=1,
            dtype="int16",
            latency="low",
        )
        stream.start()
        try:
            while not stop_event.is_set():
                item = incoming.get()
                if item is None:
                    if buffer.strip():
                        emit_sentence(buffer)
                    break

                buffer += item

                while True:
                    match = re.search(r"(?<=[.!?])(?:\s+|$)|\n+", buffer)
                    if not match:
                        break
                    sentence = buffer[:match.end()]
                    buffer = buffer[match.end():]
                    emit_sentence(sentence)
                    if stop_event.is_set():
                        break

            # Leave a short real-audio tail in the device buffer so the final
            # phoneme is fully rendered before the output stream is closed.
            if not stop_event.is_set():
                tail_samples = max(1, int(speech_model.config.sample_rate * 0.12))
                stream.write(b"\x00\x00" * tail_samples)
        finally:
            stream.stop()
            stream.close()
