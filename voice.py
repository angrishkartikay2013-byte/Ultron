from pathlib import Path
import json, queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer

MODEL_PATH=Path("voice_models")/"vosk-model-small-en-us-0.15"
model=Model(str(MODEL_PATH))
audio_queue=queue.Queue()

def callback(indata,frames,time,status):
    audio_queue.put(bytes(indata))

def listen_once(device=None):
    rec=KaldiRecognizer(model,16000)
    with sd.RawInputStream(samplerate=16000,blocksize=8000,dtype="int16",channels=1,callback=callback,device=device):
        while True:
            data=audio_queue.get()
            if rec.AcceptWaveform(data):
                text=json.loads(rec.Result()).get("text","").strip()
                if text:
                    return text
