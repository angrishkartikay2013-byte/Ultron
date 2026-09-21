from __future__ import annotations

import os
import subprocess

OLLAMA = os.path.expandvars(r'%LOCALAPPDATA%\\Programs\\Ollama\\ollama.exe')
MODEL_DIR = r'E:\\ULTRON\\models'
MODEL = 'qwen2.5:3b'

def main() -> None:
    env = os.environ.copy()
    env['OLLAMA_MODELS'] = MODEL_DIR
    print(f'Pulling {MODEL} into {MODEL_DIR}...')
    subprocess.run([OLLAMA, 'pull', MODEL], env=env, check=True)
    print(f'{MODEL} is ready.')

if __name__ == '__main__':
    main()