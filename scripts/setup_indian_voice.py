from __future__ import annotations

import io
import shutil
import zipfile
from pathlib import Path

import requests

URL = 'https://alphacephei.com/vosk/models/vosk-model-small-en-in-0.4.zip'
ROOT = Path(__file__).resolve().parents[1]
VOICE_DIR = ROOT / 'voice_models'
TARGET = VOICE_DIR / 'vosk-model-small-en-in-0.4'

def main() -> None:
    if TARGET.exists():
        print(f'Indian English Vosk model already exists: {TARGET}')
        return

    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    print('Downloading 36 MB Indian English Vosk model...')
    response = requests.get(URL, timeout=60)
    response.raise_for_status()
    archive = io.BytesIO(response.content)

    with zipfile.ZipFile(archive) as zf:
        zf.extractall(VOICE_DIR)

    print(f'Installed: {TARGET}')

if __name__ == '__main__':
    main()