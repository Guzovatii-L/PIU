import math
from typing import Tuple

from PySide6 import QtWidgets, QtGui
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QPainterPath
from PySide6.QtWidgets import QGraphicsScene

from constants import GRID_SIZE, SCENE_MARGIN
from furniture import FurnitureItem


class PlanItem: 
    def __init__(self, kind: str, graphics_item):
        self.kind = kind
        self.item = graphics_item


class CanvasScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(-SCENE_MARGIN, -SCENE_MARGIN, 2 * SCENE_MARGIN, 2 * SCENE_MARGIN)
        self._current_item = None
        self._items = []
        self.parent_widget = parent

    def snap_to_grid(self, pos: QPointF) -> QPointF:
        x = round(pos.x() / GRID_SIZE) * GRID_SIZE
        y = round(pos.y() / GRID_SIZE) * GRID_SIZE
        return QPointF(x, y)

    def add_wall(self, start: QPointF, end: QPointF) -> QtWidgets.QGraphicsLineItem:
        pen = QPen(Qt.black, 6)
        return self.addLine(start.x(), start.y(), end.x(), end.y(), pen)

    def add_door(self, start: QPointF, end: QPointF) -> Tuple[QtWidgets.QGraphicsLineItem, QtWidgets.QGraphicsPathItem]:
        line_pen = QPen(Qt.blue, 3)
        line_item = self.addLine(start.x(), start.y(), end.x(), end.y(), line_pen)

        swing_radius = math.hypot(end.x() - start.x(), end.y() - start.y())
        path = QtGui.QPainterPath(start)
        path.arcTo(start.x() - swing_radius, start.y() - swing_radius,
                    swing_radius * 2, swing_radius * 2, 0, 90)
        arc_item = QtWidgets.QGraphicsPathItem(path)
        arc_item.setPen(QPen(Qt.blue, 1))
        arc_item.setBrush(QColor(0, 0, 255, 50))
        self.addItem(arc_item)

        return (line_item, arc_item)

    def add_window(self, start: QPointF, end: QPointF) -> QtWidgets.QGraphicsLineItem:
        pen = QPen(Qt.red, 3, Qt.DashLine)
        line_item = self.addLine(start.x(), start.y(), end.x(), end.y(), pen)

        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = 10
        if dx == 0: 
            self.addLine(start.x() - length / 2, start.y(), start.x() + length / 2, start.y(), QPen(Qt.red, 2))
            self.addLine(end.x() - length / 2, end.y(), end.x() + length / 2, end.y(), QPen(Qt.red, 2))
        else: 
            self.addLine(start.x(), start.y() - length / 2, start.x(), start.y() + length / 2, QPen(Qt.red, 2))
            self.addLine(end.x(), end.y() - length / 2, end.x(), end.y() + length / 2, QPen(Qt.red, 2))

        return line_item

    def add_bed(self, center: QPointF) -> FurnitureItem:
        w, h = 200.0, 160.0
        x, y = center.x() - w / 2, center.y() - h / 2
        item = FurnitureItem("Bed", x, y, w, h)
        self.addItem(item)
        return item

    def add_table(self, center: QPointF) -> FurnitureItem:
        w, h = 200.0, 110.0
        x, y = center.x() - w / 2, center.y() - h / 2
        item = FurnitureItem("Table", x, y, w, h)
        self.addItem(item)
        return item

    def add_sofa(self, center: QPointF) -> FurnitureItem:
        w, h = 260.0, 90.0
        x, y = center.x() - w / 2, center.y() - h / 2
        item = FurnitureItem("Sofa", x, y, w, h)
        self.addItem(item)
        return item

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        from furniture import ResizeHandle 

        hit = self.itemAt(event.scenePos(), QtGui.QTransform())
        if isinstance(hit, (FurnitureItem, ResizeHandle)):
            super().mousePressEvent(event)
            return
        
        mode = getattr(self.parent_widget, "_current_mode", None)

        if event.button() == Qt.LeftButton and mode in ("Wall", "Door", "Window"):
            pos = self.snap_to_grid(event.scenePos())
            kind = mode

            if self._current_item is None:
                if kind == "Wall":
                    self._current_item = self.add_wall(pos, pos)
                elif kind == "Door":
                    self._current_item = self.add_door(pos, pos)
                elif kind == "Window":
                    self._current_item = self.add_window(pos, pos)
            else:
                self._items.append(self._current_item)
                self._current_item = None
        
        elif event.button() == Qt.LeftButton:
            pos = self.snap_to_grid(event.scenePos())
            if mode == "Furniture: Bed":
                self._items.append(self.add_bed(pos))
                if self.parent_widget: self.parent_widget.set_mode("Select")
            elif mode == "Furniture: Sofa":
                self._items.append(self.add_sofa(pos))
                if self.parent_widget: self.parent_widget.set_mode("Select")
            elif mode == "Furniture: Table":
                self._items.append(self.add_table(pos))
                if self.parent_widget: self.parent_widget.set_mode("Select")

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        if self._current_item is not None:
            end = self.snap_to_grid(event.scenePos())
            
            if isinstance(self._current_item, QtWidgets.QGraphicsLineItem):
                line = self._current_item.line()
                line.setP2(end)
                self._current_item.setLine(line)
            elif isinstance(self._current_item, tuple):
                line, arc = self._current_item
                start_point = QPointF(line.line().x1(), line.line().y1())
                line.setLine(start_point.x(), start_point.y(), end.x(), end.y())

                dx = end.x() - start_point.x()
                dy = end.y() - start_point.y()
                swing_radius = math.hypot(dx, dy)
                
                path = QtGui.QPainterPath(start_point)
                path.arcTo(start_point.x() - swing_radius, start_point.y() - swing_radius,
                           swing_radius * 2, swing_radius * 2, 0, 90)
                arc.setPath(path)
        
        super().mouseMoveEvent(event)

    def drawBackground(self, painter: QPainter, rect: QRectF):
        painter.save()
        painter.fillRect(rect, Qt.white)

        step = GRID_SIZE
        left = int(math.floor(rect.left() / step) * step)
        top = int(math.floor(rect.top() / step) * step)

        painter.setPen(QPen(QColor(0, 0, 0, 80), 1)) 
        y = top
        while y < rect.bottom():
            painter.drawLine(rect.left(), y, rect.right(), y)
            y += step
        x = left
        while x < rect.right():
            painter.drawLine(x, rect.top(), x, rect.bottom())
            x += step

