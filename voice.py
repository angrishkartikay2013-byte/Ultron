from __future__ import annotations

import json
import os
import queue
import re
import threading
import time
import urllib.request
import wave
from collections import deque
from pathlib import Path

import numpy as np
import onnxruntime as ort
import sounddevice as sd
from faster_whisper import WhisperModel
from piper import PiperVoice

from debug import info, warning, exception

ROOT = Path(__file__).resolve().parent
WHISPER_DATA_DIR = ROOT / "voice_models" / "faster_whisper"
VAD_DATA_DIR = ROOT / "voice_models" / "silero_vad"
VAD_MODEL_PATH = VAD_DATA_DIR / "silero_vad.onnx"
VAD_MODEL_URL = (
    "https://raw.githubusercontent.com/snakers4/silero-vad/master/"
    "src/silero_vad/data/silero_vad.onnx"
)
WHISPER_MODEL_NAME = os.getenv("ULTRON_STT_MODEL", "base.en")
WHISPER_THREADS = max(2, min(4, os.cpu_count() or 4))
PIPER_MODEL = ROOT / "voice_models" / "piper" / "en_US-ryan-high.onnx"
DEVICE_FILE = ROOT / "memory" / "audio_device.json"
TEMP_DIR = ROOT / "memory" / "voice_temp"

if not PIPER_MODEL.exists():
    raise FileNotFoundError(
        f"Piper voice not found at {PIPER_MODEL}. Run: uv run scripts/setup_piper_voice.py"
    )

WHISPER_DATA_DIR.mkdir(parents=True, exist_ok=True)
VAD_DATA_DIR.mkdir(parents=True, exist_ok=True)

stt_model: WhisperModel | None = None
vad_model: "SileroOnnxVAD" | None = None
speech_model: PiperVoice | None = None
audio_queue: queue.Queue[np.ndarray] = queue.Queue()
_speech_lock = threading.Lock()


class SileroOnnxVAD:
    """Small streaming wrapper around the official Silero VAD ONNX model."""

    def __init__(self, model_path: Path) -> None:
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(model_path),
            providers=["CPUExecutionProvider"],
            sess_options=opts,
        )
        self.reset()

    def reset(self) -> None:
        self.state = np.zeros((2, 1, 128), dtype=np.float32)
        self.context = np.zeros((1, 64), dtype=np.float32)
        self.last_batch_size = 1

    def probability(self, chunk: np.ndarray) -> float:
        audio = np.asarray(chunk, dtype=np.float32)
        if audio.shape[0] != 512:
            raise ValueError(f"Silero VAD expects 512 samples, got {audio.shape[0]}")

        x = audio.reshape(1, -1)
        x = np.concatenate([self.context, x], axis=1)

        outputs = self.session.run(
            None,
            {
                "input": x,
                "state": self.state,
                "sr": np.array(16000, dtype=np.int64),
            },
        )
        output, self.state = outputs
        self.context = x[:, -64:]
        return float(np.asarray(output).reshape(-1)[0])


def _ensure_vad_model() -> None:
    if VAD_MODEL_PATH.exists() and VAD_MODEL_PATH.stat().st_size > 100_000:
        return

    info("Silero VAD model not found; downloading official ONNX model.")
    VAD_DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = VAD_MODEL_PATH.with_suffix(".download")
    try:
        urllib.request.urlretrieve(VAD_MODEL_URL, tmp)
        if tmp.stat().st_size < 100_000:
            raise RuntimeError("Downloaded Silero VAD model looks incomplete.")
        tmp.replace(VAD_MODEL_PATH)
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def load_voice_models() -> tuple[str, str]:
    """Load STT, VAD, and Piper exactly once, on demand."""
    global stt_model, vad_model, speech_model

    if vad_model is None:
        _ensure_vad_model()
        info("Loading Silero VAD ONNX")
        vad_model = SileroOnnxVAD(VAD_MODEL_PATH)

    if stt_model is None:
        info(
            f"Loading faster-whisper {WHISPER_MODEL_NAME!r} "
            f"(CPU INT8, threads={WHISPER_THREADS})"
        )
        stt_model = WhisperModel(
            WHISPER_MODEL_NAME,
            device="cpu",
            compute_type="int8",
            cpu_threads=WHISPER_THREADS,
            num_workers=1,
            download_root=str(WHISPER_DATA_DIR),
        )

    if speech_model is None:
        info(f"Loading Piper voice {PIPER_MODEL.name!r}")
        speech_model = PiperVoice.load(str(PIPER_MODEL))

    info(
        f"Voice models ready: STT={WHISPER_MODEL_NAME}, "
        f"VAD=Silero-ONNX, Piper={PIPER_MODEL.name}"
    )
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


def _write_wav(samples: np.ndarray) -> Path:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    samples = np.asarray(samples, dtype=np.float32)
    samples = samples - float(np.mean(samples))

    rms = float(np.sqrt(np.mean(np.square(samples))) + 1e-9)
    if rms < 0.045:
        gain = min(4.0, 0.045 / rms)
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

    segments, meta = stt_model.transcribe(
        str(path),
        language="en",
        beam_size=5,
        best_of=5,
        temperature=0.0,
        condition_on_previous_text=False,
        vad_filter=False,
        no_speech_threshold=0.60,
        compression_ratio_threshold=2.4,
        log_prob_threshold=-1.0,
    )

    parts: list[str] = []
    for segment in segments:
        text = segment.text.strip()
        if text:
            parts.append(text)

    transcript = re.sub(r"\s+", " ", " ".join(parts)).strip()
    if transcript.casefold() in {"[blank_audio]", "[blank audio]", "(blank audio)"}:
        info("STT produced a blank-audio marker; discarding it.")
        return ""

    if not transcript:
        info(
            "STT produced an empty transcript "
            f"(language={getattr(meta, 'language', 'unknown')!r})"
        )
    return transcript


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

    load_voice_models()
    assert vad_model is not None

    sample_rate = 16000
    block_size = 512
    max_seconds = 10.0
    min_voice_seconds = 0.12
    silence_seconds = 0.55
    onset_threshold = 0.55
    release_threshold = 0.32
    pre_roll_blocks = 8

    started = False
    quiet_blocks = 0
    voiced_blocks = 0
    silence_started: float | None = None
    chunks: list[np.ndarray] = []
    pre_roll: deque[np.ndarray] = deque(maxlen=pre_roll_blocks)
    total_samples = 0

    vad_model.reset()

    info(
        f"Microphone capture starting on device {selected} "
        f"(Silero threshold={onset_threshold:.2f}, release={release_threshold:.2f})"
    )

    with sd.InputStream(
        samplerate=sample_rate,
        blocksize=block_size,
        channels=1,
        dtype="float32",
        callback=_callback,
        device=selected,
        latency="low",
    ):
        while True:
            if stop_event and stop_event.is_set():
                return ""

            try:
                chunk = audio_queue.get(timeout=0.12)
            except queue.Empty:
                continue

            probability = vad_model.probability(chunk)
            now = time.monotonic()

            if not started:
                pre_roll.append(chunk)

                if probability >= onset_threshold:
                    voiced_blocks += 1
                else:
                    voiced_blocks = 0

                if voiced_blocks >= max(2, int(min_voice_seconds / 0.032)):
                    started = True
                    silence_started = None
                    info(
                        f"Voice onset detected: vad_probability={probability:.3f}"
                    )
                    chunks.extend(list(pre_roll))
                    total_samples += sum(len(item) for item in pre_roll)
                continue

            chunks.append(chunk)
            total_samples += len(chunk)

            if probability < release_threshold:
                quiet_blocks += 1
                if silence_started is None:
                    silence_started = now
                elif now - silence_started >= silence_seconds:
                    info(
                        f"Voice end detected: vad_probability={probability:.3f}, "
                        f"duration={total_samples / sample_rate:.2f}s"
                    )
                    break
            else:
                quiet_blocks = 0
                silence_started = None

            if total_samples >= int(max_seconds * sample_rate):
                info("Voice capture reached maximum utterance duration.")
                break

    minimum_samples = int(0.18 * sample_rate)
    if not chunks or total_samples < minimum_samples:
        info("Discarding capture that was too short to be useful.")
        return ""

    path = _write_wav(np.concatenate(chunks))
    try:
        transcript = _transcribe(path)
        info(f"STT transcript: {transcript!r}")
        return transcript
    except Exception:
        exception("Speech transcription failed")
        raise
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

    info(f"TTS starting: {text[:160]!r}")
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
            info("TTS finished")


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

            if not stop_event.is_set():
                tail_samples = max(1, int(speech_model.config.sample_rate * 0.12))
                stream.write(b"\x00\x00" * tail_samples)
        finally:
            stream.stop()
            stream.close()
