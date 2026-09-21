from __future__ import annotations

import ctypes
import math
import queue
import threading
from dataclasses import dataclass

from PySide6.QtCore import QPoint, QEasingCurve, QPropertyAnimation, QRectF, Qt, QThread, QTimer, Signal
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
from brain.llm import warm_model
from brain.router import AGENT_MODEL, FAST_MODEL, route_prompt


VK_Y = 0x59
VK_CONTROL = 0x11


def interrupt_pressed() -> bool:
    user32 = ctypes.windll.user32
    return bool(
        user32.GetAsyncKeyState(VK_CONTROL) & 0x8000
        and user32.GetAsyncKeyState(VK_Y) & 0x8000
    )


class StartupWorker(QThread):
    status = Signal(str)
    progress = Signal(int)
    ready = Signal()
    failed = Signal(str)

    def run(self) -> None:
        try:
            self.status.emit("Connecting to Ollama…")
            self.progress.emit(8)

            self.status.emit("Loading reflex brain…")
            self.progress.emit(28)
            reflex = warm_model(AGENT_MODEL)

            self.status.emit(f"Reflex ready • {reflex}")
            self.progress.emit(52)

            # Only warm the second brain when it is actually a different model.
            # This avoids loading the same 1.5B model twice when the tiny model
            # is not installed yet.
            if reflex != FAST_MODEL:
                self.status.emit("Loading fast brain…")
                self.progress.emit(68)
                fast = warm_model(FAST_MODEL)
                self.status.emit(f"Fast brain ready • {fast}")
            else:
                self.status.emit("Fast brain already loaded.")
            self.progress.emit(72)

            self.status.emit("Loading voice engine…")
            self.progress.emit(82)
            from voice import load_voice_models
            whisper_name, piper_name = load_voice_models()

            self.status.emit(f"Voice ready • {whisper_name} + {piper_name}")
            self.progress.emit(96)

            self.status.emit("ULTRON is ready.")
            self.progress.emit(100)
            self.ready.emit()
        except Exception as exc:
            self.failed.emit(str(exc))


class StartupSplash(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(430, 245)
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.phase = 0.0
        self.status_text = "Initializing…"
        self.progress_value = 0

        screen = QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.move(
                area.left() + (area.width() - self.width()) // 2,
                area.top() + (area.height() - self.height()) // 2,
            )

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(16)

    def set_status(self, value: str) -> None:
        self.status_text = value
        self.update()

    def set_progress(self, value: int) -> None:
        self.progress_value = max(0, min(100, value))
        self.update()

    def animate(self) -> None:
        self.phase += 0.075
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        painter.setBrush(QColor(11, 14, 18, 250))
        painter.setPen(QPen(QColor(49, 58, 70, 235), 1))
        painter.drawRoundedRect(rect, 22, 22)

        cx = self.width() / 2
        cy = 72
        pulse = math.sin(self.phase) * 3.0

        # Animated Genesis core.
        for radius, alpha in (
            (42 + pulse, 10),
            (35 + pulse, 17),
            (29 + pulse, 26),
        ):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(114, 214, 161, alpha))
            painter.drawEllipse(
                QPoint(int(cx), int(cy)),
                int(radius),
                int(radius),
            )

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(114, 214, 161, 145), 2))
        painter.drawArc(
            QRectF(cx - 28, cy - 28, 56, 56),
            int((self.phase * 900) % 360) * 16,
            250 * 16,
        )

        painter.setBrush(QColor(114, 214, 161, 235))
        painter.setPen(QPen(QColor(238, 244, 250, 170), 1))
        painter.drawEllipse(
            QPoint(int(cx), int(cy)),
            16 + int(abs(pulse) * 0.5),
            16 + int(abs(pulse) * 0.5),
        )

        painter.setPen(QColor(232, 238, 244, 245))
        painter.setFont(QFont("Segoe UI", 18, QFont.DemiBold))
        painter.drawText(
            QRectF(0, 22, self.width(), 28),
            Qt.AlignCenter,
            "ULTRON GENESIS",
        )

        painter.setPen(QColor(145, 157, 173, 235))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(
            QRectF(20, 112, self.width() - 40, 25),
            Qt.AlignCenter,
            self.status_text,
        )

        bar = QRectF(34, 157, self.width() - 68, 8)
        painter.setBrush(QColor(29, 35, 43, 255))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bar, 4, 4)

        fill = QRectF(
            bar.left(),
            bar.top(),
            bar.width() * (self.progress_value / 100.0),
            bar.height(),
        )
        painter.setBrush(QColor(114, 214, 161, 235))
        painter.drawRoundedRect(fill, 4, 4)

        # Small moving dots under the progress bar.
        painter.setBrush(Qt.NoBrush)
        for i in range(3):
            x = self.width() / 2 + math.sin(self.phase + i * 1.7) * (18 + i * 7)
            painter.setPen(QPen(QColor(114, 214, 161, 180), 1.5))
            painter.drawPoint(QPoint(int(x), 188))

        painter.setPen(QColor(107, 120, 137, 220))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(
            QRectF(0, 198, self.width(), 20),
            Qt.AlignCenter,
            f"{self.progress_value}%",
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
            from voice import listen_once
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
    started_speaking = Signal()
    finished = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.stop_event = threading.Event()
        self.incoming: queue.Queue[str | None] = queue.Queue()

    def feed(self, text: str) -> None:
        if text and not self.stop_event.is_set():
            self.incoming.put(text)

    def finish_input(self) -> None:
        if not self.stop_event.is_set():
            self.incoming.put(None)

    def stop(self) -> None:
        self.stop_event.set()
        self.incoming.put(None)

    def run(self) -> None:
        try:
            from voice import speak_streaming
            speak_streaming(
                self.incoming,
                self.stop_event,
                started_callback=self.started_speaking.emit,
            )
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
        self.setFixedSize(150, 150)
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

        screen = QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.move(
                area.left() + (area.width() - self.width()) // 2,
                area.top() + 16,
            )

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(16)

        self.interrupt_timer = QTimer(self)
        self.interrupt_timer.timeout.connect(self.poll_interrupt)
        self.interrupt_timer.start(35)

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

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.listen()
        elif event.button() == Qt.RightButton:
            self.show_popup()

    def mouseDoubleClickEvent(self, event) -> None:
        from .genesis import open_memory_galaxy
        self.galaxy = open_memory_galaxy()

    def listen(self) -> None:
        if self.reply and self.reply.isRunning():
            return
        self.show_popup()
        self.set_state("listening")
        self.popup.text.setText("Listening…")
        self.popup.set_activity("Microphone active. Waiting for speech.")
        self.stop_voice()
        self.voice = VoiceWorker(self)
        self.voice.heard.connect(self.submit)
        self.voice.failed.connect(self.voice_error)
        self.voice.start()

    def submit(self, prompt: str) -> None:
        prompt = prompt.strip()
        if not prompt:
            return

        self.stop_voice()
        self.show_popup()
        self.set_state("thinking")
        self._active_prompt = prompt
        self._response_text = ""
        route = route_prompt(prompt)
        self.popup.text.setText(f"Founder: {prompt}\n\nULTRON:")
        self.popup.set_activity(
            f"Route: {route.agent.upper()}  •  Model: {route.model}\n"
            "Stage: generating reply + preparing speech…"
        )

        if self.reply and self.reply.isRunning():
            self.reply.terminate()
            self.reply.wait(100)

        if self.speech and self.speech.isRunning():
            self.speech.stop()
            self.speech.wait(250)

        self.speech = SpeechWorker(self)
        self.speech.started_speaking.connect(self.speech_started)
        self.speech.finished.connect(self.speech_finished)
        self.speech.start()

        self.reply = ReplyWorker(prompt, self)
        self.reply.chunk.connect(self.reply_chunk)
        self.reply.ready.connect(self.reply_ready)
        self.reply.failed.connect(self.reply_error)
        self.reply.finished.connect(self.reply_finished)

        self.reply.start()


    def reply_chunk(self, token: str) -> None:
        if not self.popup:
            return
        self._response_text += token
        self.popup.text.setText(
            f"Founder: {self._active_prompt}\n\nULTRON:\n{self._response_text}"
        )
        if self.speech and self.speech.isRunning():
            self.speech.feed(token)
        self.popup.set_activity(
            "Stage: generating + speaking when sentences are ready…"
        )
        self.popup.adjustSize()

    def reply_ready(self, text: str) -> None:
        self._generation_finished = True
        if self.speech and self.speech.isRunning():
            self.speech.finish_input()
        elif text.strip():
            self._start_emergency_speech(text)

    def speech_started(self) -> None:
        self.set_state("speaking")
        if self.popup:
            self.popup.set_activity(
                "Stage: speaking while the AI is still generating…"
            )

    def _start_emergency_speech(self, text: str) -> None:
        self._speech_finished = False
        self.speech = SpeechWorker(self)
        self.speech.started_speaking.connect(self.speech_started)
        self.speech.finished.connect(self.speech_finished)
        self.speech.start()
        self.speech.feed(text)
        self.speech.finish_input()

    def speech_finished(self) -> None:
        self._speech_finished = True
        self.speech = None
        self.set_state("idle")
        if self.popup:
            self.popup.set_activity(
                "Stage: response fully spoken. Listening for your next command…"
            )
        self._maybe_listen()

    def _maybe_listen(self) -> None:
        if self._generation_finished and self._speech_finished:
            QTimer.singleShot(350, self.listen)

    def interrupt(self) -> None:
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
        self.show_popup()
        self.popup.text.setText("Interrupted. Standing by.")
        self.popup.set_activity("Stage: interrupted by Founder.")

    def stop_voice(self) -> None:
        if self.voice and self.voice.isRunning():
            self.voice.stop()
            self.voice.wait(300)
        self.voice = None

    def voice_error(self, message: str) -> None:
        self.set_state("error")
        self.show_popup()
        self.popup.text.setText("Microphone error:\n" + message)
        self.popup.set_activity("Stage: microphone error.")

    def reply_error(self, message: str) -> None:
        self._generation_finished = True
        self._speech_finished = True
        if self.speech and self.speech.isRunning():
            self.speech.stop()
            self.speech.wait(250)
            self.speech = None
        self.set_state("error")
        self.show_popup()
        self.popup.text.setText("Brain error:\n" + message)
        self.popup.set_activity("Stage: model error. Ready to retry.")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = self.rect().center()
        color = self.COLORS[self.state]

        pulse = math.sin(self.phase) * 3.0
        ring = 42 + pulse

        # Layered ambient glow.
        for radius, alpha in (
            (61 + pulse, 8),
            (55 + pulse, 12),
            (49 + pulse, 18),
        ):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), alpha))
            painter.drawEllipse(center, radius, radius)

        # Rotating ring.
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 90), 1.4))
        painter.drawEllipse(center, ring, ring)

        painter.setPen(QPen(color, 2.2))
        painter.drawArc(
            QRectF(center.x() - 56, center.y() - 56, 112, 112),
            int((self.phase * 700) % 360) * 16,
            82 * 16,
        )

        # Six orbiting particles.
        painter.setPen(Qt.NoPen)
        for index in range(6):
            angle = self.phase * (1.0 + index * 0.05) + index * math.tau / 6
            radius = 50 + 4 * math.sin(self.phase * 1.5 + index)
            px = center.x() + math.cos(angle) * radius
            py = center.y() + math.sin(angle) * radius
            size = 2.2 + (1.0 if self.state != "idle" else 0.0)
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 210))
            painter.drawEllipse(QPoint(int(px), int(py)), int(size), int(size))

        # Core.
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
            QRectF(0, 119, self.width(), 14),
            Qt.AlignCenter,
            self.state.upper(),
        )

    def closeEvent(self, event) -> None:
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

    splash = StartupSplash()
    splash.show()

    worker = StartupWorker(splash)

    def on_ready() -> None:
        orb = GenesisOrb()
        orb.setWindowOpacity(0.0)
        orb.show()
        orb.raise_()
        app.processEvents()

        fade_in = QPropertyAnimation(orb, b"windowOpacity", orb)
        fade_in.setDuration(260)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.OutCubic)

        fade_out = QPropertyAnimation(splash, b"windowOpacity", splash)
        fade_out.setDuration(220)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.InCubic)

        fade_out.finished.connect(splash.close)
        fade_out.finished.connect(splash.deleteLater)
        fade_out.finished.connect(worker.deleteLater)

        # Keep animation objects alive until both transitions finish.
        orb._boot_fade_in = fade_in
        splash._boot_fade_out = fade_out

        fade_in.start()
        fade_out.start()

    def on_failed(message: str) -> None:
        splash.set_status("Startup warning — continuing…")
        splash.set_progress(100)

        def continue_start() -> None:
            splash.close()
            splash.deleteLater()
            worker.deleteLater()

            orb = GenesisOrb()
            orb.show()
            orb.show_popup()
            orb.set_state("error")
            orb.popup.text.setText("Model warm-up warning:\n" + message)
            orb.popup.set_activity(
                "Startup could not fully warm the models. "
                "The first request may take longer."
            )

        QTimer.singleShot(1200, continue_start)

    worker.status.connect(splash.set_status)
    worker.progress.connect(splash.set_progress)
    worker.ready.connect(on_ready)
    worker.failed.connect(on_failed)
    worker.start()

    return app.exec()
