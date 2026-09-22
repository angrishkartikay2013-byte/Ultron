from __future__ import annotations

import os
import subprocess

TOOL = {
    "name": "open_app",
    "description": "Open a Windows desktop application. Pass its plain application name.",
}

ALIASES = {
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "notepad": "notepad.exe",
    "note pad": "notepad.exe",
    "paint": "mspaint.exe",
    "microsoft paint": "mspaint.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "settings": "ms-settings:",
}


def run(app: str = "", name: str = "", application: str = "", **kwargs) -> str:
    value = (app or name or application).strip().lower()
    if not value:
        raise ValueError("No application name was supplied.")

    target = ALIASES.get(value, value)

    if target.endswith(":"):
        os.startfile(target)
    elif target.endswith(".exe") or "\\" in target or "/" in target:
        subprocess.Popen(target, shell=True)
    else:
        subprocess.Popen(f'start "" "{target}"', shell=True)

    return f"Opened {value}."
