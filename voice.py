from __future__ import annotations

import base64
import json
import queue
import subprocess
import threading
from pathlib import Path

import sounddevice as sd
from vosk import KaldiRecognizer, Model

MODEL_PATH = Path("voice_models") / "vosk-model-small-en-us-0.15"
DEVICE_FILE = Path("memory") / "audio_device.json"

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Vosk model not found at {MODEL_PATH}. "
        "Download/extract vosk-model-small-en-us-0.15 there first."
    )

model = Model(str(MODEL_PATH))
audio_queue: queue.Queue[bytes] = queue.Queue()


def _callback(indata, frames, time_info, status) -> None:
    audio_queue.put(bytes(indata))


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
        raw = input("Select microphone number: ").strip()
        try:
            selected = int(raw)
        except ValueError:
            continue

        if selected in available:
            save_device(selected)
            return selected


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

    recognizer = KaldiRecognizer(model, 16000)

    with sd.RawInputStream(
        samplerate=16000,
        blocksize=4000,
        dtype="int16",
        channels=1,
        callback=_callback,
        device=selected,
    ):
        while True:
            if stop_event and stop_event.is_set():
                return ""

            try:
                data = audio_queue.get(timeout=0.15)
            except queue.Empty:
                continue

            if recognizer.AcceptWaveform(data):
                text = json.loads(recognizer.Result()).get("text", "").strip()
                if text:
                    return text


def speak(text: str, stop_event: threading.Event | None = None) -> None:
    """Speak using Windows PowerShell/System.Speech and support cancellation."""
    payload = base64.b64encode(text.encode("utf-8")).decode("ascii")
    script = (
        "$b=[Convert]::FromBase64String('"
        + payload
        + "');"
        "$t=[Text.Encoding]::UTF8.GetString($b);"
        "Add-Type -AssemblyName System.Speech;"
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$s.Rate=0;"
        "$s.Speak($t);"
        "$s.Dispose();"
    )

    process = subprocess.Popen(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    while process.poll() is None:
        if stop_event and stop_event.is_set():
            process.terminate()
            try:
                process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                process.kill()
            return
        try:
            process.wait(timeout=0.1)
        except subprocess.TimeoutExpired:
            pass
