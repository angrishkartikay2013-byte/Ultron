from __future__ import annotations

import ctypes
import threading
import time
import traceback

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from brain.agent import handle_prompt
from runtime.token_state import get as token_state
from ui.token_meter import TokenMeter


VK_CONTROL = 0x11
VK_Y = 0x59


def _interrupt_pressed() -> bool:
    user32 = ctypes.windll.user32
    return bool(
        user32.GetAsyncKeyState(VK_CONTROL) & 0x8000
        and user32.GetAsyncKeyState(VK_Y) & 0x8000
    )


class VoiceRuntime(QThread):
    """Headless voice runtime. No chat/orb/popup UI."""

    def __init__(self) -> None:
        super().__init__()
        self.stop_event = threading.Event()
        self._active_stop: threading.Event | None = None
        self._lock = threading.Lock()

    def stop(self) -> None:
        self.stop_event.set()
        self.interrupt()

    def interrupt(self) -> None:
        with self._lock:
            active = self._active_stop
        if active is not None:
            active.set()

    def _set_active(self, event: threading.Event | None) -> None:
        with self._lock:
            self._active_stop = event

    def run(self) -> None:
        from voice import listen_once, load_voice_models, speak

        load_voice_models()

        last_interrupt = False
        while not self.stop_event.is_set():
            interrupted = _interrupt_pressed()
            if interrupted and not last_interrupt:
                self.interrupt()
            last_interrupt = interrupted

            listen_stop = threading.Event()
            self._set_active(listen_stop)
            try:
                prompt = listen_once(stop_event=listen_stop)
            finally:
                self._set_active(None)

            if self.stop_event.is_set():
                break
            if not prompt.strip():
                continue

            print(f"You: {prompt}", flush=True)

            try:
                response = handle_prompt(prompt)
            except Exception as exc:
                print(f"ULTRON error: {exc}", flush=True)
                continue

            if not response.strip():
                continue

            print(f"ULTRON: {response}", flush=True)

            speech_stop = threading.Event()
            self._set_active(speech_stop)
            try:
                speak(response, stop_event=speech_stop)
            except Exception as exc:
                print(f"TTS error: {exc}", flush=True)
            finally:
                self._set_active(None)

            if self.stop_event.wait(1.5):
                break

            # Keep Ctrl+Y responsive between turns without changing the
            # normal voice flow.
            for _ in range(6):
                if self.stop_event.wait(0.05):
                    return


def main() -> int:
    print("⚡ ULTRON GENESIS starting...", flush=True)
    app = QApplication.instance() or QApplication([])

    meter = TokenMeter()
    meter.show()

    runtime = VoiceRuntime()
    runtime.finished.connect(app.quit)
    runtime.start()

    try:
        return app.exec()
    finally:
        runtime.stop()
        if runtime.isRunning():
            runtime.wait(3000)
        meter.close()


if __name__ == "__main__":
    raise SystemExit(main())
