import math
from typing import Tuple

from PySide6 import QtWidgets, QtGui
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QBrush
from PySide6.QtWidgets import QGraphicsScene
from constants import SCENE_MARGIN, GRID_SIZE


class PlanItem:
    def __init__(self, kind: str, graphics_item):
        self.kind = kind
        self.item = graphics_item


class WallHandle(QtWidgets.QGraphicsEllipseItem):

    def __init__(self, wall_item: 'WallItem', end_index: int):
        self.wall_item = wall_item
        self.end_index = end_index
        radius = 8
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.setPen(QPen(Qt.black, 1))
        self.setBrush(QBrush(Qt.white))
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setZValue(100)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            scene = self.wall_item.scene()
            if hasattr(scene, 'snap_to_grid'):
                new_pos = scene.snap_to_grid(value)
            else:
                new_pos = value

            line = self.wall_item.line()

            if self.end_index == 1:
                line.setP1(new_pos)
            else:
                line.setP2(new_pos)

            self.wall_item.setPos(QPointF(0, 0))

            self.wall_item.setLine(line)

            return new_pos

        return super().itemChange(change, value)


class WallItem(QtWidgets.QGraphicsLineItem):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptHoverEvents(True)
        self._default_pen = QPen(Qt.black, 5)
        self._hover_pen = QPen(QColor(50, 100, 255), 5)
        self.setPen(self._default_pen)
        self.setZValue(10)

        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)

        self.handles = []

    def hoverEnterEvent(self, event):
        self.setPen(self._hover_pen)
        effect = QtWidgets.QGraphicsDropShadowEffect()
        effect.setColor(QColor(100, 150, 255, 180))
        effect.setBlurRadius(10)
        effect.setOffset(0, 0)
        self.setGraphicsEffect(effect)

        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setPen(self._default_pen)
        self.setGraphicsEffect(None)
        super().hoverLeaveEvent(event)

    def _update_handles(self):
        if not self.scene(): return

        line = self.line()
        if not self.handles:
            self.handles.append(WallHandle(self, 1))
            self.handles.append(WallHandle(self, 2))
            for h in self.handles:
                self.scene().addItem(h)
                h.setVisible(self.isSelected())

        self.handles[0].setPos(line.p1())
        self.handles[1].setPos(line.p2())

    def _show_handles(self, show: bool):
        if not self.handles and show:
            self._update_handles()

        for h in self.handles:
            h.setVisible(show)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemSelectedChange:
            self._show_handles(value)

        elif change == QtWidgets.QGraphicsItem.ItemPositionChange:
            scene = self.scene()
            if scene and hasattr(scene, 'snap_to_grid'):
                return scene.snap_to_grid(value)

        elif change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            self._update_handles()

        return super().itemChange(change, value)


class CanvasScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(-SCENE_MARGIN, -SCENE_MARGIN, 2 * SCENE_MARGIN, 2 * SCENE_MARGIN)
        self._current_item = None
        self._items = []
        self._wall_end_markers = []
        self.parent_widget = parent

    def snap_to_grid(self, pos: QPointF) -> QPointF:
        x = round(pos.x() / GRID_SIZE) * GRID_SIZE
        y = round(pos.y() / GRID_SIZE) * GRID_SIZE
        return QPointF(x, y)

    def add_wall(self, start: QPointF, end: QPointF) -> WallItem:
        item = WallItem()
        item.setLine(start.x(), start.y(), end.x(), end.y())
        self.addItem(item)
        return item

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

    def clear_wall_end_markers(self):
        for marker in self._wall_end_markers:
            self.removeItem(marker)
        self._wall_end_markers.clear()

    def show_wall_end_markers(self):
        self.clear_wall_end_markers()

        radius = 4
        for item in self._items:
            if isinstance(item, WallItem):
                line = item.line()
                for pt in (line.p1(), line.p2()):
                    marker = self.addEllipse(pt.x() - radius, pt.y() - radius,
                                             radius * 2, radius * 2,
                                             QPen(Qt.darkGray), QBrush(Qt.green))
                    marker.setZValue(1000)
                    self._wall_end_markers.append(marker)

    def _exit_drawing_mode(self):
        if self._current_item is not None:
            if isinstance(self._current_item, QtWidgets.QGraphicsItem):
                self.removeItem(self._current_item)
            elif isinstance(self._current_item, tuple):
                for item in self._current_item:
                    self.removeItem(item)

            self._current_item = None
            self.show_wall_end_markers()
            if self.parent_widget:
                self.parent_widget.set_mode("Select")


    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        from furniture import ResizeHandle

        if event.button() == Qt.RightButton and self._current_item is not None:
            self._exit_drawing_mode()
            return

        hit = self.itemAt(event.scenePos(), QtGui.QTransform())

        if isinstance(hit, (ResizeHandle, WallHandle)):
            super().mousePressEvent(event)
            return

        mode = getattr(self.parent_widget, "_current_mode", None)

        if event.button() == Qt.LeftButton and mode == "Wall":
            pos = self.snap_to_grid(event.scenePos())

            if self._current_item is None:
                self._current_item = self.add_wall(pos, pos)
                self.clear_wall_end_markers()
            else:
                self._items.append(self._current_item)
                self._current_item = None
                self.show_wall_end_markers()

        elif event.button() == Qt.LeftButton and mode in ("Door", "Window"):
            pos = self.snap_to_grid(event.scenePos())
            kind = mode
            if self._current_item is None:
                if kind == "Door":
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

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self._exit_drawing_mode()
            return

        super().keyPressEvent(event)

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
        painter.restore()