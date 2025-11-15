import math
from typing import Tuple

from PySide6 import QtWidgets, QtGui
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QBrush
from PySide6.QtWidgets import QGraphicsScene

from furniture import FurnitureItem
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
            new_pos = scene.snap_to_grid(value) if hasattr(scene, 'snap_to_grid') else value
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
        if not self.scene():
            return
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
        self._door_ccw = True
        self._door_groups = {}
        self._next_door_id = 1
        self._window_groups = {}
        self._next_window_id = 1

    def snap_to_grid(self, pos: QPointF) -> QPointF:
        x = round(pos.x() / GRID_SIZE) * GRID_SIZE
        y = round(pos.y() / GRID_SIZE) * GRID_SIZE
        return QPointF(x, y)

    def _door_path(self, hinge: QPointF, end: QPointF) -> QtGui.QPainterPath:
        dx, dy = end.x() - hinge.x(), end.y() - hinge.y()
        r = max(1.0, math.hypot(dx, dy))
        theta = math.degrees(math.atan2(-dy, dx))
        sweep = 90 if self._door_ccw else -90
        path = QtGui.QPainterPath(hinge)
        path.arcTo(hinge.x() - r, hinge.y() - r, 2 * r, 2 * r, theta, sweep)
        return path

    def toggle_door_swing(self):
        self._door_ccw = not self._door_ccw
        if isinstance(self._current_item, tuple):
            line, arc = self._current_item
            hinge = QPointF(line.line().x1(), line.line().y1())
            end = QPointF(line.line().x2(), line.line().y2())
            arc.setPath(self._door_path(hinge, end))

    def add_wall(self, start: QPointF, end: QPointF) -> WallItem:
        item = WallItem()
        item.setLine(start.x(), start.y(), end.x(), end.y())
        item.setData(0, "wall")
        self.addItem(item)
        return item

    def add_door(self, start: QPointF, end: QPointF) -> Tuple[QtWidgets.QGraphicsLineItem, QtWidgets.QGraphicsPathItem]:
        line_pen = QPen(Qt.blue, 3)
        line_item = self.addLine(start.x(), start.y(), end.x(), end.y(), line_pen)
        arc_item = QtWidgets.QGraphicsPathItem()
        arc_item.setPen(QPen(Qt.blue, 1))
        arc_item.setBrush(QColor(0, 0, 255, 50))
        arc_item.setPath(self._door_path(start, end))
        self.addItem(arc_item)
        door_id = self._next_door_id
        self._next_door_id += 1
        for it in (line_item, arc_item):
            it.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
            it.setData(0, "door")
            it.setData(1, door_id)
        self._door_groups[door_id] = (line_item, arc_item)
        return (line_item, arc_item)

    def add_window(self, start: QPointF, end: QPointF) -> QtWidgets.QGraphicsLineItem:
        win_id = self._next_window_id
        self._next_window_id += 1
        pen = QPen(Qt.red, 3, Qt.DashLine)
        line_item = self.addLine(start.x(), start.y(), end.x(), end.y(), pen)
        line_item.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        line_item.setData(0, "window")
        line_item.setData(1, win_id)
        dx = end.x() - start.x()
        length = 10
        if dx == 0:
            l1 = self.addLine(start.x() - length / 2, start.y(), start.x() + length / 2, start.y(), QPen(Qt.red, 2))
            l2 = self.addLine(end.x() - length / 2, end.y(), end.x() + length / 2, end.y(), QPen(Qt.red, 2))
        else:
            l1 = self.addLine(start.x(), start.y() - length / 2, start.x(), start.y() + length / 2, QPen(Qt.red, 2))
            l2 = self.addLine(end.x(), end.y() - length / 2, end.x(), end.y() + length / 2, QPen(Qt.red, 2))
        for deco in (l1, l2):
            deco.setData(0, "window_deco")
            deco.setData(1, win_id)
        self._window_groups[win_id] = (line_item, l1, l2)
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

    def add_wardrobe(self, center: QPointF) -> FurnitureItem:
        w, h = 140.0, 60.0
        x, y = center.x() - w / 2, center.y() - h / 2
        item = FurnitureItem("Wardrobe", x, y, w, h)
        self.addItem(item)
        return item

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
        if isinstance(hit, (ResizeHandle, WallHandle, FurnitureItem)):
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
            if self._current_item is None:
                if mode == "Door":
                    self._current_item = self.add_door(pos, pos)
                else:
                    self._current_item = self.add_window(pos, pos)
            else:
                self._items.append(self._current_item)
                self._current_item = None
        elif event.button() == Qt.LeftButton:
            pos = self.snap_to_grid(event.scenePos())
            if mode == "Furniture: Bed":
                self._items.append(self.add_bed(pos))
                if self.parent_widget:
                    self.parent_widget.set_mode("Select")
                return
            elif mode == "Furniture: Sofa":
                self._items.append(self.add_sofa(pos))
                if self.parent_widget:
                    self.parent_widget.set_mode("Select")
                return
            elif mode == "Furniture: Table":
                self._items.append(self.add_table(pos))
                if self.parent_widget:
                    self.parent_widget.set_mode("Select")
                return
            elif mode == "Furniture: Wardrobe":
                self._items.append(self.add_wardrobe(pos))
                if self.parent_widget:
                    self.parent_widget.set_mode("Select")
                return
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
                hinge = QPointF(line.line().x1(), line.line().y1())
                line.setLine(hinge.x(), hinge.y(), end.x(), end.y())
                arc.setPath(self._door_path(hinge, end))
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self._exit_drawing_mode()
            return
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_selected()
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

    def delete_selected(self):
        selected = self.selectedItems()
        if not selected:
            return
        removed = set()
        processed_doors = set()
        processed_windows = set()
        for it in selected:
            kind = it.data(0)
            if isinstance(it, FurnitureItem):
                removed.add(it)
                self.removeItem(it)
                continue
            if isinstance(it, WallItem):
                for h in getattr(it, "handles", []):
                    if h.scene() is self:
                        self.removeItem(h)
                it.handles = []
                removed.add(it)
                self.removeItem(it)
                continue
            if kind == "window":
                win_id = it.data(1)
                if win_id is not None and win_id not in processed_windows:
                    processed_windows.add(win_id)
                    grp = self._window_groups.pop(win_id, None)
                    if grp:
                        for obj in grp:
                            if obj.scene() is self:
                                self.removeItem(obj)
                                removed.add(obj)
                continue
            if kind == "door":
                door_id = it.data(1)
                if door_id is not None and door_id not in processed_doors:
                    processed_doors.add(door_id)
                    pair = self._door_groups.pop(door_id, None)
                    if pair:
                        line, arc = pair
                        if line.scene() is self:
                            self.removeItem(line)
                            removed.add(line)
                        if arc.scene() is self:
                            self.removeItem(arc)
                            removed.add(arc)
                continue
        if removed:
            new_items = []
            for obj in self._items:
                if isinstance(obj, tuple):
                    keep = True
                    for part in obj:
                        if part in removed:
                            keep = False
                            break
                    if keep:
                        new_items.append(obj)
                else:
                    if obj in removed:
                        continue
                    new_items.append(obj)
            self._items = new_items
        self.show_wall_end_markers()

    def contextMenuEvent(self, event: QtWidgets.QGraphicsSceneContextMenuEvent):
        it = self.itemAt(event.scenePos(), QtGui.QTransform())
        if it:
            menu = QtWidgets.QMenu()
            act_del = menu.addAction("Delete")
            chosen = menu.exec(event.screenPos())
            if chosen == act_del:
                it.setSelected(True)
                self.delete_selected()
        else:
            super().contextMenuEvent(event)
