from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WHISPER_DATA_DIR = ROOT / "voice_models" / "whispercpp_data"
WHISPER_MODELS_DIR = WHISPER_DATA_DIR / "models"

os.environ.setdefault("XDG_DATA_HOME", str(WHISPER_DATA_DIR))

from pywhispercpp.model import Model

MODEL = os.getenv("ULTRON_STT_MODEL", "base.en")


def main() -> None:
    WHISPER_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Loading Whisper.cpp model: {MODEL}")
    print(f"Model directory: {WHISPER_MODELS_DIR}")
    Model(
        MODEL,
        models_dir=str(WHISPER_MODELS_DIR),
        print_progress=True,
        print_realtime=False,
        n_threads=4,
    )
    print(f"{MODEL} is ready.")


if __name__ == "__main__":
    main()
