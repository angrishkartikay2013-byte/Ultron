from __future__ import annotations

import json
import queue
import re
import threading
from array import array
from pathlib import Path

import pyttsx3
import sounddevice as sd
from vosk import KaldiRecognizer, Model

VOICE_MODELS = [
    Path("voice_models") / "vosk-model-small-en-in-0.4",
    Path("voice_models") / "vosk-model-small-en-us-0.15",
]
DEVICE_FILE = Path("memory") / "audio_device.json"

MODEL_PATH = next((path for path in VOICE_MODELS if path.exists()), None)
if MODEL_PATH is None:
    raise FileNotFoundError("No Vosk model found in voice_models/.")

model = Model(str(MODEL_PATH))
audio_queue: queue.Queue[bytes] = queue.Queue()

def _callback(indata, frames, time_info, status) -> None:
    audio_queue.put(bytes(indata))

def list_microphones() -> list[tuple[int, str]]:
    devices = sd.query_devices()
    return [(i, str(info['name'])) for i, info in enumerate(devices) if info.get('max_input_channels', 0) > 0]

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
        value = int(sample * gain)
        samples[i] = max(-32768, min(32767, value))
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
    recognizer = KaldiRecognizer(model, sample_rate)
    recognizer.SetWords(True)
    with sd.RawInputStream(samplerate=sample_rate, blocksize=2048, dtype='int16', channels=1, callback=_callback, device=selected, latency='low'):
        while True:
            if stop_event and stop_event.is_set():
                return ''
            try:
                data = audio_queue.get(timeout=0.15)
            except queue.Empty:
                continue
            boosted = _adaptive_gain(data)
            if recognizer.AcceptWaveform(boosted):
                text = json.loads(recognizer.Result()).get('text', '').strip()
                if text:
                    return text

_tts_lock = threading.Lock()
_tts_engine = None

def _tts():
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = pyttsx3.init('sapi5')
        voices = _tts_engine.getProperty('voices') or []
        preferred = ('zira', 'david', 'english', 'mark')
        chosen = None
        for voice in voices:
            name = str(getattr(voice, 'name', '')).lower()
            if any(token in name for token in preferred):
                chosen = voice.id
                break
        if chosen:
            _tts_engine.setProperty('voice', chosen)
        _tts_engine.setProperty('rate', 165)
        _tts_engine.setProperty('volume', 1.0)
    return _tts_engine

def _speech_chunks(text: str) -> list[str]:
    clean = re.sub(r'```.*?```', ' ', text, flags=re.S)
    clean = re.sub(r'[#*_`>]', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    if not clean:
        return []
    chunks = re.split(r'(?<=[.!?])\s+', clean)
    return [chunk.strip() for chunk in chunks if chunk.strip()]

def speak(text: str, stop_event: threading.Event | None = None) -> None:
    chunks = _speech_chunks(text)
    if not chunks:
        return
    with _tts_lock:
        engine = _tts()
        for chunk in chunks:
            if stop_event and stop_event.is_set():
                engine.stop()
                return
            try:
                engine.say(chunk)
                engine.runAndWait()
            except RuntimeError:
                engine.stop()
                break