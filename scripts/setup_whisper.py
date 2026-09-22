from __future__ import annotations

from pathlib import Path

from moonshine_voice import ModelArch, get_model_for_language

ROOT = Path(__file__).resolve().parents[1]
MOONSHINE_DATA_DIR = ROOT / "voice_models" / "moonshine_voice"
MODEL_ARCH = ModelArch.SMALL_STREAMING


def main() -> None:
    MOONSHINE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("Preparing Moonshine Voice small-streaming English model...")
    print(f"Model cache: {MOONSHINE_DATA_DIR}")

    model_path, model_arch = get_model_for_language(
        "en",
        wanted_model_arch=MODEL_ARCH,
        cache_root=MOONSHINE_DATA_DIR,
    )

    print(f"Moonshine model ready: {model_path}")
    print(f"Model architecture: {model_arch}")


if __name__ == "__main__":
    main()
