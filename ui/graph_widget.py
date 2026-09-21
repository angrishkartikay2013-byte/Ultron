
import json
import math
from pathlib import Path

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QColor,QPainter,QPen,QBrush,QFont
from PySide6.QtCore import Qt,QPointF,QTimer

GRAPH_FILE = Path("memory/graph.json")

class BrainCell:
    def __init__(self,data,angle,radius):

        self.id=data["id"]
        self.label=data["label"]
        self.description=data["description"]
        self.links=data["links"]

        self.color=QColor(data["color"])

        self.radius=radius
        self.angle=angle

        self.size=24
        self.pulse=0

        self.update()

    def update(self):
        self.x=math.cos(self.angle)*self.radius
        self.y=math.sin(self.angle)*self.radius

class MemoryGraph(QWidget):

    def __init__(self,callback):
        super().__init__()

        with open(GRAPH_FILE,"r") as f:
            graph=json.load(f)

        self.callback=callback

        self.cells=[]

        total=len(graph["nodes"])

        for i,node in enumerate(graph["nodes"]):

            angle=(math.pi*2/total)*i

            radius=0 if node["id"]=="kartikay" else 230

            self.cells.append(
                BrainCell(node,angle,radius)
            )

        self.selected=self.cells[0]
        self.callback(self.selected)

        self.zoom=1
        self.offset=QPointF(0,0)

        self.drag=False
        self.last_pos=None

        self.rotation=0

        self.timer=QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(16)

    def animate(self):

        self.rotation+=0.003

        for i,cell in enumerate(self.cells):

            if cell.radius>0:
                cell.angle+=0.0008
                cell.update()

            cell.pulse+=0.08

        self.update()

    def wheelEvent(self,event):

        if event.angleDelta().y()>0:
            self.zoom*=1.1
        else:
            self.zoom/=1.1

        self.zoom=max(.5,min(self.zoom,3))

        self.update()

    def mousePressEvent(self,event):
        self.drag=True
        self.last_pos=event.pos()

    def mouseMoveEvent(self,event):

        if self.drag:
            diff=event.pos()-self.last_pos
            self.offset+=diff
            self.last_pos=event.pos()
            self.update()

    def mouseReleaseEvent(self,event):

        self.drag=False

        cx=self.width()/2+self.offset.x()
        cy=self.height()/2+self.offset.y()

        for cell in self.cells:

            x=cx+cell.x*self.zoom
            y=cy+cell.y*self.zoom

            if math.hypot(event.position().x()-x,event.position().y()-y)<cell.size+5:
                self.selected=cell
                self.callback(cell)
                break

        self.update()

    def paintEvent(self,event):

        p=QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        p.fillRect(self.rect(),QColor("#040816"))

        cx=self.width()/2+self.offset.x()
        cy=self.height()/2+self.offset.y()

        p.setPen(Qt.NoPen)

        for i in range(250):

            x=(i*53)%self.width()
            y=(i*97)%self.height()

            p.setBrush(QColor(70,180,255,35))
            p.drawEllipse(QPointF(x,y),1.3,1.3)

        pen=QPen(QColor(50,200,255,70),2)
        p.setPen(pen)

        center=self.cells[0]

        for cell in self.cells[1:]:

            p.drawLine(
                QPointF(cx,cy),
                QPointF(cx+cell.x*self.zoom,cy+cell.y*self.zoom)
            )

        p.setPen(Qt.NoPen)

        for cell in self.cells:

            x=cx+cell.x*self.zoom
            y=cy+cell.y*self.zoom

            glow=cell.size+math.sin(cell.pulse)*4

            p.setBrush(QColor(cell.color.red(),cell.color.green(),cell.color.blue(),35))
            p.drawEllipse(QPointF(x,y),glow,glow)

            p.setBrush(cell.color)
            p.drawEllipse(QPointF(x,y),cell.size,cell.size)

            if cell==self.selected:
                p.setPen(QPen(Qt.white,2))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(QPointF(x,y),cell.size+7,cell.size+7)

            p.setPen(Qt.white)
            p.setFont(QFont("Segoe UI",9,QFont.Bold))
            p.drawText(x-35,y+40,cell.label)