from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOONSHINE_DATA_DIR = ROOT / "voice_models" / "moonshine_voice"
MOONSHINE_TEMP_DIR = ROOT / "tmp" / "moonshine"
MODEL_ARCH_NAME = "small-streaming"


def main() -> None:
    MOONSHINE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    MOONSHINE_TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # Force both the Moonshine cache and Python temporary downloads onto E:.
    os.environ["MOONSHINE_VOICE_CACHE"] = str(MOONSHINE_DATA_DIR)
    os.environ["TEMP"] = str(MOONSHINE_TEMP_DIR)
    os.environ["TMP"] = str(MOONSHINE_TEMP_DIR)
    tempfile.tempdir = str(MOONSHINE_TEMP_DIR)

    _, _, free_bytes = shutil.disk_usage(MOONSHINE_DATA_DIR)
    if free_bytes < 300 * 1024 * 1024:
        raise RuntimeError(
            "ULTRON needs at least 300 MB free on the drive containing "
            f"{MOONSHINE_DATA_DIR}. Only {free_bytes / (1024 * 1024):.1f} MB is free. "
            "Free some space and run this setup again."
        )

    from moonshine_voice import ModelArch, get_model_for_language

    print("Preparing Moonshine Voice small-streaming English model...")
    print(f"Model cache: {MOONSHINE_DATA_DIR}")
    print(f"Temporary downloads: {MOONSHINE_TEMP_DIR}")

    model_path, model_arch = get_model_for_language(
        "en",
        wanted_model_arch=ModelArch.SMALL_STREAMING,
        cache_root=MOONSHINE_DATA_DIR,
    )

    print(f"Moonshine model ready: {model_path}")
    print(f"Model architecture: {model_arch}")


if __name__ == "__main__":
    main()
