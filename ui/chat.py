from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from brain.agent import stream_prompt
from brain.core import history, reset_memory
from .theme import ACCENT, ACCENT_SOFT, APP_BG, BORDER, MUTED, SIDEBAR_BG, SURFACE, SURFACE_2, TEXT


class ChatWorker(QThread):
    chunk = Signal(str)
    finished_text = Signal(str)
    failed = Signal(str)

    def __init__(self, prompt: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.prompt = prompt

    def run(self) -> None:
        parts: list[str] = []
        try:
            for token in stream_prompt(self.prompt):
                parts.append(token)
                self.chunk.emit(token)
            self.finished_text.emit("".join(parts).strip())
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class MessageBubble(QFrame):
    def __init__(self, role: str, text: str = "") -> None:
        super().__init__()
        self.role = role
        self.setObjectName("userBubble" if role == "Founder" else "assistantBubble")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(5)

        meta = QLabel(role)
        meta.setStyleSheet(
            f"color:{ACCENT if role == 'Founder' else MUTED};"
            "font-size:10px;font-weight:600;"
        )

        self.body = QLabel(text)
        self.body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.body.setWordWrap(True)
        self.body.setStyleSheet(
            f"color:{TEXT};font-size:14px;line-height:1.45;"
        )

        layout.addWidget(meta)
        layout.addWidget(self.body)


class ChatCanvas(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(36, 26, 36, 26)
        self.layout.setSpacing(14)
        self.layout.addStretch()

    def clear_messages(self) -> None:
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.layout.addStretch()

    def add_message(self, role: str, text: str = "") -> MessageBubble:
        bubble = MessageBubble(role, text)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(0 if role == "ULTRON" else 1)
        row.addWidget(bubble, 0 if role == "Founder" else 1)
        row.addStretch(1 if role == "Founder" else 0)
        self.layout.insertLayout(self.layout.count() - 1, row)
        return bubble


class ChatWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ULTRON")
        self.resize(1280, 820)
        self.setMinimumSize(980, 650)
        self.worker: ChatWorker | None = None
        self._assistant_bubble: MessageBubble | None = None

        root = QWidget()
        self.setCentralWidget(root)
        root.setStyleSheet(
            f"QWidget{{background:{APP_BG};color:{TEXT};font-family:'Segoe UI';}}"
            f"QFrame#sidebar{{background:{SIDEBAR_BG};border-right:1px solid {BORDER};}}"
            f"QFrame#topbar{{background:{APP_BG};border-bottom:1px solid {BORDER};}}"
            f"QFrame#userBubble{{background:{ACCENT_SOFT};border:1px solid #29405f;border-radius:14px;}}"
            f"QFrame#assistantBubble{{background:transparent;border:1px solid {BORDER};border-radius:14px;}}"
            f"QPushButton{{background:{SURFACE};color:{TEXT};border:1px solid {BORDER};border-radius:9px;padding:9px 12px;}}"
            f"QPushButton:hover{{background:{SURFACE_2};border-color:#374151;}}"
            f"QPushButton#accent{{background:{ACCENT};color:#08101a;border:none;font-weight:700;}}"
            f"QLineEdit{{background:{SURFACE};color:{TEXT};border:1px solid {BORDER};border-radius:12px;padding:12px 14px;font-size:14px;}}"
            f"QLineEdit:focus{{border:1px solid #4f78b2;}}"
            f"QListWidget{{background:transparent;border:none;color:{MUTED};outline:none;}}"
            f"QListWidget::item{{padding:9px 10px;border-radius:7px;}}"
            f"QListWidget::item:selected{{background:{SURFACE};color:{TEXT};}}"
            f"QScrollArea{{border:none;background:{APP_BG};}}"
        )

        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(270)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 18, 16, 16)
        sidebar_layout.setSpacing(10)

        brand = QLabel("ULTRON")
        brand.setFont(QFont("Segoe UI", 18, QFont.DemiBold))
        brand.setStyleSheet(f"color:{TEXT};")

        subtitle = QLabel("Local intelligence workspace")
        subtitle.setStyleSheet(f"color:{MUTED};font-size:11px;")

        new_chat = QPushButton("+  New chat")
        new_chat.setObjectName("accent")
        new_chat.clicked.connect(self.new_chat)

        memory_btn = QPushButton("Memory Galaxy")
        memory_btn.clicked.connect(self.open_memory)

        sessions = QLabel("RECENT")
        sessions.setStyleSheet(
            f"color:{MUTED};font-size:9px;font-weight:700;letter-spacing:1px;"
        )

        self.session_list = QListWidget()
        self.session_list.setMinimumHeight(180)

        sidebar_layout.addWidget(brand)
        sidebar_layout.addWidget(subtitle)
        sidebar_layout.addSpacing(8)
        sidebar_layout.addWidget(new_chat)
        sidebar_layout.addWidget(memory_btn)
        sidebar_layout.addSpacing(14)
        sidebar_layout.addWidget(sessions)
        sidebar_layout.addWidget(self.session_list, 1)

        footer = QLabel("LOCAL • OLLAMA\nWhisper.cpp • Piper")
        footer.setStyleSheet(f"color:{MUTED};font-size:10px;line-height:1.5;")
        sidebar_layout.addWidget(footer)

        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(64)
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel("Conversation")
        title.setFont(QFont("Segoe UI", 13, QFont.DemiBold))

        status = QLabel("LOCAL  •  READY")
        status.setStyleSheet(f"color:{MUTED};font-size:10px;font-weight:600;")

        top_layout.addWidget(title)
        top_layout.addStretch()
        top_layout.addWidget(status)

        self.scroll = QScrollArea()
        self.canvas = ChatCanvas()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.canvas)

        composer = QFrame()
        composer_layout = QHBoxLayout(composer)
        composer_layout.setContentsMargins(24, 14, 24, 18)
        composer_layout.setSpacing(10)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Message ULTRON…")
        self.input.returnPressed.connect(self.send)

        send = QPushButton("Send")
        send.setObjectName("accent")
        send.clicked.connect(self.send)
        self.send_button = send

        composer_layout.addWidget(self.input, 1)
        composer_layout.addWidget(send)

        main_layout.addWidget(topbar)
        main_layout.addWidget(self.scroll, 1)
        main_layout.addWidget(composer)

        layout.addWidget(sidebar)
        layout.addWidget(main, 1)

        self.reload_history()
        self.input.setFocus()

    def reload_history(self) -> None:
        self.session_list.clear()
        self.canvas.clear_messages()

        for item in history:
            if item.get("role") == "user":
                prompt = str(item.get("content", "")).strip()
                if prompt:
                    self.session_list.addItem(QListWidgetItem(prompt[:34]))
        for item in history:
            role = "Founder" if item.get("role") == "user" else "ULTRON"
            self.canvas.add_message(role, str(item.get("content", "")))
        self._scroll_bottom()

    def _scroll_bottom(self) -> None:
        QApplication.processEvents()
        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def new_chat(self) -> None:
        reset_memory()
        self.reload_history()

    def open_memory(self) -> None:
        from .genesis import open_memory_galaxy
        self.galaxy = open_memory_galaxy()

    def send(self) -> None:
        prompt = self.input.text().strip()
        if not prompt or (self.worker and self.worker.isRunning()):
            return

        self.input.clear()
        self.canvas.add_message("Founder", prompt)
        self._assistant_bubble = self.canvas.add_message("ULTRON", " ")
        self.send_button.setEnabled(False)
        self.input.setEnabled(False)
        self._scroll_bottom()

        self.worker = ChatWorker(prompt, self)
        self.worker.chunk.connect(self.append_chunk)
        self.worker.finished_text.connect(self.finish_reply)
        self.worker.failed.connect(self.fail_reply)
        self.worker.start()

    def append_chunk(self, token: str) -> None:
        if self._assistant_bubble is None:
            return
        current = self._assistant_bubble.body.text()
        self._assistant_bubble.body.setText(current + token)
        self._scroll_bottom()

    def finish_reply(self, text: str) -> None:
        if self._assistant_bubble and not self._assistant_bubble.body.text().strip():
            self._assistant_bubble.body.setText(text or "No response.")
        self.send_button.setEnabled(True)
        self.input.setEnabled(True)
        self.input.setFocus()
        self._assistant_bubble = None
        self._scroll_bottom()

    def fail_reply(self, message: str) -> None:
        if self._assistant_bubble:
            self._assistant_bubble.body.setText(message)
        self.send_button.setEnabled(True)
        self.input.setEnabled(True)
        self.input.setFocus()
        self._assistant_bubble = None
        self._scroll_bottom()


def open_chat_window() -> ChatWindow:
    window = ChatWindow()
    window.show()
    window.raise_()
    window.activateWindow()
    return window


def run_chat() -> int:
    app = QApplication.instance() or QApplication([])
    window = open_chat_window()
    app.aboutToQuit.connect(window.close)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run_chat())
