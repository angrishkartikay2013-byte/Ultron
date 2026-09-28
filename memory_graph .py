from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter,QColor,QPen
from PySide6.QtCore import Qt

class MemoryGraph(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ULTRON Memory Galaxy")
        self.resize(1000,700)

    def paintEvent(self,e):
        p=QPainter(self)
        p.fillRect(self.rect(),QColor("#020617"))
        p.setPen(QPen(QColor("#38BDF8"),2))
        p.drawText(40,50,"ULTRON Memory Galaxy v3 Starter")
