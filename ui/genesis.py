from __future__ import annotations

from PySide6.QtWidgets import QApplication

from .chat import open_chat_window


def open_memory_galaxy():
    from .galaxy_widget import GalaxyWidget
    from .sidebar import MemoryVault

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMainWindow, QVBoxLayout, QWidget

    window = QMainWindow()
    window.setWindowTitle("ULTRON • Memory Galaxy")
    window.resize(1500, 900)
    window.setMinimumSize(1000, 650)

    root = QWidget()
    window.setCentralWidget(root)

    layout = QVBoxLayout(root)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    header = QFrame()
    header.setFixedHeight(64)
    header.setStyleSheet("QFrame{background:#0b0d10;border-bottom:1px solid #252a31;}")

    bar = QHBoxLayout(header)
    bar.setContentsMargins(24, 0, 24, 0)

    title = QLabel("ULTRON")
    title.setStyleSheet("color:#f2f4f7;font-size:18px;font-weight:700;")

    subtitle = QLabel("MEMORY GALAXY")
    subtitle.setStyleSheet("color:#9299a4;font-size:10px;font-weight:600;")

    status = QLabel("LOCAL  •  MEMORY")
    status.setAlignment(Qt.AlignRight)
    status.setStyleSheet("color:#72d6a1;font-size:10px;font-weight:600;")

    bar.addWidget(title)
    bar.addSpacing(14)
    bar.addWidget(subtitle)
    bar.addStretch()
    bar.addWidget(status)
    layout.addWidget(header)

    body = QHBoxLayout()
    body.setContentsMargins(0, 0, 0, 0)
    body.setSpacing(0)

    sidebar = MemoryVault()
    graph = GalaxyWidget(sidebar.update_info)

    body.addWidget(graph, 1)
    body.addWidget(sidebar)
    layout.addLayout(body)

    return window


def run_memory_galaxy() -> int:
    app = QApplication.instance() or QApplication([])
    window = open_memory_galaxy()
    window.show()
    app.aboutToQuit.connect(window.close)
    return app.exec()


def open_chat() -> object:
    return open_chat_window()


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    window = open_chat_window()
    app.aboutToQuit.connect(window.close)
    raise SystemExit(app.exec())
