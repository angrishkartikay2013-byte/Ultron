from __future__ import annotations

import json
import queue
import re
import threading
from pathlib import Path

import sounddevice as sd
from moonshine_voice import (
    MicTranscriber,
    ModelArch,
    TranscriptEventListener,
    get_model_for_language,
)
from piper import PiperVoice

from debug import info, exception

ROOT = Path(__file__).resolve().parent
MOONSHINE_DATA_DIR = ROOT / "voice_models" / "moonshine_voice"
PIPER_MODEL = ROOT / "voice_models" / "piper" / "en_US-ryan-high.onnx"
DEVICE_FILE = ROOT / "memory" / "audio_device.json"

if not PIPER_MODEL.exists():
    raise FileNotFoundError(
        f"Piper voice not found at {PIPER_MODEL}. Run: uv run scripts/setup_piper_voice.py"
    )

MOONSHINE_MODEL_ARCH = ModelArch.SMALL_STREAMING

speech_model: PiperVoice | None = None
moonshine_model_path: Path | None = None
moonshine_model_arch: ModelArch | None = None
moonshine_mic: MicTranscriber | None = None
moonshine_device: int | None = None
_speech_lock = threading.Lock()


def list_microphones() -> list[tuple[int, str]]:
    devices = sd.query_devices()
    return [
        (index, str(device["name"]))
        for index, device in enumerate(devices)
        if device.get("max_input_channels", 0) > 0
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


def load_voice_models(device: int | None = None) -> tuple[str, str]:
    """Load Moonshine and Piper exactly once, on demand."""
    global speech_model
    global moonshine_model_path, moonshine_model_arch, moonshine_mic, moonshine_device

    selected_device = get_saved_device() if device is None else device
    if selected_device is None:
        selected_device = choose_microphone()

    if moonshine_mic is None or moonshine_device != selected_device:
        if moonshine_mic is not None:
            try:
                moonshine_mic.stop()
            except Exception:
                pass
            try:
                moonshine_mic.close()
            except Exception:
                pass

        info(
            "Loading Moonshine Voice small-streaming model "
            f"for microphone device {selected_device}"
        )
        moonshine_model_path, moonshine_model_arch = get_model_for_language(
            "en",
            wanted_model_arch=MOONSHINE_MODEL_ARCH,
            cache_root=MOONSHINE_DATA_DIR,
        )

        moonshine_mic = (
            MicTranscriber()
            .language("en")
            .model_arch(MOONSHINE_MODEL_ARCH)
            .device(selected_device)
            .update_interval(0.25)
        )
        moonshine_mic.load()
        moonshine_device = selected_device

    if speech_model is None:
        info(f"Loading Piper voice {PIPER_MODEL.name!r}")
        speech_model = PiperVoice.load(str(PIPER_MODEL))

    info(
        "Voice models ready: "
        "STT=Moonshine small-streaming, "
        f"device={moonshine_device}, Piper={PIPER_MODEL.name}"
    )
    return "moonshine-small-streaming", PIPER_MODEL.name


class _LineListener(TranscriptEventListener):
    def __init__(
        self,
        result_event: threading.Event,
        result_box: dict[str, str],
    ) -> None:
        self.result_event = result_event
        self.result_box = result_box

    def on_line_completed(self, event) -> None:
        text = re.sub(r"\s+", " ", (event.line.text or "")).strip()
        if not text:
            return

        self.result_box["text"] = text
        info(f"Moonshine transcript: {text!r}")
        self.result_event.set()

    def on_error(self, event) -> None:
        error = getattr(event, "error", event)
        exception(f"Moonshine voice error: {error}")


def listen_once(
    device: int | None = None,
    stop_event: threading.Event | None = None,
) -> str:
    selected = get_saved_device() if device is None else device
    if selected is None:
        selected = choose_microphone()

    load_voice_models(selected)
    assert moonshine_mic is not None

    result_event = threading.Event()
    result_box: dict[str, str] = {"text": ""}
    listener = _LineListener(result_event, result_box)

    moonshine_mic.remove_all_listeners()
    moonshine_mic.add_listener(listener)

    info(f"Moonshine microphone listening on device {selected}")

    try:
        moonshine_mic.start()

        while not result_event.wait(0.10):
            if stop_event and stop_event.is_set():
                moonshine_mic.stop()
                return ""

        # Give the recognizer a tiny amount of time to settle the final event
        # before the audio device is handed back to the rest of ULTRON.
        result_event.wait(0.05)
        moonshine_mic.stop()

        transcript = result_box["text"].strip()
        if transcript:
            info(f"Voice worker heard: {transcript!r}")
        return transcript
    except Exception:
        exception("Moonshine microphone capture failed")
        try:
            moonshine_mic.stop()
        except Exception:
            pass
        raise
    finally:
        moonshine_mic.remove_all_listeners()


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
