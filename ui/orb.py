from __future__ import annotations

import ctypes
import math
import threading
from dataclasses import dataclass

from PySide6.QtCore import QPoint, QRectF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLineEdit,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from brain.agent import stream_prompt
from brain.llm import warm_speed_stack
from voice import listen_once, speak


VK_Y = 0x59
VK_CONTROL = 0x11


def interrupt_pressed() -> bool:
    user32 = ctypes.windll.user32
    return bool(
        user32.GetAsyncKeyState(VK_CONTROL) & 0x8000
        and user32.GetAsyncKeyState(VK_Y) & 0x8000
    )


class VoiceWorker(QThread):
    heard = Signal(str)
    failed = Signal(str)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.stop_event = threading.Event()

    def stop(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        try:
            text = listen_once(stop_event=self.stop_event)
            if text and not self.stop_event.is_set():
                self.heard.emit(text)
        except Exception as exc:
            if not self.stop_event.is_set():
                self.failed.emit(str(exc))


class ReplyWorker(QThread):
    ready = Signal(str)
    chunk = Signal(str)
    failed = Signal(str)

    def __init__(self, prompt: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.prompt = prompt

    def run(self) -> None:
        try:
            parts: list[str] = []
            for token in stream_prompt(self.prompt):
                parts.append(token)
                self.chunk.emit(token)
            self.ready.emit("".join(parts).strip())
        except Exception as exc:
            self.failed.emit(str(exc))


class SpeechWorker(QThread):
    finished = Signal()

    def __init__(self, text: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.text = text
        self.stop_event = threading.Event()

    def stop(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        try:
            speak(self.text, stop_event=self.stop_event)
        finally:
            self.finished.emit()


@dataclass
class Message:
    role: str
    text: str


class CommandPopup(QFrame):
    submit_requested = Signal(str)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(430)

        self.status = QLabel("ULTRON • READY")
        self.status.setStyleSheet(
            "color:#8ea7c2;font-size:10px;font-weight:700;letter-spacing:1px;"
        )

        self.text = QLabel("Click the orb to speak.")
        self.text.setWordWrap(True)
        self.text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.text.setStyleSheet("color:#f2f4f7;font-size:14px;")

        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a command…")
        self.input.returnPressed.connect(self._send)
        self.input.setStyleSheet(
            "QLineEdit{background:#12161b;color:#f2f4f7;border:1px solid #252a31;"
            "border-radius:9px;padding:9px;font-size:13px;}"
            "QLineEdit:focus{border:1px solid #4f78b2;}"
        )

        send = QPushButton("SEND")
        send.clicked.connect(self._send)
        send.setStyleSheet(
            "QPushButton{background:#1a2028;color:#dbe7f7;border:1px solid #313944;"
            "border-radius:9px;padding:8px;font-weight:700;}"
            "QPushButton:hover{background:#212832;}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        layout.addWidget(self.status)
        layout.addWidget(self.text)
        layout.addWidget(self.input)
        layout.addWidget(send)

    def _send(self) -> None:
        value = self.input.text().strip()
        if value:
            self.input.clear()
            self.submit_requested.emit(value)

    def set_status(self, value: str) -> None:
        self.status.setText(value.upper())

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(15, 17, 21, 248))
        painter.setPen(QPen(QColor(48, 55, 65, 220), 1))
        painter.drawRoundedRect(
            QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 16, 16
        )


class GenesisOrb(QWidget):
    COLORS = {
        "idle": QColor("#71829a"),
        "listening": QColor("#6ea8fe"),
        "thinking": QColor("#9b87d9"),
        "speaking": QColor("#72d6a1"),
        "error": QColor("#d77c7c"),
    }

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(110, 110)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("ULTRON")

        self.phase = 0.0
        self.state = "idle"
        self.popup: CommandPopup | None = None
        self.voice: VoiceWorker | None = None
        self.reply: ReplyWorker | None = None
        self.speech: SpeechWorker | None = None
        self.chat_window = None
        self._interrupt_down = False
        self._typing_token = 0

        screen = QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.move(area.right() - self.width() - 28, area.bottom() - self.height() - 28)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(16)

        self.interrupt_timer = QTimer(self)
        self.interrupt_timer.timeout.connect(self.poll_interrupt)
        self.interrupt_timer.start(35)

    def animate(self) -> None:
        self.phase += 0.035
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

        desired_x = self.x() + self.width() // 2 - 215
        desired_y = self.y() + self.height() + 10
        area = screen.availableGeometry()
        desired_x = max(area.left() + 10, min(desired_x, area.right() - 440))
        if desired_y + 250 > area.bottom():
            desired_y = self.y() - 250
        return QPoint(desired_x, max(area.top() + 10, desired_y))

    def show_popup(self) -> None:
        if self.popup is None:
            self.popup = CommandPopup(self)
            self.popup.submit_requested.connect(self.submit)
        self.popup.move(self.popup_pos())
        self.popup.show()
        self.popup.raise_()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.listen()
        elif event.button() == Qt.RightButton:
            self.show_popup()

    def mouseDoubleClickEvent(self, event) -> None:
        from .chat import open_chat_window
        self.chat_window = open_chat_window()

    def listen(self) -> None:
        if self.reply and self.reply.isRunning():
            return
        self.show_popup()
        self.set_state("listening")
        self.popup.text.setText("Listening…")
        self.stop_voice()
        self.voice = VoiceWorker(self)
        self.voice.heard.connect(self.submit)
        self.voice.failed.connect(self.voice_error)
        self.voice.finished.connect(self._voice_finished)
        self.voice.start()

    def submit(self, prompt: str) -> None:
        prompt = prompt.strip()
        if not prompt:
            return

        self.stop_voice()
        self.show_popup()
        self.set_state("thinking")
        self.popup.text.setText(f"Founder: {prompt}\n\nULTRON is responding…")

        if self.reply and self.reply.isRunning():
            self.reply.terminate()
            self.reply.wait(100)

        self.reply = ReplyWorker(prompt, self)
        self.reply.chunk.connect(self.reply_chunk)
        self.reply.ready.connect(self.reply_ready)
        self.reply.failed.connect(self.reply_error)
        self.reply.finished.connect(self.reply_finished)
        self.reply.start()

    def reply_chunk(self, token: str) -> None:
        if not self.popup:
            return
        if self.state == "thinking":
            self.set_state("thinking")
        existing = self.popup.text.text()
        prefix = existing.split("\n\nULTRON:", 1)[0]
        if "\n\nULTRON:" not in existing:
            prefix = existing
            self.popup.text.setText(prefix + "\n\nULTRON:")
            existing = self.popup.text.text()
        self.popup.text.setText(self.popup.text.text() + token)
        self.popup.adjustSize()

    def reply_ready(self, text: str) -> None:
        if not text.strip():
            return
        self.set_state("speaking")
        if self.speech and self.speech.isRunning():
            self.speech.stop()
            self.speech.wait(150)
        self.speech = SpeechWorker(text, self)
        self.speech.finished.connect(self.speech_finished)
        self.speech.start()

    def interrupt(self) -> None:
        self._typing_token += 1
        self.stop_voice()
        if self.speech and self.speech.isRunning():
            self.speech.stop()
            self.speech.wait(250)
            self.speech = None
        if self.reply and self.reply.isRunning():
            self.reply.terminate()
            self.reply.wait(200)
            self.reply = None
        self.set_state("idle")
        self.show_popup()
        self.popup.text.setText("Interrupted. Standing by.")

    def speech_finished(self) -> None:
        self.speech = None
        if self.state == "speaking":
            self.set_state("idle")
            QTimer.singleShot(700, self.listen)

    def reply_finished(self) -> None:
        self.reply = None

    def stop_voice(self) -> None:
        if self.voice and self.voice.isRunning():
            self.voice.stop()
            self.voice.wait(300)
        self.voice = None

    def _voice_finished(self) -> None:
        self.voice = None

    def voice_error(self, message: str) -> None:
        self.set_state("error")
        self.show_popup()
        self.popup.text.setText("Microphone error:\n" + message)

    def reply_error(self, message: str) -> None:
        self.set_state("error")
        self.show_popup()
        self.popup.text.setText("Brain error:\n" + message)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = self.rect().center()
        color = self.COLORS[self.state]

        pulse = math.sin(self.phase) * 1.8
        for radius, alpha in ((45 + pulse, 10), (40 + pulse, 16), (35 + pulse, 20)):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), alpha))
            painter.drawEllipse(center, radius, radius)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 85), 1.2))
        painter.drawEllipse(center, 30, 30)
        painter.drawEllipse(center, 38 + pulse, 38 + pulse)

        painter.setPen(QPen(color, 1.8))
        painter.drawArc(
            QRectF(center.x() - 42, center.y() - 42, 84, 84),
            int((self.phase * 500) % 360) * 16,
            65 * 16,
        )

        gradient = QRadialGradient(center, 25)
        gradient.setColorAt(0.0, QColor(255, 255, 255, 235))
        gradient.setColorAt(0.2, color.lighter(135))
        gradient.setColorAt(0.7, color)
        gradient.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))

        painter.setPen(QPen(QColor(230, 236, 242, 170), 1))
        painter.setBrush(gradient)
        painter.drawEllipse(center, 23, 23)

        painter.setPen(QColor(190, 200, 214, 180))
        painter.setFont(QFont("Segoe UI", 7, QFont.DemiBold))
        painter.drawText(
            QRectF(0, 88, self.width(), 14),
            Qt.AlignCenter,
            self.state.upper(),
        )

    def closeEvent(self, event) -> None:
        self._typing_token += 1
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
    threading.Thread(
        target=lambda: _warm_stack(),
        daemon=True,
        name="ULTRON-speed-stack-warmup",
    ).start()
    orb = GenesisOrb()
    orb.show()
    return app.exec()


def _warm_stack() -> None:
    try:
        warm_speed_stack()
    except Exception:
        pass
