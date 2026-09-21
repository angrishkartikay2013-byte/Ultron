
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QFrame
from PySide6.QtCore import Qt

from graph_widget import MemoryGraph
from sidebar import MemoryVault

class Genesis(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("ULTRON GENESIS v0.2.0 Alpha")

        self.resize(1500,900)

        self.setStyleSheet("""
            QMainWindow{
                background:#040816;
            }

            QLabel{
                color:white;
            }
        """)

        root=QWidget()
        self.setCentralWidget(root)

        layout=QVBoxLayout(root)
        layout.setContentsMargins(0,0,0,0)

        top=QFrame()
        top.setFixedHeight(70)

        top.setStyleSheet("""
            background:#050B16;
            border-bottom:1px solid #123B5A;
        """)

        bar=QHBoxLayout(top)

        title=QLabel("ULTRON GENESIS")
        title.setStyleSheet("""
            color:#67E8F9;
            font-size:24px;
            font-weight:bold;
        """)

        status=QLabel("🧠 Brain Online")
        status.setAlignment(Qt.AlignRight)

        status.setStyleSheet("""
            color:#38BDF8;
            font-size:12px;
        """)

        bar.addWidget(title)
        bar.addStretch()
        bar.addWidget(status)

        layout.addWidget(top)

        body=QHBoxLayout()

        self.sidebar=MemoryVault()

        graph=MemoryGraph(self.sidebar.update_info)

        body.addWidget(graph,4)
        body.addWidget(self.sidebar,1)

        layout.addLayout(body)

app=QApplication([])

window=Genesis()
window.show()

app.exec()