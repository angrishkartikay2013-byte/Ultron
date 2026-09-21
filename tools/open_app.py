import subprocess

TOOL = {
    "name": "open_app",
    "description": "Open a Windows application by its name."
}

COMMON_APPS = {
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "notepad": "notepad.exe",
    "cmd": "cmd.exe",
    "explorer": "explorer.exe"
}

def run(app):
    app = app.lower().strip()

    target = COMMON_APPS.get(app, app)

    subprocess.Popen(target, shell=True)

    return f"Opened {app}."