from __future__ import annotations

import ctypes
import math
import queue
import threading
import time
from dataclasses import dataclass

from PySide6.QtCore import QPoint, QRectF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from brain.agent import stream_prompt
from brain.llm import resident_model_for, warm_model
from brain.router import MICRO_MODEL, AGENT_MODEL, FAST_MODEL, MID_MODEL, HEAVY_MODEL, VISION_MODEL, route_prompt
from debug import info, error, exception, log_path


VK_Y = 0x59
VK_CONTROL = 0x11

_BACKGROUND_IDLE_SECONDS = 30.0
_ACTIVITY_LOCK = threading.Lock()
_LAST_ACTIVITY = time.monotonic()
_ULTRON_BUSY = threading.Event()


def mark_activity() -> None:
    global _LAST_ACTIVITY
    with _ACTIVITY_LOCK:
        _LAST_ACTIVITY = time.monotonic()


def background_idle() -> bool:
    if _ULTRON_BUSY.is_set():
        return False
    with _ACTIVITY_LOCK:
        return time.monotonic() - _LAST_ACTIVITY >= _BACKGROUND_IDLE_SECONDS




def interrupt_pressed() -> bool:
    user32 = ctypes.windll.user32
    return bool(
        user32.GetAsyncKeyState(VK_CONTROL) & 0x8000
        and user32.GetAsyncKeyState(VK_Y) & 0x8000
    )


class StartupWorker(QThread):
    ready = Signal()
    status = Signal(str)
    failed = Signal(str)
    finished_background = Signal()

    def run(self) -> None:
        # Only the tiny micro-brain blocks the orb from appearing.
        try:
            self.status.emit("Starting micro-brain…")
            micro = warm_model(MICRO_MODEL)
            self.status.emit(f"Micro online • {micro}")
            mark_activity()
            self.ready.emit()
        except Exception as exc:
            exception("Micro-brain startup failed")
            self.failed.emit(
                f"Micro startup failed: {exc} • debug: {log_path()}"
            )
            return

        # Richer brains and voice warm only after the orb is already usable.
        background_tasks = [
            ("operator brain", lambda: warm_model(AGENT_MODEL)),
            ("conversation brain", lambda: warm_model(FAST_MODEL)),
            ("voice engine", self._warm_voice),
        ]

        for label, task in background_tasks:
            while not background_idle():
                time.sleep(0.5)

            try:
                self.status.emit(f"Background: loading {label}…")
                loaded = task()
                if loaded:
                    self.status.emit(f"Background: {label} online • {loaded}")
                else:
                    self.status.emit(f"Background: {label} online")
            except Exception as exc:
                exception(f"Background startup failed: {label}")
                self.status.emit(
                    f"Background: {label} skipped • {exc} • debug: {log_path()}"
                )

        self.status.emit("Background: larger brains remain on-demand.")
        self.finished_background.emit()

    @staticmethod
    def _warm_voice() -> str:
        from voice import load_voice_models
        stt_name = load_voice_models()
        return stt_name


class VoiceWorker(QThread):
    heard = Signal(str)
    partial = Signal(str)
    failed = Signal(str)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.stop_event = threading.Event()

    def stop(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        try:
            info("Voice worker started listening")
            from voice import listen_once
            text = listen_once(
                stop_event=self.stop_event,
                partial_callback=self.partial.emit,
            )
            info(f"Voice worker heard: {text!r}")
            if text and not self.stop_event.is_set():
                self.heard.emit(text)
        except Exception as exc:
            if not self.stop_event.is_set():
                exception("Voice worker failed")
                self.failed.emit(
                    f"{exc} • debug: {log_path()}"
                )


class ReplyWorker(QThread):
    ready = Signal(str)
    chunk = Signal(str)
    failed = Signal(str)

    def __init__(self, prompt: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.prompt = prompt

    def run(self) -> None:
        try:
            info(f"Reply worker started: {self.prompt!r}")
            parts: list[str] = []
            for token in stream_prompt(self.prompt):
                parts.append(token)
                self.chunk.emit(token)
            final = "".join(parts).strip()
            info(f"Reply worker completed: {final[:200]!r}")
            self.ready.emit(final)
        except Exception as exc:
            exception("Reply worker failed")
            self.failed.emit(f"{exc} • debug: {log_path()}")


class SpeechWorker(QThread):
    started_speaking = Signal()
    done = Signal()

    def __init__(self, text: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.text = text
        self.stop_event = threading.Event()

    def stop(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        try:
            from voice import speak
            if self.text.strip() and not self.stop_event.is_set():
                self.started_speaking.emit()
                speak(self.text, stop_event=self.stop_event)
        finally:
            self.done.emit()



@dataclass
class Message:
    role: str
    text: str


class CommandPopup(QFrame):
    submit_requested = Signal(str)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(460)

        self.status = QLabel("ULTRON • READY")
        self.status.setStyleSheet(
            "color:#8ea7c2;font-size:10px;font-weight:700;letter-spacing:1px;"
        )

        self.text = QLabel("Double-click the orb for Memory Galaxy.")
        self.text.setWordWrap(True)
        self.text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.text.setStyleSheet("color:#f2f4f7;font-size:14px;")

        self.activity = QLabel("")
        self.activity.setWordWrap(True)
        self.activity.setStyleSheet(
            "color:#8792a2;font-size:10px;line-height:1.4;"
        )
        self.activity.hide()

        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a command…")
        self.input.returnPressed.connect(self._send)
        self.input.setStyleSheet(
            "QLineEdit{background:#12161b;color:#f2f4f7;border:1px solid #252a31;"
            "border-radius:9px;padding:9px;font-size:13px;}"
            "QLineEdit:focus{border:1px solid #4f78b2;}"
        )

        buttons = QHBoxLayout()
        buttons.setSpacing(8)

        details = QPushButton("ACTIVITY")
        details.clicked.connect(lambda: self.activity.setVisible(not self.activity.isVisible()))
        details.setStyleSheet(
            "QPushButton{background:#12161b;color:#9eabbc;border:1px solid #2a313a;"
            "border-radius:8px;padding:7px 10px;font-weight:600;}"
            "QPushButton:hover{background:#1b2027;}"
        )

        send = QPushButton("SEND")
        send.clicked.connect(self._send)
        send.setStyleSheet(
            "QPushButton{background:#1a2028;color:#dbe7f7;border:1px solid #313944;"
            "border-radius:8px;padding:7px 12px;font-weight:700;}"
            "QPushButton:hover{background:#212832;}"
        )

        buttons.addWidget(details)
        buttons.addStretch()
        buttons.addWidget(send)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(9)
        layout.addWidget(self.status)
        layout.addWidget(self.text)
        layout.addWidget(self.activity)
        layout.addWidget(self.input)
        layout.addLayout(buttons)

    def _send(self) -> None:
        value = self.input.text().strip()
        if value:
            self.input.clear()
            self.submit_requested.emit(value)

    def set_status(self, value: str) -> None:
        self.status.setText(value.upper())

    def set_activity(self, value: str) -> None:
        self.activity.setText(value)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(15, 17, 21, 249))
        painter.setPen(QPen(QColor(48, 55, 65, 230), 1))
        painter.drawRoundedRect(
            QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
            16,
            16,
        )


class GenesisOrb(QWidget):
    COLORS = {
        "idle": QColor("#66809a"),
        "listening": QColor("#6ea8fe"),
        "thinking": QColor("#a58bd9"),
        "speaking": QColor("#72d6a1"),
        "error": QColor("#d77c7c"),
    }

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(380, 250)
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("ULTRON")

        self.phase = 0.0
        self.state = "idle"
        self.popup: CommandPopup | None = None
        self.voice: VoiceWorker | None = None
        self.reply: ReplyWorker | None = None
        self.speech: SpeechWorker | None = None
        self.galaxy = None
        self._interrupt_down = False
        self._active_prompt = ""
        self._response_text = ""
        self._generation_finished = False
        self._speech_finished = False
        self.boot_status = "Reflex brain starting…"

        self._dragging = False
        self._drag_offset = QPoint()
        self._last_mouse_pos = QPoint()

        self.caption = QLabel("", self)
        self.caption.setGeometry(24, 128, 332, 78)
        self.caption.setAlignment(Qt.AlignCenter)
        self.caption.setWordWrap(True)
        self.caption.setTextInteractionFlags(Qt.NoTextInteraction)
        self.caption.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.caption.setStyleSheet(
            "QLabel{color:#eef3f8;font-size:12px;font-weight:500;"
            "background:transparent;padding:2px 6px;}"
        )

        self.activity_label = QLabel("", self)
        self.activity_label.setGeometry(34, 209, 312, 30)
        self.activity_label.setAlignment(Qt.AlignCenter)
        self.activity_label.setWordWrap(True)
        self.activity_label.setTextInteractionFlags(Qt.NoTextInteraction)
        self.activity_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.activity_label.setStyleSheet(
            "QLabel{color:#7f8da0;font-size:9px;background:transparent;}"
        )

        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.setInterval(210)
        self._click_timer.timeout.connect(self.listen)

        self._listen_again_timer = QTimer(self)
        self._listen_again_timer.setSingleShot(True)
        self._listen_again_timer.timeout.connect(self.listen)

        screen = QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.move(
                area.left() + (area.width() - self.width()) // 2,
                area.top() + 10,
            )

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(16)

        self.interrupt_timer = QTimer(self)
        self.interrupt_timer.timeout.connect(self.poll_interrupt)
        self.interrupt_timer.start(35)

    def set_display(self, text: str) -> None:
        self.caption.setText(text.strip())
        self.caption.adjustSize()
        # Keep the response area tied to the orb instead of spawning a chat window.
        self.caption.setGeometry(24, 128, 332, 78)

    def set_activity(self, text: str) -> None:
        self.activity_label.setText(text.strip())
        self.activity_label.adjustSize()
        self.activity_label.setGeometry(34, 209, 312, 30)
        if self.popup is not None and self.popup.isVisible():
            self.popup.set_activity(text)

    def animate(self) -> None:
        self.phase += 0.045
        self.update()

    def poll_interrupt(self) -> None:
        down = interrupt_pressed()
        if down and not self._interrupt_down:
            self.interrupt()
        self._interrupt_down = down

    def set_state(self, state: str) -> None:
        self.state = state
        if self.popup:
            self.popup.set_status(f"ULTRON • {state}")

    def popup_pos(self) -> QPoint:
        screen = QApplication.primaryScreen()
        if screen is None:
            return QPoint(self.x(), self.y() + self.height() + 10)

        desired_x = self.x() + self.width() // 2 - 230
        desired_y = self.y() + self.height() + 10
        area = screen.availableGeometry()
        desired_x = max(area.left() + 10, min(desired_x, area.right() - 470))
        if desired_y + 290 > area.bottom():
            desired_y = self.y() - 290
        return QPoint(desired_x, max(area.top() + 10, desired_y))

    def show_popup(self) -> None:
        if self.popup is None:
            self.popup = CommandPopup(self)
            self.popup.submit_requested.connect(self.submit)
        self.popup.move(self.popup_pos())
        self.popup.show()
        self.popup.raise_()
        self.popup.set_activity(self.boot_status)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.RightButton:
            self.show_popup()
            return

        if event.button() == Qt.LeftButton:
            self._click_timer.stop()
            self._last_mouse_pos = event.globalPosition().toPoint()
            self._drag_offset = self._last_mouse_pos - self.frameGeometry().topLeft()
            self._dragging = False

    def mouseMoveEvent(self, event) -> None:
        if not (event.buttons() & Qt.LeftButton):
            return

        current = event.globalPosition().toPoint()
        delta = current - self._last_mouse_pos
        if not self._dragging and (abs(delta.x()) > 3 or abs(delta.y()) > 3):
            self._dragging = True
            if self.popup is not None:
                self.popup.hide()

        if not self._dragging:
            return

        screen = QApplication.primaryScreen()
        if screen is None:
            return

        area = screen.availableGeometry()
        desired_x = current.x() - self._drag_offset.x()
        desired_y = current.y() - self._drag_offset.y()
        desired_x = max(area.left(), min(desired_x, area.right() - self.width() + 1))
        desired_y = max(area.top(), min(desired_y, area.bottom() - self.height() + 1))
        self.move(desired_x, desired_y)
        self._last_mouse_pos = current

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return
        if not self._dragging:
            self._click_timer.start()
        self._dragging = False

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return
        self._click_timer.stop()
        from .genesis import open_memory_galaxy
        self.galaxy = open_memory_galaxy()

    def listen(self) -> None:
        if self.reply and self.reply.isRunning():
            return
        if self.voice and self.voice.isRunning():
            return

        self._listen_again_timer.stop()
        self.set_state("listening")
        self.set_display("Listening…")
        self.set_activity("Microphone active • speak naturally")
        self.voice = VoiceWorker(self)
        self.voice.heard.connect(self.submit)
        self.voice.partial.connect(self.voice_partial)
        self.voice.failed.connect(self.voice_error)
        self.voice.finished.connect(self.voice_finished)
        self.voice.start()

    def voice_partial(self, text: str) -> None:
        if not text.strip() or _ULTRON_BUSY.is_set():
            return
        self.set_display(f"Hearing: {text}")
        self.set_activity("Live transcription • waiting for you to finish speaking")
        self.update()

    def voice_finished(self) -> None:
        # An empty/no-speech capture should retry instead of leaving the orb
        # listening visually while the worker has already exited.
        if self.voice and not self.voice.isRunning():
            self.voice = None
        if (
            self.state == "listening"
            and not self._ULTRON_busy_for_voice()
            and not (self.reply and self.reply.isRunning())
        ):
            self._listen_again_timer.start(350)

    def _ULTRON_busy_for_voice(self) -> bool:
        return _ULTRON_BUSY.is_set()

    def submit(self, prompt: str) -> None:
        prompt = prompt.strip()
        if not prompt:
            return

        _ULTRON_BUSY.set()
        mark_activity()
        self.stop_voice()
        if self.popup is not None:
            self.popup.hide()

        self.set_state("thinking")
        self._active_prompt = prompt
        self._response_text = ""
        self._generation_finished = False
        self._speech_finished = False

        route = route_prompt(prompt)
        try:
            actual_model = resident_model_for(route.model)
        except Exception:
            actual_model = route.model

        self.set_display(
            f"Heard: {prompt}\n\nInterpreting…"
        )
        self.set_activity(
            f"Stage: interpreting → {route.agent.upper()} • {actual_model}"
        )
        info(
            f"Prompt received: {prompt!r} | route={route.agent} | "
            f"requested_model={route.model} | resident_model={actual_model}"
        )

        if self.reply and self.reply.isRunning():
            self.reply.terminate()
            self.reply.wait(100)

        if self.speech and self.speech.isRunning():
            self.speech.stop()
            self.speech.wait(250)

        self.reply = ReplyWorker(prompt, self)
        self.reply.chunk.connect(self.reply_chunk)
        self.reply.ready.connect(self.reply_ready)
        self.reply.failed.connect(self.reply_error)
        self.reply.start()

    def reply_chunk(self, token: str) -> None:
        self._response_text += token
        self.set_display(
            f"Heard: {self._active_prompt}\n\nInterpreting…\n\n"
            f"ULTRON: {self._response_text}"
        )
        self.set_activity("Stage: interpreting → generating response")
        self.update()


    def reply_ready(self, text: str) -> None:
        self._generation_finished = True
        final_text = text.strip() or self._response_text.strip()

        if final_text:
            self.set_display(
                f"Heard: {self._active_prompt}\n\n"
                f"Conclusion:\n{final_text}"
            )
            self.set_activity("Stage: conclusion reached • preparing voice…")
            self._start_speech(final_text)
            return

        self._speech_finished = True
        _ULTRON_BUSY.clear()
        self.set_state("idle")
        self.set_activity("Ready")

    def _start_speech(self, text: str) -> None:
        self._speech_finished = False
        if self.speech and self.speech.isRunning():
            self.speech.stop()
            self.speech.wait(250)

        self.speech = SpeechWorker(text, self)
        self.speech.started_speaking.connect(self.speech_started)
        self.speech.done.connect(self.speech_finished)
        self.speech.start()


    def speech_started(self) -> None:
        info("TTS playback started")
        self.set_state("speaking")
        self.set_activity("Stage: speaking conclusion • Ctrl+Y interrupts")


    def speech_finished(self) -> None:
        info("TTS playback finished")
        self._speech_finished = True
        _ULTRON_BUSY.clear()
        mark_activity()
        self.speech = None
        self.set_state("idle")
        self.set_activity("Voice finished • waiting 1.5 seconds before listening")
        self._maybe_listen()


    def _maybe_listen(self) -> None:
        if self._generation_finished and self._speech_finished:
            self._listen_again_timer.start(1500)

    def interrupt(self) -> None:
        info("Founder interrupted ULTRON")
        _ULTRON_BUSY.clear()
        mark_activity()
        self._click_timer.stop()
        self._listen_again_timer.stop()
        self.stop_voice()
        if self.speech and self.speech.isRunning():
            self.speech.stop()
            self.speech.wait(250)
            self.speech = None
        if self.reply and self.reply.isRunning():
            self.reply.terminate()
            self.reply.wait(200)
            self.reply = None
        self._generation_finished = False
        self._speech_finished = False
        self.set_state("idle")
        self.set_display("Interrupted.")
        self.set_activity("Ready • Ctrl+Y interrupted the current task")

    def stop_voice(self) -> None:
        if self.voice and self.voice.isRunning():
            self.voice.stop()
            self.voice.wait(300)
        self.voice = None

    def voice_error(self, message: str) -> None:
        error(f"Microphone/voice error surfaced: {message}")
        self.set_state("error")
        self.set_display("Voice error")
        self.set_activity(
            f"{message}\nDebug log: {log_path()}"
        )

    def reply_error(self, message: str) -> None:
        error(f"Brain error surfaced: {message}")
        _ULTRON_BUSY.clear()
        mark_activity()
        self._generation_finished = True
        self._speech_finished = True
        if self.speech and self.speech.isRunning():
            self.speech.stop()
            self.speech.wait(250)
            self.speech = None
        self.set_state("error")
        self.set_display("Brain error")
        self.set_activity(
            f"{message}\nDebug log: {log_path()}"
        )

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = QPoint(self.width() // 2, 70)
        color = self.COLORS[self.state]

        pulse = math.sin(self.phase) * 3.0
        ring = 42 + pulse

        for radius, alpha in (
            (61 + pulse, 8),
            (55 + pulse, 12),
            (49 + pulse, 18),
        ):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), alpha))
            painter.drawEllipse(center, int(radius), int(radius))

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 90), 1.4))
        painter.drawEllipse(center, int(ring), int(ring))

        painter.setPen(QPen(color, 2.2))
        painter.drawArc(
            QRectF(center.x() - 56, center.y() - 56, 112, 112),
            int((self.phase * 700) % 360) * 16,
            82 * 16,
        )

        painter.setPen(Qt.NoPen)
        for index in range(6):
            angle = self.phase * (1.0 + index * 0.05) + index * math.tau / 6
            radius = 50 + 4 * math.sin(self.phase * 1.5 + index)
            px = center.x() + math.cos(angle) * radius
            py = center.y() + math.sin(angle) * radius
            size = 2.2 + (1.0 if self.state != "idle" else 0.0)
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 210))
            painter.drawEllipse(QPoint(int(px), int(py)), int(size), int(size))

        gradient = QRadialGradient(center, 31)
        gradient.setColorAt(0.0, QColor(255, 255, 255, 240))
        gradient.setColorAt(0.2, color.lighter(145))
        gradient.setColorAt(0.68, color)
        gradient.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))

        painter.setPen(QPen(QColor(238, 244, 250, 185), 1))
        painter.setBrush(gradient)
        painter.drawEllipse(center, 29, 29)

        painter.setPen(QColor(190, 200, 214, 180))
        painter.setFont(QFont("Segoe UI", 7, QFont.DemiBold))
        painter.drawText(
            QRectF(0, 110, self.width(), 16),
            Qt.AlignCenter,
            self.state.upper(),
        )

    def closeEvent(self, event) -> None:
        self._click_timer.stop()
        self._listen_again_timer.stop()
        self.stop_voice()
        if self.speech and self.speech.isRunning():
            self.speech.stop()
            self.speech.wait(200)
        if self.reply and self.reply.isRunning():
            self.reply.terminate()
            self.reply.wait(200)
        event.accept()


def run_genesis() -> int:
    app = QApplication.instance() or QApplication([])

    worker = StartupWorker()
    app._ultron_boot_worker = worker

    def attach_orb() -> None:
        orb = GenesisOrb()
        app._ultron_orb = orb

        orb.show()
        orb.raise_()
        app.processEvents()

        orb.set_state("idle")
        orb.boot_status = (
            "REFLEX ONLINE\n"
            "Voice, fast, reasoning, vision, and builder brains loading in background…"
        )

        def update_boot_status(message: str) -> None:
            orb.boot_status = message
            if orb.popup is not None:
                orb.popup.set_activity(message)

        worker.status.connect(update_boot_status)

    def background_done() -> None:
        orb = getattr(app, "_ultron_orb", None)
        if orb is not None and orb.popup is not None:
            orb.popup.set_activity(
                "SYSTEM: background brain loading pass complete.\n"
                "ULTRON routes each task to the smallest suitable brain."
            )

    def startup_failed(message: str) -> None:
        orb = getattr(app, "_ultron_orb", None)
        if orb is None:
            orb = GenesisOrb()
            app._ultron_orb = orb
            orb.show()
        orb.set_state("error")
        orb.show_popup()
        orb.popup.text.setText("Brain startup warning:\n" + message)
        orb.popup.set_activity("Reflex brain could not start.")

    worker.ready.connect(attach_orb)
    worker.finished_background.connect(background_done)
    worker.failed.connect(startup_failed)
    worker.start()

    return app.exec()

