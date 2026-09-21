
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout
from PySide6.QtGui import QFont

class MemoryVault(QFrame):
    def __init__(self):
        super().__init__()

        self.setFixedWidth(320)

        self.setStyleSheet("""
            QFrame{
                background:#07111E;
                border-left:1px solid #123B5A;
            }

            QLabel{
                color:white;
            }
        """)

        layout = QVBoxLayout(self)

        title = QLabel("MEMORY VAULT")
        title.setStyleSheet("color:#38BDF8;font-size:12px;")

        self.name = QLabel("Kartikay")
        self.name.setFont(QFont("Segoe UI",18,QFont.Bold))

        self.description = QLabel("Welcome to ULTRON Genesis.")
        self.description.setWordWrap(True)
        self.description.setStyleSheet("color:#94A3B8")

        layout.addWidget(title)
        layout.addWidget(self.name)
        layout.addWidget(self.description)

        layout.addSpacing(20)

        connections = QLabel("CONNECTED MEMORIES")
        connections.setStyleSheet("color:#38BDF8;font-size:12px;")
        layout.addWidget(connections)

        self.link_labels = []

        for _ in range(8):
            lbl = QLabel("")
            lbl.setStyleSheet("""
                background:#0B1826;
                padding:8px;
                border-radius:8px;
                color:#E2F3FF;
            """)
            layout.addWidget(lbl)
            self.link_labels.append(lbl)

        layout.addStretch()

        self.status = QLabel("🧠 GENESIS ACTIVE")
        self.status.setStyleSheet("""
            background:#09273A;
            padding:15px;
            border-radius:15px;
            color:#67E8F9;
        """)
        layout.addWidget(self.status)

    def update_info(self, cell):
        self.name.setText(cell.label)
        self.description.setText(cell.description)

        for i,lbl in enumerate(self.link_labels):
            if i < len(cell.links):
                lbl.setText("• "+cell.links[i].title())
            else:
                lbl.setText("")