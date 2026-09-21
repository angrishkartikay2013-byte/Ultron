from __future__ import annotations

import json
import queue
import re
import threading
from array import array
from pathlib import Path

import sounddevice as sd
from piper import PiperVoice
from vosk import KaldiRecognizer, Model

VOICE_MODELS = [
    Path("voice_models") / "vosk-model-small-en-in-0.4",
    Path("voice_models") / "vosk-model-small-en-us-0.15",
]
PIPER_MODEL = Path("voice_models") / "piper" / "en_US-ryan-high.onnx"
DEVICE_FILE = Path("memory") / "audio_device.json"

VOICE_MODEL_PATH = next((path for path in VOICE_MODELS if path.exists()), None)
if VOICE_MODEL_PATH is None:
    raise FileNotFoundError("No Vosk model found in voice_models/.")
if not PIPER_MODEL.exists():
    raise FileNotFoundError(f"Piper voice not found at {PIPER_MODEL}. Run: uv run scripts/setup_piper_voice.py")

recognition_model = Model(str(VOICE_MODEL_PATH))
speech_model = PiperVoice.load(str(PIPER_MODEL))
audio_queue: queue.Queue[bytes] = queue.Queue()

def _callback(indata, frames, time_info, status) -> None:
    audio_queue.put(bytes(indata))

def list_microphones() -> list[tuple[int, str]]:
    devices = sd.query_devices()
    return [(index, str(info['name'])) for index, info in enumerate(devices) if info.get('max_input_channels', 0) > 0]

def get_saved_device() -> int | None:
    try:
        data = json.loads(DEVICE_FILE.read_text(encoding='utf-8'))
        value = data.get('device')
        return int(value) if value is not None else None
    except (FileNotFoundError, ValueError, TypeError, OSError):
        return None

def save_device(device: int) -> None:
    DEVICE_FILE.parent.mkdir(parents=True, exist_ok=True)
    DEVICE_FILE.write_text(json.dumps({'device': int(device)}, indent=2), encoding='utf-8')

def choose_microphone() -> int:
    saved = get_saved_device()
    available = dict(list_microphones())
    if saved in available:
        return saved
    print('\nULTRON microphone selection')
    for index, name in available.items():
        print(f'  [{index}] {name}')
    while True:
        try:
            selected = int(input('Select microphone number: ').strip())
        except ValueError:
            continue
        if selected in available:
            save_device(selected)
            return selected

def _adaptive_gain(data: bytes) -> bytes:
    samples = array('h')
    samples.frombytes(data)
    if not samples:
        return data
    rms = (sum(sample * sample for sample in samples) / len(samples)) ** 0.5
    if rms < 180:
        gain = 2.8
    elif rms < 500:
        gain = 2.0
    elif rms < 1100:
        gain = 1.35
    else:
        gain = 1.0
    if gain == 1.0:
        return data
    for i, sample in enumerate(samples):
        samples[i] = max(-32768, min(32767, int(sample * gain)))
    return samples.tobytes()

def listen_once(device: int | None = None, stop_event: threading.Event | None = None) -> str:
    selected = get_saved_device() if device is None else device
    if selected is None:
        selected = choose_microphone()
    info = sd.query_devices(selected, 'input')
    try:
        sd.check_input_settings(device=selected, samplerate=16000, channels=1, dtype='int16')
        sample_rate = 16000
    except Exception:
        sample_rate = int(info.get('default_samplerate', 16000))
    while not audio_queue.empty():
        try:
            audio_queue.get_nowait()
        except queue.Empty:
            break
    recognizer = KaldiRecognizer(recognition_model, sample_rate)
    recognizer.SetWords(True)
    with sd.RawInputStream(samplerate=sample_rate, blocksize=2048, dtype='int16', channels=1, callback=_callback, device=selected, latency='low'):
        while True:
            if stop_event and stop_event.is_set():
                return ''
            try:
                data = audio_queue.get(timeout=0.15)
            except queue.Empty:
                continue
            if recognizer.AcceptWaveform(_adaptive_gain(data)):
                text = json.loads(recognizer.Result()).get('text', '').strip()
                if text:
                    return text

def _speech_chunks(text: str) -> list[str]:
    clean = re.sub(r'```.*?```', ' ', text, flags=re.S)
    clean = re.sub(r'[#*_`>]', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    if not clean:
        return []
    return [chunk.strip() for chunk in re.split(r'(?<=[.!?])\s+', clean) if chunk.strip()]

_speech_lock = threading.Lock()

def speak(text: str, stop_event: threading.Event | None = None) -> None:
    chunks = _speech_chunks(text)
    if not chunks:
        return
    with _speech_lock:
        stream = sd.RawOutputStream(samplerate=speech_model.config.sample_rate, channels=1, dtype='int16', latency='low')
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