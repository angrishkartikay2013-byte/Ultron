from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault(
    'XDG_DATA_HOME',
    str(Path(__file__).resolve().parents[1] / 'voice_models' / 'whispercpp_data'),
)

from pywhispercpp.model import Model

MODEL = os.getenv('ULTRON_STT_MODEL', 'base.en')

def main() -> None:
    print(f'Loading Whisper.cpp model: {MODEL}')
    Model(MODEL, print_progress=True, print_realtime=False, n_threads=4)
    print(f'{MODEL} is ready.')

if __name__ == '__main__':
    main()