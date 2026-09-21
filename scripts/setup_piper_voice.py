from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'voice_models' / 'piper'

def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-m', 'piper.download_voices', 'en_US-ryan-high', '--data-dir', str(DATA_DIR)]
    print('Downloading Piper en_US-ryan-high neural voice (~121 MB)...')
    subprocess.run(command, check=True)
    print(f'Piper voice installed under: {DATA_DIR}')

if __name__ == '__main__':
    main()