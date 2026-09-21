from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QVBoxLayout, QWidget

from .galaxy_widget import GalaxyWidget
from .sidebar import MemoryVault


class GenesisMemory(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ULTRON GENESIS • Memory Galaxy")
        self.resize(1500, 900)
        self.setMinimumSize(1000, 650)

        root = QWidget()
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(68)
        header.setStyleSheet(
            "QFrame{background:#050b16;border-bottom:1px solid #123b5a;}"
        )

        bar = QHBoxLayout(header)
        bar.setContentsMargins(24, 0, 24, 0)

        title = QLabel("ULTRON GENESIS")
        title.setStyleSheet(
            "color:#67e8f9;font-size:23px;font-weight:800;letter-spacing:1px;"
        )

        subtitle = QLabel("MEMORY GALAXY")
        subtitle.setStyleSheet("color:#64748b;font-size:11px;font-weight:700;")

        status = QLabel("● BRAIN ONLINE")
        status.setAlignment(Qt.AlignRight)
        status.setStyleSheet("color:#55ffad;font-size:11px;font-weight:700;")

        bar.addWidget(title)
        bar.addSpacing(16)
        bar.addWidget(subtitle)
        bar.addStretch()
        bar.addWidget(status)
        layout.addWidget(header)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.sidebar = MemoryVault()
        self.graph = GalaxyWidget(self.sidebar.update_info)

        body.addWidget(self.graph, 1)
        body.addWidget(self.sidebar)
        layout.addLayout(body)


def open_memory_galaxy() -> GenesisMemory:
    window = GenesisMemory()
    window.show()
    window.raise_()
    window.activateWindow()
    return window


def run_memory_galaxy() -> int:
    app = QApplication.instance() or QApplication([])
    window = open_memory_galaxy()
    app.aboutToQuit.connect(window.close)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run_memory_galaxy())
