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
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from brain import ask
from voice import listen_once, speak


def y_pressed() -> bool:
    return bool(ctypes.windll.user32.GetAsyncKeyState(0x59) & 0x8000)


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
    failed = Signal(str)

    def __init__(self, prompt: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.prompt = prompt

    def run(self) -> None:
        try:
            self.ready.emit(ask(self.prompt))
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
            "color:#7cecff;font-size:11px;font-weight:700;letter-spacing:1px;"
        )

        self.text = QLabel("Click the orb to speak.")
        self.text.setWordWrap(True)
        self.text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.text.setStyleSheet("color:#e9faff;font-size:14px;")

        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a command…")
        self.input.returnPressed.connect(self._send)
        self.input.setStyleSheet(
            "QLineEdit{background:#071522;color:#e9faff;border:1px solid #205b75;"
            "border-radius:10px;padding:10px;font-size:13px;}"
            "QLineEdit:focus{border:1px solid #54d7ff;}"
        )

        send = QPushButton("SEND")
        send.clicked.connect(self._send)
        send.setStyleSheet(
            "QPushButton{background:#0d4057;color:#a5f2ff;border:1px solid #3a8eaa;"
            "border-radius:10px;padding:8px;font-weight:700;}"
            "QPushButton:hover{background:#15566f;}"
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
        painter.setBrush(QColor(4, 14, 24, 245))
        painter.setPen(QPen(QColor(65, 190, 230, 120), 1))
        painter.drawRoundedRect(
            QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 18, 18
        )


class GenesisOrb(QWidget):
    COLORS = {
        "idle": QColor("#45d8ff"),
        "listening": QColor("#6effff"),
        "thinking": QColor("#ae7dff"),
        "speaking": QColor("#55ffad"),
        "error": QColor("#ff6370"),
    }

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(126, 126)
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("ULTRON GENESIS")

        self.phase = 0.0
        self.state = "idle"
        self.popup: CommandPopup | None = None
        self.voice: VoiceWorker | None = None
        self.reply: ReplyWorker | None = None
        self.speech: SpeechWorker | None = None
        self.messages: list[Message] = []
        self._y_down = False
        self._typing_token = 0
        self.galaxy = None

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
        self.phase += 0.05
        self.update()

    def poll_interrupt(self) -> None:
        down = y_pressed()
        if down and not self._y_down:
            self.interrupt()
        self._y_down = down

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
        from ui.genesis import open_memory_galaxy
        self.galaxy = open_memory_galaxy()

    def listen(self) -> None:
        if self.reply and self.reply.isRunning():
            return
        self.show_popup()
        self.set_state("listening")
        self.popup.text.setText("Listening…  (press Y to interrupt)")
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
        self.popup.text.setText(f"Founder: {prompt}\n\nULTRON is thinking…")
        self.messages.append(Message("Founder", prompt))

        if self.reply and self.reply.isRunning():
            self.reply.terminate()
            self.reply.wait(100)

        self.reply = ReplyWorker(prompt, self)
        self.reply.ready.connect(self.reply_ready)
        self.reply.failed.connect(self.reply_error)
        self.reply.finished.connect(self.reply_finished)
        self.reply.start()

    def reply_ready(self, text: str) -> None:
        self.messages.append(Message("ULTRON", text))
        self.set_state("speaking")
        self.type_reply(text)
        if self.speech and self.speech.isRunning():
            self.speech.stop()
            self.speech.wait(150)
        self.speech = SpeechWorker(text, self)
        self.speech.finished.connect(self.speech_finished)
        self.speech.start()

    def type_reply(self, text: str) -> None:
        if not self.popup:
            return

        self._typing_token += 1
        token = self._typing_token
        index = 0
        self.popup.text.setText("ULTRON:\n")

        def tick() -> None:
            nonlocal index
            if token != self._typing_token or not self.popup:
                return

            index = min(len(text), index + 3)
            self.popup.text.setText("ULTRON:\n" + text[:index])

            if index < len(text):
                QTimer.singleShot(14, tick)
            else:
                self.set_state("idle")
                QTimer.singleShot(250, self.listen)

        tick()

    def interrupt(self) -> None:
        self._typing_token += 1
        self.stop_voice()
        if self.speech and self.speech.isRunning():
            self.speech.stop()
            self.speech.wait(200)
            self.speech = None

        if self.reply and self.reply.isRunning():
            self.reply.terminate()
            self.reply.wait(150)
            self.reply = None

        self.set_state("idle")
        self.show_popup()
        self.popup.text.setText("Interrupted. Standing by.")

    def speech_finished(self) -> None:
        self.speech = None
        if self.state == "speaking":
            self.set_state("idle")

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

        pulse = math.sin(self.phase) * 2.5
        for radius, alpha in ((52 + pulse, 12), (47 + pulse, 18), (42 + pulse, 28)):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), alpha))
            painter.drawEllipse(center, radius, radius)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 95), 1.5))
        painter.drawEllipse(center, 38, 38)
        painter.drawEllipse(center, 46 + pulse, 46 + pulse)

        start_angle = int((self.phase * 700) % 360) * 16
        painter.setPen(QPen(color, 2.2))
        painter.drawArc(
            QRectF(center.x() - 50, center.y() - 50, 100, 100),
            start_angle,
            80 * 16,
        )

        gradient = QRadialGradient(center, 30)
        gradient.setColorAt(0.0, QColor(255, 255, 255, 245))
        gradient.setColorAt(0.18, color.lighter(155))
        gradient.setColorAt(0.65, color)
        gradient.setColorAt(
            1.0, QColor(color.red(), color.green(), color.blue(), 0)
        )

        painter.setPen(QPen(QColor(225, 251, 255, 190), 1))
        painter.setBrush(gradient)
        painter.drawEllipse(center, 28, 28)

        painter.setPen(QColor(216, 247, 255, 190))
        painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
        painter.drawText(
            QRectF(0, 99, self.width(), 18),
            Qt.AlignCenter,
            self.state.upper(),
        )

    def closeEvent(self, event) -> None:
        self._typing_token += 1
        self.stop_voice()
        if self.speech and self.speech.isRunning():
            self.speech.stop()
            self.speech.wait(200)
            self.speech = None
        if self.reply and self.reply.isRunning():
            self.reply.terminate()
            self.reply.wait(200)
        event.accept()


def run_genesis() -> int:
    app = QApplication.instance() or QApplication([])
    orb = GenesisOrb()
    orb.show()
    app.aboutToQuit.connect(orb.close)
    return app.exec()
