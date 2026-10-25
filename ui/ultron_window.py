from __future__ import annotations

import html
import math
import random

from PySide6.QtCore import Qt, QTimer, Signal, QRectF
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

INK = "#03090b"
PANEL = "#071114"
PANEL_2 = "#09191b"
TEAL = "#45f5df"
TEAL_DIM = "#168f88"
TEAL_DARK = "#0c3839"
ORANGE = "#ff7845"
TEXT = "#d9fff9"
MUTED = "#679b98"
BORDER = "#14524f"


def _label(text: str, *, size: int = 10, color: str = MUTED, bold: bool = False) -> QLabel:
    item = QLabel(text)
    item.setFont(QFont("Consolas", size, QFont.Bold if bold else QFont.Normal))
    item.setStyleSheet(f"color:{color}; background:transparent;")
    return item


class OrbButton(QWidget):
    """Animated circular core; clicking it opens the conversation workspace."""
    activated = Signal()

    def __init__(self, size: int = 320) -> None:
        super().__init__()
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(40)

    def _tick(self) -> None:
        self.phase = (self.phase + 1.1) % 360
        self.update()

    def paintEvent(self, _event) -> None:
        side = min(self.width(), self.height())
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.translate(self.width() / 2, self.height() / 2)
        r = side * 0.46

        # Outer atmospheric halo.
        halo = QRadialGradient(0, 0, r * 1.04)
        halo.setColorAt(0.0, QColor(15, 135, 128, 34))
        halo.setColorAt(0.52, QColor(8, 65, 67, 23))
        halo.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(halo)
        p.drawEllipse(QRectF(-r * 1.04, -r * 1.04, r * 2.08, r * 2.08))

        # Concentric HUD rings.
        for radius, width, color, alpha in [
            (r, 1.4, TEAL, 180),
            (r * 0.92, 1.0, TEAL_DIM, 180),
            (r * 0.82, 1.0, TEAL, 105),
            (r * 0.71, 1.5, ORANGE, 185),
            (r * 0.61, 1.0, TEAL, 160),
            (r * 0.48, 1.0, TEAL_DIM, 210),
        ]:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(color), width, Qt.SolidLine))
            p.drawEllipse(QRectF(-radius, -radius, radius * 2, radius * 2))

        # Rotating segmented arcs and angular indicators.
        p.save()
        p.rotate(self.phase)
        p.setPen(QPen(QColor(TEAL), 3.0))
        p.drawArc(QRectF(-r * 0.88, -r * 0.88, r * 1.76, r * 1.76), 18 * 16, 72 * 16)
        p.setPen(QPen(QColor(ORANGE), 2.5))
        p.drawArc(QRectF(-r * 0.76, -r * 0.76, r * 1.52, r * 1.52), 190 * 16, 46 * 16)
        p.setPen(QPen(QColor(TEAL), 1.5))
        p.drawArc(QRectF(-r * 0.57, -r * 0.57, r * 1.14, r * 1.14), 32 * 16, 105 * 16)
        p.restore()

        # Fine radial tick marks.
        for i in range(64):
            angle = math.radians(i * 360 / 64 + self.phase * 0.12)
            outer = r * (0.96 if i % 4 else 1.015)
            inner = r * (0.90 if i % 4 else 0.86)
            p.setPen(QPen(QColor(TEAL if i % 8 else ORANGE), 1.2 if i % 4 else 1.8))
            p.drawLine(
                int(math.cos(angle) * inner), int(math.sin(angle) * inner),
                int(math.cos(angle) * outer), int(math.sin(angle) * outer),
            )

        # Dense luminous central core.
        core_r = r * 0.39
        core = QRadialGradient(-core_r * 0.15, -core_r * 0.2, core_r * 1.3)
        core.setColorAt(0.0, QColor(96, 255, 237, 220))
        core.setColorAt(0.18, QColor(22, 183, 171, 190))
        core.setColorAt(0.48, QColor(5, 78, 79, 235))
        core.setColorAt(0.82, QColor(3, 23, 28, 250))
        core.setColorAt(1.0, QColor(2, 9, 11, 255))
        p.setPen(QPen(QColor(TEAL), 1.3))
        p.setBrush(core)
        p.drawEllipse(QRectF(-core_r, -core_r, core_r * 2, core_r * 2))

        # Inner reticle and orange pulse.
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(TEAL), 1.0))
        p.drawEllipse(QRectF(-core_r * 0.56, -core_r * 0.56, core_r * 1.12, core_r * 1.12))
        p.setPen(QPen(QColor(ORANGE), 1.6))
        p.drawArc(QRectF(-core_r * 0.72, -core_r * 0.72, core_r * 1.44, core_r * 1.44),
                  int((self.phase * 2) % 360) * 16, 54 * 16)
        p.setPen(QPen(QColor(TEAL), 1.0))
        p.drawLine(-core_r * 0.2, 0, core_r * 0.2, 0)
        p.drawLine(0, -core_r * 0.2, 0, core_r * 0.2)
        p.setPen(QPen(QColor(ORANGE), 2.0))
        p.setBrush(QColor(ORANGE))
        p.drawEllipse(QRectF(-3, -3, 6, 6))
        p.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.activated.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class HudPanel(QFrame):
    def __init__(self, heading: str, rows: list[tuple[str, str]]) -> None:
        super().__init__()
        self.setObjectName("hudPanel")
        self.setMinimumWidth(185)
        self.setMaximumWidth(225)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(13)
        head = _label(heading.upper(), size=10, color=TEAL, bold=True)
        layout.addWidget(head)
        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet(f"background:{BORDER}; border:0;")
        layout.addWidget(rule)
        self.values: dict[str, QLabel] = {}
        for title, value in rows:
            layout.addWidget(_label(title.upper(), size=8, color=MUTED))
            val = _label(value, size=10, color=TEXT, bold=True)
            val.setWordWrap(True)
            layout.addWidget(val)
            self.values[title] = val
        layout.addStretch(1)
        self.setStyleSheet(
            f"QFrame#hudPanel{{background:rgba(5,17,20,210); border:1px solid {BORDER};"
            "border-radius:8px;}"
        )

    def set_value(self, key: str, value: str) -> None:
        if key in self.values:
            self.values[key].setText(value)


class HomePage(QWidget):
    open_cortex = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"background:{INK};")
        self.voice_state = "INITIALIZING"
        self.token_label = _label("CONTEXT  —", size=9, color=TEAL)
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 19, 26, 18)
        root.setSpacing(14)

        top = QHBoxLayout()
        brand = _label("ULTRON", size=18, color=TEAL, bold=True)
        brand.setStyleSheet(f"color:{TEAL}; letter-spacing:4px; background:transparent;")
        top.addWidget(brand)
        top.addSpacing(12)
        top.addWidget(_label("PERSONAL INTELLIGENCE SYSTEM", size=9))
        top.addStretch(1)
        self.link_state = _label("● SYSTEM READY", size=9, color=ORANGE, bold=True)
        top.addWidget(self.link_state)
        root.addLayout(top)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background:{BORDER}; border:0;")
        root.addWidget(divider)

        main = QHBoxLayout()
        main.setSpacing(16)
        self.left = HudPanel("Core systems", [
            ("VOICE", "STANDBY"),
            ("VISION", "READY ON REQUEST"),
            ("MEMORY", "LOCAL"),
            ("AGENCY", "TOOL-CALLING"),
        ])
        main.addWidget(self.left, 0, Qt.AlignVCenter)

        center = QVBoxLayout()
        center.setAlignment(Qt.AlignCenter)
        center.setSpacing(8)
        self.orb = OrbButton(328)
        self.orb.activated.connect(self.open_cortex.emit)
        center.addWidget(self.orb, 0, Qt.AlignCenter)
        tap = _label("CLICK THE CORE TO CONNECT", size=9, color=TEAL, bold=True)
        tap.setAlignment(Qt.AlignCenter)
        center.addWidget(tap)
        hint = _label("VOICE + TEXT  /  TOOL EXECUTION  /  MEMORY", size=8)
        hint.setAlignment(Qt.AlignCenter)
        center.addWidget(hint)
        main.addLayout(center, 1)

        self.right = HudPanel("Mission interface", [
            ("ACTIVE MISSION", "NONE"),
            ("MODEL", "LOCAL OLLAMA"),
            ("INPUT", "VOICE + TEXT"),
            ("INTERRUPT", "CTRL + Y"),
        ])
        main.addWidget(self.right, 0, Qt.AlignVCenter)
        root.addLayout(main, 1)

        bottom = QHBoxLayout()
        self.status_label = _label("● VOICE ENGINE STARTING", size=9, color=ORANGE)
        bottom.addWidget(self.status_label)
        bottom.addStretch(1)
        bottom.addWidget(self.token_label)
        bottom.addStretch(1)
        bottom.addWidget(_label("LOCAL-FIRST • WINDOWS", size=8))
        root.addLayout(bottom)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(12, 63, 62, 70), 1))
        step = 34
        for x in range(0, self.width(), step):
            p.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), step):
            p.drawLine(0, y, self.width(), y)
        p.setPen(QPen(QColor(255, 120, 69, 115), 1.2))
        margin = 12
        corner = 24
        for x, y, dx, dy in [
            (margin, margin, 1, 1),
            (self.width() - margin, margin, -1, 1),
            (margin, self.height() - margin, 1, -1),
            (self.width() - margin, self.height() - margin, -1, -1),
        ]:
            p.drawLine(x, y, x + dx * corner, y)
            p.drawLine(x, y, x, y + dy * corner)
        p.end()

    def set_voice_status(self, status: str) -> None:
        self.voice_state = status
        self.status_label.setText(f"● {status.upper()}")
        self.left.set_value("VOICE", status.upper())
        self.link_state.setText("● SYSTEM READY" if "ERROR" not in status.upper() else "● CHECK VOICE")
        self.link_state.setStyleSheet(
            f"color:{ORANGE if 'ERROR' in status.upper() else TEAL}; background:transparent;"
        )

    def set_tokens(self, remaining: int) -> None:
        self.token_label.setText(f"CONTEXT LEFT  {remaining:,}")


class CortexPage(QWidget):
    go_home = Signal()
    prompt_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"background:{INK};")
        self.busy = False
        root = QVBoxLayout(self)
        root.setContentsMargins(27, 20, 27, 22)
        root.setSpacing(13)

        top = QHBoxLayout()
        self.home_button = QPushButton("‹  CORE")
        self.home_button.setCursor(Qt.PointingHandCursor)
        self.home_button.clicked.connect(self.go_home.emit)
        self.home_button.setFixedWidth(110)
        top.addWidget(self.home_button)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(_label("ULTRON  /  NEURAL INTERFACE", size=13, color=TEAL, bold=True))
        title_col.addWidget(_label("COGNITIVE LINK • LIVE CONVERSATION", size=8))
        top.addLayout(title_col)
        top.addStretch(1)
        self.status_label = _label("● READY", size=9, color=ORANGE, bold=True)
        top.addWidget(self.status_label)
        root.addLayout(top)

        self.transcript = QTextBrowser()
        self.transcript.setOpenExternalLinks(False)
        self.transcript.setStyleSheet(
            f"QTextBrowser{{background:rgba(2,10,12,218);color:{TEXT};"
            f"border:1px solid {BORDER};border-radius:8px;padding:16px;"
            "font-family:Consolas;font-size:11pt;selection-background-color:#14524f;}"
        )
        self.transcript.setPlaceholderText("Your conversation will appear here.")
        root.addWidget(self.transcript, 1)

        bottom = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Tell ULTRON what you need…")
        self.input.returnPressed.connect(self._submit)
        self.input.setMinimumHeight(46)
        bottom.addWidget(self.input, 1)
        self.send_button = QPushButton("TRANSMIT  ↗")
        self.send_button.setCursor(Qt.PointingHandCursor)
        self.send_button.setMinimumHeight(46)
        self.send_button.setMinimumWidth(145)
        self.send_button.clicked.connect(self._submit)
        bottom.addWidget(self.send_button)
        root.addLayout(bottom)
        root.addWidget(_label("ENTER TO SEND  •  CTRL+Y TO INTERRUPT VOICE  •  EXECUTION RESULTS ARE REPORTED", size=8))

        self.setStyleSheet(self.styleSheet() + f"""
            QPushButton {{
                color: {TEAL}; background: rgba(8, 32, 34, 225);
                border: 1px solid {TEAL_DIM}; border-radius: 5px;
                padding: 8px 12px; font-family: Consolas; font-size: 9pt; font-weight: bold;
            }}
            QPushButton:hover {{ background: rgba(17, 78, 75, 235); border-color: {TEAL}; }}
            QPushButton:disabled {{ color: {MUTED}; border-color: {BORDER}; }}
            QLineEdit {{
                color: {TEXT}; background: rgba(3, 14, 16, 238);
                border: 1px solid {BORDER}; border-radius: 5px; padding: 10px;
                font-family: Consolas; font-size: 11pt;
            }}
            QLineEdit:focus {{ border-color: {TEAL}; }}
        """)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rng = random.Random(41)
        points: list[tuple[float, float, int]] = []
        for i in range(76):
            x = rng.random() * self.width()
            y = rng.random() * self.height()
            points.append((x, y, i))
        for i, (x1, y1, idx) in enumerate(points):
            distances = []
            for x2, y2, jdx in points[i + 1:]:
                d = math.hypot(x2 - x1, y2 - y1)
                if d < min(122, self.width() * 0.13):
                    distances.append((d, x2, y2, jdx))
            for d, x2, y2, jdx in sorted(distances)[:3]:
                alpha = max(14, int(75 * (1 - d / 140)))
                p.setPen(QPen(QColor(69, 245, 223, alpha), 0.7))
                p.drawLine(int(x1), int(y1), int(x2), int(y2))
            is_orange = idx % 11 == 0
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 120, 69, 175) if is_orange else QColor(69, 245, 223, 135))
            r = 2.6 if is_orange else 1.6
            p.drawEllipse(QRectF(x1 - r, y1 - r, r * 2, r * 2))
        p.end()

    def _submit(self) -> None:
        prompt = self.input.text().strip()
        if not prompt or self.busy:
            return
        self.input.clear()
        self.prompt_requested.emit(prompt)

    def add_message(self, role: str, message: str) -> None:
        safe = html.escape(message).replace("\n", "<br>")
        if role == "user":
            name, color = "YOU", ORANGE
        elif role == "error":
            name, color = "SYSTEM", ORANGE
        else:
            name, color = "ULTRON", TEAL
        self.transcript.append(
            f'<p style="margin:12px 0 4px 0;color:{color};font-weight:bold;">{name}</p>'
            f'<p style="margin:0 0 12px 0;color:{TEXT};line-height:1.45;">{safe}</p>'
        )
        bar = self.transcript.verticalScrollBar()
        bar.setValue(bar.maximum())

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.send_button.setDisabled(busy)
        self.input.setDisabled(busy)
        self.send_button.setText("THINKING…" if busy else "TRANSMIT  ↗")
        self.set_status("PROCESSING" if busy else "READY")

    def set_status(self, status: str) -> None:
        self.status_label.setText(f"● {status.upper()}")
        self.status_label.setStyleSheet(
            f"color:{ORANGE if 'ERROR' in status.upper() else TEAL}; background:transparent;"
        )

    def set_tokens(self, remaining: int) -> None:
        # Kept as an extensible hook for the HUD's live token meter.
        self.setToolTip(f"Context remaining: {remaining:,}")


class UltronWindow(QWidget):
    """Top-level stacked UI. The orbital HUD opens into the neural chat workspace."""
    prompt_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ULTRON")
        self.setMinimumSize(960, 640)
        self.setStyleSheet(f"background:{INK};")
        self.stack = QStackedWidget(self)
        self.home = HomePage()
        self.cortex = CortexPage()
        self.stack.addWidget(self.home)
        self.stack.addWidget(self.cortex)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.stack)
        self.history: list[tuple[str, str]] = []
        self.home.open_cortex.connect(self.show_cortex)
        self.cortex.go_home.connect(lambda: self.stack.setCurrentWidget(self.home))
        self.cortex.prompt_requested.connect(self.prompt_requested.emit)

    def show_cortex(self) -> None:
        self.stack.setCurrentWidget(self.cortex)
        if not self.history:
            self.cortex.add_message(
                "assistant",
                "Neural link established. I’m ULTRON. Tell me what you want done, and I’ll use the available tools when appropriate."
            )
        else:
            self.cortex.transcript.clear()
            for role, message in self.history:
                self.cortex.add_message(role, message)
        self.cortex.input.setFocus()

    def add_message(self, role: str, message: str) -> None:
        self.history.append((role, message))
        if self.stack.currentWidget() is self.cortex:
            self.cortex.add_message(role, message)

    def set_voice_status(self, status: str) -> None:
        self.home.set_voice_status(status)
        self.cortex.set_status(status)

    def set_tokens(self, remaining: int) -> None:
        self.home.set_tokens(remaining)
        self.cortex.set_tokens(remaining)

    def set_busy(self, busy: bool) -> None:
        self.cortex.set_busy(busy)
