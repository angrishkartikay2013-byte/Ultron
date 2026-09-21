from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

GRAPH_FILE = Path("memory") / "graph.json"


@dataclass
class GalaxyNode:
    id: str
    label: str
    description: str
    color: QColor
    links: list[str]
    x: float
    y: float
    z: float


class GalaxyWidget(QWidget):
    node_selected = Signal(object)

    def __init__(self, callback=None, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(700, 500)
        self.setMouseTracking(True)

        data = json.loads(GRAPH_FILE.read_text(encoding="utf-8"))
        raw_nodes = data.get("nodes", [])
        self.nodes: list[GalaxyNode] = []

        # Fibonacci-like 3D distribution gives the graph real depth instead of
        # putting every node on one flat circle.
        count = max(1, len(raw_nodes))
        golden = math.pi * (3.0 - math.sqrt(5.0))

        for i, item in enumerate(raw_nodes):
            y = 1.0 - (2.0 * i) / max(1, count - 1)
            radius = math.sqrt(max(0.0, 1.0 - y * y))
            theta = golden * i
            self.nodes.append(
                GalaxyNode(
                    id=item["id"],
                    label=item["label"],
                    description=item["description"],
                    color=QColor(item["color"]),
                    links=item.get("links", []),
                    x=math.cos(theta) * radius * 2.7,
                    y=y * 2.7,
                    z=math.sin(theta) * radius * 2.7,
                )
            )

        self.lookup = {node.id: node for node in self.nodes}
        self.selected = self.nodes[0] if self.nodes else None
        self.yaw = 0.25
        self.pitch = -0.18
        self.zoom = 1.0
        self.pan = QPointF(0.0, 0.0)
        self._drag_start = None
        self._drag_origin = None
        self._dragging = False
        self._hovered = None
        self._phase = 0.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(16)

        if self.selected and callback:
            callback(self.selected)

    def animate(self) -> None:
        self._phase += 0.018
        self.update()

    def _rotate(self, x: float, y: float, z: float) -> tuple[float, float, float]:
        cy = math.cos(self.yaw)
        sy = math.sin(self.yaw)
        x1 = x * cy - z * sy
        z1 = x * sy + z * cy

        cp = math.cos(self.pitch)
        sp = math.sin(self.pitch)
        y1 = y * cp - z1 * sp
        z2 = y * sp + z1 * cp
        return x1, y1, z2

    def _project(self, node: GalaxyNode) -> tuple[QPointF, float, float] | None:
        x, y, z = self._rotate(node.x, node.y, node.z)
        camera = 8.0
        depth = camera - z

        if depth <= 0.3:
            return None

        scale = (min(self.width(), self.height()) * 0.23 * self.zoom) / depth
        sx = self.width() * 0.47 + self.pan.x() + x * scale
        sy = self.height() * 0.50 + self.pan.y() - y * scale
        return QPointF(sx, sy), scale, depth

    def _node_radius(self, scale: float, selected: bool) -> float:
        base = max(7.0, min(26.0, scale * 0.16))
        return base + (4.0 if selected else 0.0)

    def _select_at(self, position: QPointF) -> GalaxyNode | None:
        best = None
        best_distance = 34.0

        for node in self.nodes:
            projected = self._project(node)
            if projected is None:
                continue
            point, scale, depth = projected
            radius = self._node_radius(scale, node is self.selected) + 5
            distance = math.hypot(position.x() - point.x(), position.y() - point.y())
            if distance <= radius and distance < best_distance:
                best = node
                best_distance = distance

        return best

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        factor = 1.12 if delta > 0 else 1 / 1.12
        self.zoom = max(0.55, min(4.2, self.zoom * factor))
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position()
            self._drag_origin = (self.yaw, self.pitch, self.pan)
            self._dragging = False

    def mouseMoveEvent(self, event) -> None:
        if self._drag_start is None or self._drag_origin is None:
            return

        delta = event.position() - self._drag_start
        if abs(delta.x()) + abs(delta.y()) > 5:
            self._dragging = True

        if self._dragging:
            self.yaw = self._drag_origin[0] + delta.x() * 0.008
            self.pitch = max(
                -1.25,
                min(1.25, self._drag_origin[1] + delta.y() * 0.008),
            )
            self.pan = QPointF(
                self._drag_origin[2].x() + delta.x() * 0.7,
                self._drag_origin[2].y() + delta.y() * 0.7,
            )
            self.update()

        self._hovered = self._select_at(event.position())
        self.setCursor(Qt.OpenHandCursor if self._hovered else Qt.ArrowCursor)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return

        if not self._dragging:
            node = self._select_at(event.position())
            if node is not None:
                self.selected = node
                self.node_selected.emit(node)

        self._drag_start = None
        self._drag_origin = None
        self._dragging = False
        self.update()

    def mouseDoubleClickEvent(self, event) -> None:
        node = self._select_at(event.position())
        if node is not None:
            self.selected = node
            self.zoom = min(4.2, self.zoom * 1.35)
            self.node_selected.emit(node)
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#020711"))

        # star field
        painter.setPen(Qt.NoPen)
        for i in range(220):
            x = (i * 97 + 31) % max(1, self.width())
            y = (i * 47 + 17) % max(1, self.height())
            alpha = 24 + ((i * 19) % 70)
            painter.setBrush(QColor(110, 210, 255, alpha))
            painter.drawEllipse(QPointF(x, y), 0.8 + (i % 3) * 0.25, 0.8 + (i % 3) * 0.25)

        projected: dict[str, tuple[QPointF, float, float]] = {}
        for node in self.nodes:
            p = self._project(node)
            if p:
                projected[node.id] = p

        # connections
        for node in self.nodes:
            if node.id not in projected:
                continue
            a = projected[node.id][0]
            for linked in node.links:
                if linked not in projected:
                    continue
                b = projected[linked][0]
                opacity = 35 if linked != (self.selected.id if self.selected else "") else 90
                painter.setPen(QPen(QColor(80, 200, 255, opacity), 1.0))
                painter.drawLine(a, b)

        # draw far nodes first
        ordered = sorted(
            self.nodes,
            key=lambda node: projected.get(node.id, (QPointF(), 0, 999))[2],
            reverse=True,
        )

        for node in ordered:
            if node.id not in projected:
                continue

            point, scale, depth = projected[node.id]
            selected = node is self.selected
            hovered = node is self._hovered
            radius = self._node_radius(scale, selected)

            pulse = math.sin(self._phase * 3.0 + hash(node.id) % 17) * 2.0
            glow_radius = radius + 8 + pulse

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(node.color.red(), node.color.green(), node.color.blue(), 26))
            painter.drawEllipse(point, glow_radius * 1.8, glow_radius * 1.8)
            painter.setBrush(QColor(node.color.red(), node.color.green(), node.color.blue(), 50))
            painter.drawEllipse(point, glow_radius, glow_radius)

            painter.setBrush(node.color)
            painter.setPen(QPen(QColor(230, 250, 255, 190), 1 if selected or hovered else 0))
            painter.drawEllipse(point, radius, radius)

            if selected:
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(QColor(255, 255, 255, 220), 1.5))
                painter.drawEllipse(point, radius + 7, radius + 7)

            label_size = max(8, min(13, int(8 + scale * 0.025)))
            painter.setPen(QColor(225, 247, 255, 220))
            painter.setFont(QFont("Segoe UI", label_size, QFont.Bold))
            painter.drawText(
                point.x() - 70,
                point.y() + radius + 18,
                140,
                18,
                Qt.AlignCenter,
                node.label,
            )

        # HUD
        painter.setPen(QColor(95, 220, 255, 150))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.drawText(20, 28, "MEMORY GALAXY")
        painter.setPen(QColor(120, 150, 175, 150))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(20, 47, "Drag to orbit  •  Wheel to zoom  •  Click a node")
