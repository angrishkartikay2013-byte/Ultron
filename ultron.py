from __future__ import annotations

import ctypes
import threading
import time

from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtWidgets import QApplication

from brain.agent import handle_prompt
from brain.llm import provider_status
from runtime.token_state import get as token_state
from ui.ultron_window import UltronWindow

PROMPT_LOCK = threading.Lock()
VK_CONTROL = 0x11
VK_Y = 0x59


class PromptWorker(QThread):
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, prompt: str) -> None:
        super().__init__()
        self.prompt = prompt

    def run(self) -> None:
        try:
            # Voice and typed missions share conversation memory, so serialize them.
            with PROMPT_LOCK:
                response = handle_prompt(self.prompt)
            self.succeeded.emit(response or "I didn't get a response for that request.")
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class VoiceRuntime(QThread):
    heard = Signal(str)
    answered = Signal(str)
    status = Signal(str)

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

    def _interrupt_loop(self) -> None:
        was_down = False
        while not self.stop_event.is_set():
            try:
                down = bool(
                    ctypes.windll.user32.GetAsyncKeyState(VK_CONTROL) & 0x8000
                    and ctypes.windll.user32.GetAsyncKeyState(VK_Y) & 0x8000
                )
                if down and not was_down:
                    self.interrupt()
                was_down = down
            except Exception:
                return
            time.sleep(0.035)

    def run(self) -> None:
        try:
            from voice import listen_once, load_voice_models, speak
            self.status.emit("LOADING VOICE MODEL")
            load_voice_models()
        except Exception as exc:
            self.status.emit(f"VOICE ERROR: {exc}")
            return

        threading.Thread(
            target=self._interrupt_loop,
            name="ultron-interrupt-monitor",
            daemon=True,
        ).start()

        while not self.stop_event.is_set():
            listen_stop = threading.Event()
            self._set_active(listen_stop)
            self.status.emit("LISTENING")
            try:
                prompt = listen_once(stop_event=listen_stop)
            except Exception as exc:
                self.status.emit(f"VOICE ERROR: {exc}")
                if self.stop_event.wait(2.0):
                    break
                continue
            finally:
                self._set_active(None)

            if self.stop_event.is_set():
                break
            if not prompt or not prompt.strip():
                continue

            prompt = prompt.strip()
            self.heard.emit(prompt)
            self.status.emit("PROCESSING VOICE")
            try:
                with PROMPT_LOCK:
                    response = handle_prompt(prompt)
            except Exception as exc:
                self.status.emit(f"AGENT ERROR: {exc}")
                continue

            if not response or not response.strip():
                continue
            self.answered.emit(response.strip())
            self.status.emit("SPEAKING")

            speech_stop = threading.Event()
            self._set_active(speech_stop)
            try:
                speak(response, stop_event=speech_stop)
            except Exception as exc:
                self.status.emit(f"TTS ERROR: {exc}")
            finally:
                self._set_active(None)

            if self.stop_event.wait(0.35):
                break


class UltronApplication:
    def __init__(self) -> None:
        self.window = UltronWindow()
        self.window.set_model_provider(provider_status())
        self.voice = VoiceRuntime()
        self.workers: set[PromptWorker] = set()

        self.window.prompt_requested.connect(self.submit_prompt)
        self.voice.heard.connect(lambda prompt: self.window.add_message("user", prompt))
        self.voice.answered.connect(lambda response: self.window.add_message("assistant", response))
        self.voice.status.connect(self.window.set_voice_status)

        self.token_timer = QTimer()
        self.token_timer.timeout.connect(self.update_tokens)
        self.token_timer.start(1000)

    def update_tokens(self) -> None:
        snapshot = token_state()
        self.window.set_tokens(snapshot.remaining_tokens)

    def submit_prompt(self, prompt: str) -> None:
        self.window.add_message("user", prompt)
        self.window.set_busy(True)
        self.window.set_voice_status("TEXT MISSION")
        worker = PromptWorker(prompt)
        self.workers.add(worker)
        worker.succeeded.connect(self.on_success)
        worker.failed.connect(self.on_failure)
        worker.finished.connect(lambda w=worker: self._release_worker(w))
        worker.start()

    def on_success(self, response: str) -> None:
        self.window.add_message("assistant", response)
        self.window.set_busy(False)
        self.window.set_voice_status("READY")

    def on_failure(self, error: str) -> None:
        self.window.add_message("error", error)
        self.window.set_busy(False)
        self.window.set_voice_status("AGENT ERROR")

    def _release_worker(self, worker: PromptWorker) -> None:
        self.workers.discard(worker)
        worker.deleteLater()

    def run(self) -> int:
        self.window.show()
        self.voice.start()
        code = QApplication.instance().exec()
        self.voice.stop()
        if self.voice.isRunning():
            self.voice.wait(3000)
        for worker in list(self.workers):
            if worker.isRunning():
                worker.wait(1000)
        return code


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("ULTRON")
    app.setOrganizationName("ULTRON")
    application = UltronApplication()
    return application.run()


if __name__ == "__main__":
    raise SystemExit(main())
