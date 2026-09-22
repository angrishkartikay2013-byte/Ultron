from __future__ import annotations

import os
import urllib.request
from pathlib import Path

from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parents[1]
WHISPER_DATA_DIR = ROOT / "voice_models" / "faster_whisper"
VAD_DATA_DIR = ROOT / "voice_models" / "silero_vad"
VAD_MODEL_PATH = VAD_DATA_DIR / "silero_vad.onnx"
VAD_MODEL_URL = (
    "https://raw.githubusercontent.com/snakers4/silero-vad/master/"
    "src/silero_vad/data/silero_vad.onnx"
)

MODEL = os.getenv("ULTRON_STT_MODEL", "base.en")
THREADS = max(2, min(4, os.cpu_count() or 4))


def download_vad() -> None:
    VAD_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if VAD_MODEL_PATH.exists() and VAD_MODEL_PATH.stat().st_size > 100_000:
        print(f"Silero VAD already ready: {VAD_MODEL_PATH}")
        return

    tmp = VAD_MODEL_PATH.with_suffix(".download")
    print(f"Downloading official Silero VAD ONNX model to {VAD_MODEL_PATH}")
    urllib.request.urlretrieve(VAD_MODEL_URL, tmp)
    if tmp.stat().st_size < 100_000:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise RuntimeError("Downloaded Silero VAD model looks incomplete.")
    tmp.replace(VAD_MODEL_PATH)


def download_whisper() -> None:
    WHISPER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Preparing faster-whisper model: {MODEL}")
    print(f"Model directory: {WHISPER_DATA_DIR}")
    WhisperModel(
        MODEL,
        device="cpu",
        compute_type="int8",
        cpu_threads=THREADS,
        num_workers=1,
        download_root=str(WHISPER_DATA_DIR),
    )
    print(f"{MODEL} is ready for CPU INT8 inference.")


def main() -> None:
    download_vad()
    download_whisper()


if __name__ == "__main__":
    main()
