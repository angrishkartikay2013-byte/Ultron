from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from runtime.token_state import get


class TokenMeter(QWidget):
    """Minimal always-on-top UI: only the current context tokens remaining."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(190, 32)

        self.label = QLabel("TOKENS LEFT 0", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setGeometry(0, 0, 190, 32)
        self.label.setStyleSheet(
            "QLabel{"
            "background:#0d1117;"
            "color:#dbe7f7;"
            "border:1px solid #252d38;"
            "border-radius:8px;"
            "padding:4px 8px;"
            "font-size:10px;"
            "font-weight:700;"
            "}"
        )

        screen = QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.move(area.right() - self.width() - 18, area.top() + 18)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(250)

    def refresh(self) -> None:
        snapshot = get()
        self.label.setText(f"TOKENS LEFT {snapshot.remaining_tokens:,}")

    def closeEvent(self, event) -> None:
        self.timer.stop()
        super().closeEvent(event)
