import math
from typing import Tuple, List

from PySide6 import QtWidgets, QtGui
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QTransform, QFont, QPainterPath, QUndoStack
from PySide6.QtWidgets import QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsLineItem, QGraphicsPathItem

from command import AddItemCommand, DeleteItemsCommand
from furniture import FurnitureItem
from constants import SCENE_MARGIN, GRID_SIZE


class PlanItem:
    def __init__(self, kind: str, graphics_item):
        self.kind = kind
        self.item = graphics_item


class WallHandle(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, wall_item: "WallItem", end_index: int):
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
            new_pos = scene.snap_to_grid(value) if hasattr(scene, "snap_to_grid") else value
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
        self.dimension_text: QGraphicsSimpleTextItem | None = None

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

    def _get_wall_length(self) -> float:
        line = self.line()
        return math.hypot(line.x2() - line.x1(), line.y2() - line.y1())

    def _update_dimension_text(self):
        if not self.scene():
            return
        line = self.line()
        length = self._get_wall_length()
        mid_point = (line.p1() + line.p2()) / 2
        text = f"{length:.0f}"
        if self.dimension_text is None:
            self.dimension_text = QGraphicsSimpleTextItem(text)
            self.dimension_text.setBrush(QBrush(Qt.black))
            font = QFont("Arial", 10)
            font.setBold(True)
            self.dimension_text.setFont(font)
            self.dimension_text.setZValue(15)
            self.scene().addItem(self.dimension_text)
        self.dimension_text.setText(text)
        angle = math.degrees(math.atan2(line.dy(), line.dx()))
        transform = QTransform()
        transform.translate(mid_point.x(), mid_point.y())
        transform.rotate(angle)
        transform.translate(0, -15)
        if abs(angle) > 85 and abs(angle) < 95:
            transform.rotate(90)
            transform.translate(15, 0)
        self.dimension_text.setTransform(transform)

    def _show_dimension_text(self, show: bool):
        if self.dimension_text:
            self.dimension_text.setVisible(show)

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
        if self.isSelected():
            self._update_dimension_text()

    def _show_handles(self, show: bool):
        if not self.handles and show:
            self._update_handles()
        for h in self.handles:
            h.setVisible(show)
        self._show_dimension_text(show)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemSelectedChange:
            self._show_handles(value)
            if value:
                self._update_dimension_text()
        elif change == QtWidgets.QGraphicsItem.ItemPositionChange:
            scene = self.scene()
            if scene and hasattr(scene, "snap_to_grid"):
                return scene.snap_to_grid(value)
        elif change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            self._update_handles()
        return super().itemChange(change, value)

    def prepare_for_delete(self):
        scene = self.scene()
        if scene:
            for h in self.handles:
                if h.scene() == scene:
                    scene.removeItem(h)
            self.handles.clear()
            if self.dimension_text and self.dimension_text.scene() == scene:
                scene.removeItem(self.dimension_text)
            self.dimension_text = None
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
        self.setSelected(False)


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

    def _get_undo_stack(self) -> QUndoStack | None:
        if self.parent_widget and hasattr(self.parent_widget, "undo_stack"):
            return self.parent_widget.undo_stack
        return None

    def snap_to_grid(self, pos: QPointF) -> QPointF:
        x = round(pos.x() / GRID_SIZE) * GRID_SIZE
        y = round(pos.y() / GRID_SIZE) * GRID_SIZE
        return QPointF(x, y)

    def _door_path(self, hinge: QPointF, end: QPointF) -> QPainterPath:
        dx, dy = end.x() - hinge.x(), end.y() - hinge.y()
        r = max(1.0, math.hypot(dx, dy))
        theta = math.degrees(math.atan2(-dy, dx))
        sweep = 90 if self._door_ccw else -90
        path = QPainterPath(hinge)
        path.arcTo(hinge.x() - r, hinge.y() - r, 2 * r, 2 * r, theta, sweep)
        return path

    def toggle_door_swing(self):
        self._door_ccw = not self._door_ccw
        if isinstance(self._current_item, tuple) and self._current_item[0].data(0) == "door":
            line, arc = self._current_item
            start = QPointF(line.line().x1(), line.line().y1())
            end = QPointF(line.line().x2(), line.line().y2())
            arc.setPath(self._door_path(start, end))

    def add_wall(self, start: QPointF, end: QPointF) -> WallItem:
        item = WallItem()
        item.setLine(start.x(), start.y(), end.x(), end.y())
        item.setData(0, "wall")
        return item

    def add_door(self, start: QPointF, end: QPointF) -> Tuple[QGraphicsLineItem, QGraphicsPathItem]:
        line_pen = QPen(Qt.blue, 3)
        line_item = QGraphicsLineItem(start.x(), start.y(), end.x(), end.y())
        line_item.setPen(line_pen)
        arc_item = QGraphicsPathItem()
        arc_item.setPen(QPen(Qt.blue, 1))
        arc_item.setBrush(QColor(0, 0, 255, 50))
        arc_item.setPath(self._door_path(start, end))
        door_id = self._next_door_id
        self._next_door_id += 1
        for it in (line_item, arc_item):
            it.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
            it.setData(0, "door")
            it.setData(1, door_id)
        self._door_groups[door_id] = (line_item, arc_item)
        return line_item, arc_item

    def add_window(self, start: QPointF, end: QPointF) -> Tuple[QGraphicsLineItem, QGraphicsLineItem, QGraphicsLineItem]:
        win_id = self._next_window_id
        self._next_window_id += 1
        pen = QPen(Qt.red, 3, Qt.DashLine)
        line_item = QGraphicsLineItem(start.x(), start.y(), end.x(), end.y())
        line_item.setPen(pen)
        line_item.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        line_item.setData(0, "window")
        line_item.setData(1, win_id)
        length = 10
        if abs(end.x() - start.x()) < 1e-3:
            l1 = QGraphicsLineItem(start.x() - length / 2, start.y(), start.x() + length / 2, start.y())
            l2 = QGraphicsLineItem(end.x() - length / 2, end.y(), end.x() + length / 2, end.y())
        else:
            l1 = QGraphicsLineItem(start.x(), start.y() - length / 2, start.x(), start.y() + length / 2)
            l2 = QGraphicsLineItem(end.x(), end.y() - length / 2, end.x(), end.y() + length / 2)
        for deco in (l1, l2):
            deco.setPen(QPen(Qt.red, 2))
            deco.setData(0, "window_deco")
            deco.setData(1, win_id)
        self._window_groups[win_id] = (line_item, l1, l2)
        return line_item, l1, l2

    def add_bed(self, center: QPointF) -> FurnitureItem:
        w, h = 200.0, 160.0
        x, y = center.x() - w / 2, center.y() - h / 2
        return FurnitureItem("Bed", x, y, w, h)

    def add_table(self, center: QPointF) -> FurnitureItem:
        w, h = 200.0, 110.0
        x, y = center.x() - w / 2, center.y() - h / 2
        return FurnitureItem("Table", x, y, w, h)

    def add_sofa(self, center: QPointF) -> FurnitureItem:
        w, h = 260.0, 90.0
        x, y = center.x() - w / 2, center.y() - h / 2
        return FurnitureItem("Sofa", x, y, w, h)

    def add_wardrobe(self, center: QPointF) -> FurnitureItem:
        w, h = 140.0, 60.0
        x, y = center.x() - w / 2, center.y() - h / 2
        return FurnitureItem("Wardrobe", x, y, w, h)

    def add_chair(self, center: QPointF) -> FurnitureItem:
        w, h = 60.0, 70.0
        x, y = center.x() - w / 2, center.y() - h / 2
        return FurnitureItem("Chair", x, y, w, h)

    def add_plant(self, center: QPointF) -> FurnitureItem:
        w, h = 60.0, 60.0
        x, y = center.x() - w / 2, center.y() - h / 2
        return FurnitureItem("Plant", x, y, w, h)

    def clear_wall_end_markers(self):
        for marker in self._wall_end_markers:
            self.removeItem(marker)
        self._wall_end_markers.clear()

    def show_wall_end_markers(self):
        self.clear_wall_end_markers()
        radius = 4
        for item in self.items():
            if isinstance(item, WallItem):
                line = item.line()
                for pt in (line.p1(), line.p2()):
                    marker = self.addEllipse(pt.x() - radius, pt.y() - radius, radius * 2, radius * 2, QPen(Qt.darkGray), QBrush(Qt.green))
                    marker.setZValue(1000)
                    self._wall_end_markers.append(marker)

    def _exit_drawing_mode(self):
        if self._current_item is not None:
            items_to_remove = self._current_item if isinstance(self._current_item, tuple) else (self._current_item,)
            for item in items_to_remove:
                if item is not None and item.scene() is self:
                    self.removeItem(item)
            self._current_item = None
            self.show_wall_end_markers()
            if self.parent_widget:
                self.parent_widget.set_mode("Select")

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        from furniture import ResizeHandle
        undo_stack = self._get_undo_stack()
        if event.button() == Qt.RightButton and self._current_item is not None:
            self._exit_drawing_mode()
            return
        hit = self.itemAt(event.scenePos(), QtGui.QTransform())
        if isinstance(hit, (ResizeHandle, WallHandle, FurnitureItem)):
            super().mousePressEvent(event)
            return
        mode = getattr(self.parent_widget, "_current_mode", None)
        pos = self.snap_to_grid(event.scenePos())
        if event.button() == Qt.LeftButton and mode == "Wall":
            if self._current_item is None:
                new_wall = self.add_wall(pos, pos)
                self.addItem(new_wall)
                self._current_item = new_wall
                self.clear_wall_end_markers()
            else:
                current_wall: WallItem = self._current_item
                if current_wall._get_wall_length() < GRID_SIZE / 2:
                    self.removeItem(current_wall)
                else:
                    self._items.append(current_wall)
                    if undo_stack:
                        cmd = AddItemCommand(current_wall, self, "Add Wall")
                        undo_stack.push(cmd)
                self._current_item = None
                self.show_wall_end_markers()
        elif event.button() == Qt.LeftButton and mode in ("Door", "Window"):
            if self._current_item is None:
                if mode == "Door":
                    self._current_item = self.add_door(pos, pos)
                else:
                    self._current_item = self.add_window(pos, pos)
                items_to_add = self._current_item if isinstance(self._current_item, tuple) else (self._current_item,)
                for it in items_to_add:
                    if it.scene() is not self:
                        self.addItem(it)
            else:
                items_to_finalize = self._current_item
                main_item = items_to_finalize[0] if isinstance(items_to_finalize, tuple) else items_to_finalize
                line = main_item.line()
                length = math.hypot(line.x2() - line.x1(), line.y2() - line.y1())
                if length < GRID_SIZE / 2:
                    self._exit_drawing_mode()
                else:
                    self._items.append(items_to_finalize)
                    if undo_stack:
                        cmd = AddItemCommand(items_to_finalize, self, f"Add {mode}")
                        undo_stack.push(cmd)
                    self._current_item = None
        elif event.button() == Qt.LeftButton and mode and mode.startswith("Furniture: "):
            furniture_kind = mode.split(": ")[1]
            new_item = None
            if furniture_kind == "Bed":
                new_item = self.add_bed(pos)
            elif furniture_kind == "Sofa":
                new_item = self.add_sofa(pos)
            elif furniture_kind == "Table":
                new_item = self.add_table(pos)
            elif furniture_kind == "Wardrobe":
                new_item = self.add_wardrobe(pos)
            elif furniture_kind == "Chair":
                new_item = self.add_chair(pos)
            elif furniture_kind == "Plant":
                new_item = self.add_plant(pos)
            if new_item:
                self.addItem(new_item)
                self._items.append(new_item)
                if undo_stack:
                    cmd = AddItemCommand(new_item, self, f"Add {new_item.kind}")
                    undo_stack.push(cmd)
                if self.parent_widget:
                    self.parent_widget.set_mode("Select")
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        if self._current_item is not None:
            end = self.snap_to_grid(event.scenePos())
            if isinstance(self._current_item, WallItem):
                line = self._current_item.line()
                line.setP2(end)
                self._current_item.setLine(line)
                self._current_item._update_dimension_text()
            elif isinstance(self._current_item, tuple):
                main_item = self._current_item[0]
                if main_item.data(0) == "door":
                    line, arc = main_item, self._current_item[1]
                    hinge = QPointF(line.line().x1(), line.line().y1())
                    line.setLine(hinge.x(), hinge.y(), end.x(), end.y())
                    arc.setPath(self._door_path(hinge, end))
                elif main_item.data(0) == "window":
                    line_item, l1, l2 = self._current_item
                    start = QPointF(line_item.line().x1(), line_item.line().y1())
                    line_item.setLine(start.x(), start.y(), end.x(), end.y())
                    dx = end.x() - start.x()
                    length = 10
                    if abs(dx) < 1e-3:
                        l1.setLine(start.x() - length / 2, start.y(), start.x() + length / 2, start.y())
                        l2.setLine(end.x() - length / 2, end.y(), end.x() + length / 2, end.y())
                    else:
                        l1.setLine(start.x(), start.y() - length / 2, start.x(), start.y() + length / 2)
                        l2.setLine(end.x(), end.y() - length / 2, end.x(), end.y() + length / 2)
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self._exit_drawing_mode()
            return
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_selected()
            return
        if event.key() == Qt.Key_R:
            for item in self.selectedItems():
                if isinstance(item, FurnitureItem):
                    item.rotate_90_degrees()
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
        items_to_delete: List[QtWidgets.QGraphicsItem] = []
        processed_doors = set()
        processed_windows = set()
        for it in selected:
            if it in items_to_delete:
                continue
            kind = it.data(0)
            if isinstance(it, FurnitureItem):
                items_to_delete.append(it)
                continue
            if isinstance(it, WallItem):
                it.prepare_for_delete()
                items_to_delete.append(it)
                continue
            if kind == "door":
                door_id = it.data(1)
                if door_id in processed_doors:
                    continue
                processed_doors.add(door_id)
                pair = self._door_groups.pop(door_id, None)
                if pair:
                    line, arc = pair
                    if line:
                        items_to_delete.append(line)
                    if arc:
                        items_to_delete.append(arc)
                continue
            if kind == "window" or kind == "window_deco":
                win_id = it.data(1)
                if win_id in processed_windows:
                    continue
                processed_windows.add(win_id)
                grp = self._window_groups.pop(win_id, None)
                if grp:
                    line_item, l1, l2 = grp
                    if line_item:
                        items_to_delete.append(line_item)
                    if l1:
                        items_to_delete.append(l1)
                    if l2:
                        items_to_delete.append(l2)
                continue
        unique_items = []
        seen = set()
        for obj in items_to_delete:
            if (obj not in seen) and (obj.scene() is self):
                seen.add(obj)
                unique_items.append(obj)
        self.clear_wall_end_markers()
        undo_stack = self._get_undo_stack()
        if undo_stack and unique_items:
            cmd = DeleteItemsCommand(unique_items, self, "Delete Items")
            undo_stack.push(cmd)
        else:
            for obj in unique_items:
                self.removeItem(obj)
        removed_set = set(unique_items)
        new_items = []
        for obj in self._items:
            if isinstance(obj, tuple):
                if any(part in removed_set for part in obj):
                    continue
            elif obj in removed_set:
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
                if it.data(0) in ("door", "window", "window_deco"):
                    group_id = it.data(1)
                    group = self._door_groups.get(group_id, ()) if it.data(0) == "door" else self._window_groups.get(group_id, ())
                    for part in group:
                        part.setSelected(True)
                else:
                    it.setSelected(True)
                self.delete_selected()
        else:
            super().contextMenuEvent(event)
