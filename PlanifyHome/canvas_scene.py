import math
import command
from typing import Tuple, List
from PySide6 import QtWidgets, QtGui
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QTransform, QFont, QPainterPath, QUndoStack
from PySide6.QtWidgets import QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsLineItem, QGraphicsPathItem
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
        self._start_line = None
        radius = 8
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.setPen(QPen(Qt.black, 1))
        self.setBrush(QBrush(Qt.white))
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setZValue(100)

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        self._start_line = QtGui.QLineF(self.wall_item.line())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        if self._start_line is not None:
            end_line = QtGui.QLineF(self.wall_item.line())
            if end_line.p1() != self._start_line.p1() or end_line.p2() != self._start_line.p2():
                sc = self.wall_item.scene()
                if sc and hasattr(sc, "_get_undo_stack"):
                    us = sc._get_undo_stack()
                    if us:
                        us.push(command.WallResizeCommand(self.wall_item, self._start_line, end_line, "Resize Wall"))
        sc2 = self.wall_item.scene()
        if sc2 and hasattr(sc2, "show_wall_end_markers"):
            sc2.show_wall_end_markers()
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            sc = self.wall_item.scene()
            new_scene_pos = sc.snap_to_grid(value) if sc and hasattr(sc, 'snap_to_grid') else value
            local = self.wall_item.mapFromScene(new_scene_pos)

            line = self.wall_item.line()
            if self.end_index == 1:
                line.setP1(local)
            else:
                line.setP2(local)

            self.wall_item.setLine(line)
            self.wall_item._update_dimension_text()
            return new_scene_pos

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

        mid_local = (line.p1() + line.p2()) / 2
        mid_scene = self.mapToScene(mid_local)

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
        t = QTransform()
        t.translate(mid_scene.x(), mid_scene.y())
        t.rotate(angle)
        t.translate(0, -15)
        if 85 < abs(angle) < 95:
            t.rotate(90)
            t.translate(15, 0)
        self.dimension_text.setTransform(t)

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
        p1_scene = self.mapToScene(line.p1())
        p2_scene = self.mapToScene(line.p2())
        self.handles[0].setPos(p1_scene)
        self.handles[1].setPos(p2_scene)

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
            sc = self.scene()
            if sc and hasattr(sc, 'snap_to_grid'):
                return sc.snap_to_grid(value)
            return value

        elif change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            self._update_handles()

        return super().itemChange(change, value)


    def prepare_for_delete(self):
        sc = self.scene()
        if sc:
            for h in self.handles:
                if h.scene() == sc:
                    sc.removeItem(h)
            self.handles.clear()
            if self.dimension_text and self.dimension_text.scene() == sc:
                sc.removeItem(self.dimension_text)
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
        self._next_door_id = 1
        self._next_window_id = 1

    def _get_undo_stack(self) -> QUndoStack | None:
        if self.parent_widget and hasattr(self.parent_widget, 'undo_stack'):
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
        orientation_flag = 1 if self._door_ccw else 0
        for it in (line_item, arc_item):
            it.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
            it.setData(0, "door")
            it.setData(1, door_id)
            it.setData(2, orientation_flag)
        return (line_item, arc_item)

    def add_window(self, start: QPointF, end: QPointF) -> Tuple[QGraphicsLineItem, QGraphicsLineItem, QGraphicsLineItem]:
        win_id = self._next_window_id
        self._next_window_id += 1
        pen = QPen(Qt.red, 3, Qt.DashLine)
        line_item = QGraphicsLineItem(start.x(), start.y(), end.x(), end.y())
        line_item.setPen(pen)
        line_item.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        line_item.setData(0, "window")
        line_item.setData(1, win_id)
        dx = end.x() - start.x()
        length = 10
        if dx == 0:
            l1 = QGraphicsLineItem(start.x() - length / 2, start.y(), start.x() + length / 2, start.y())
            l2 = QGraphicsLineItem(end.x() - length / 2, end.y(), end.x() + length / 2, end.y())
        else:
            l1 = QGraphicsLineItem(start.x(), start.y() - length / 2, start.x(), start.y() + length / 2)
            l2 = QGraphicsLineItem(end.x(), end.y() - length / 2, end.x(), end.y() + length / 2)
        for deco in (l1, l2):
            deco.setPen(QPen(Qt.red, 2))
            deco.setData(0, "window_deco")
            deco.setData(1, win_id)
        return (line_item, l1, l2)

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
        for it in self.items():
            if isinstance(it, WallItem):
                line = it.line()
                p1 = it.mapToScene(line.p1())
                p2 = it.mapToScene(line.p2())
                for pt in (p1, p2):
                    marker = self.addEllipse(pt.x() - radius, pt.y() - radius,
                                         radius * 2, radius * 2,
                                         QPen(Qt.darkGray), QBrush(Qt.green))
                    marker.setZValue(1000)
                    self._wall_end_markers.append(marker)

    def _exit_drawing_mode(self):
        if self._current_item is None:
            return

        if isinstance(self._current_item, WallItem):
            wall = self._current_item
            wall.prepare_for_delete()
            if wall.scene() is self:
                self.removeItem(wall)

        elif isinstance(self._current_item, tuple):
            for it in self._current_item:
                if it is not None and it.scene() is self:
                    self.removeItem(it)

        elif isinstance(self._current_item, QtWidgets.QGraphicsItem):
            if self._current_item.scene() is self:
                self.removeItem(self._current_item)

        self._current_item = None
        self.show_wall_end_markers()
        if self.parent_widget:
            self.parent_widget.set_mode("Select")

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        from furniture import ResizeHandle
        us = self._get_undo_stack()
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
                    current_wall.prepare_for_delete()
                    self.removeItem(current_wall)
                else:
                    self._items.append(current_wall)
                    if us:
                        us.push(command.AddItemCommand(current_wall, self, "Add Wall"))
                self._current_item = None
                self.show_wall_end_markers()

        elif event.button() == Qt.LeftButton and mode in ("Door", "Window"):
            if self._current_item is None:
                if mode == "Door":
                    self._current_item = self.add_door(pos, pos)
                else:
                    self._current_item = self.add_window(pos, pos)
                for it in (self._current_item if isinstance(self._current_item, tuple) else (self._current_item,)):
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
                    if us:
                        us.push(command.AddItemCommand(items_to_finalize, self, f"Add {mode}"))
                    self._current_item = None

        elif event.button() == Qt.LeftButton and mode and mode.startswith("Furniture: "):
            kind = mode.split(": ")[1]
            new_item = None
            if kind == "Bed":
                new_item = self.add_bed(pos)
            elif kind == "Sofa":
                new_item = self.add_sofa(pos)
            elif kind == "Table":
                new_item = self.add_table(pos)
            elif kind == "Wardrobe":
                new_item = self.add_wardrobe(pos)
            elif kind == "Chair":
                new_item = self.add_chair(pos)
            elif kind == "Plant":
                new_item = self.add_plant(pos)
            if new_item:
                self._items.append(new_item)
                if us:
                    us.push(command.AddItemCommand(new_item, self, f"Add {new_item.kind}"))
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
                    if dx == 0:
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
                if isinstance(item, FurnitureItem) and hasattr(item, "rotate_90_degrees"):
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

    def _collect_group_for_delete(self, it):
        items = []
        kind = it.data(0)
        if kind == "door":
            gid = it.data(1)
            for obj in self.items():
                if obj.data(0) == "door" and obj.data(1) == gid:
                    items.append(obj)
        elif kind == "window":
            gid = it.data(1)
            for obj in self.items():
                if obj.data(1) == gid and obj.data(0) in ("window", "window_deco"):
                    items.append(obj)
        elif kind == "window_deco":
            gid = it.data(1)
            for obj in self.items():
                if obj.data(1) == gid and obj.data(0) in ("window", "window_deco"):
                    items.append(obj)
        return items

    def delete_selected(self):
        selected = self.selectedItems()
        if not selected:
            return
        to_delete: list[QtWidgets.QGraphicsItem] = []
        for it in selected:
            if isinstance(it, WallItem):
                to_delete.append(it)
                continue
            if isinstance(it, FurnitureItem):
                to_delete.append(it)
                continue
            group = self._collect_group_for_delete(it)
            if group:
                for g in group:
                    if g not in to_delete:
                        to_delete.append(g)
            else:
                to_delete.append(it)
        unique = []
        seen = set()
        for it in to_delete:
            if id(it) not in seen:
                unique.append(it)
                seen.add(id(it))
        self.clear_wall_end_markers()
        us = self._get_undo_stack()
        if us and unique:
            us.push(command.DeleteItemsCommand(unique, self, "Delete Items"))
        removed_set = set(unique)
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
                    group = self._collect_group_for_delete(it)
                    for part in group:
                        part.setSelected(True)
                else:
                    it.setSelected(True)
                self.delete_selected()
        else:
            super().contextMenuEvent(event)

    def to_json(self) -> dict:
        data = {"walls": [], "doors": [], "windows": [], "furniture": []}

        for it in self.items():
            if isinstance(it, WallItem):
                l = it.line()
                data["walls"].append({"p1": [l.x1(), l.y1()], "p2": [l.x2(), l.y2()]})

        seen_doors = set()
        for it in self.items():
            if isinstance(it, QGraphicsLineItem) and it.data(0) == "door":
                gid = it.data(1)
                if gid in seen_doors:
                    continue
                seen_doors.add(gid)
                l = it.line()
                ccw = bool(it.data(2)) if it.data(2) is not None else True
                data["doors"].append({"p1": [l.x1(), l.y1()], "p2": [l.x2(), l.y2()], "ccw": ccw})

        seen_windows = set()
        for it in self.items():
            if isinstance(it, QGraphicsLineItem) and it.data(0) == "window":
                gid = it.data(1)
                if gid in seen_windows:
                    continue
                seen_windows.add(gid)
                l = it.line()
                data["windows"].append({"p1": [l.x1(), l.y1()], "p2": [l.x2(), l.y2()]})

        for it in self.items():
            if isinstance(it, FurnitureItem):
                r = it.rect()
                pos = it.scenePos()
                data["furniture"].append({
                    "kind": it.kind,
                    "x": pos.x(),
                    "y": pos.y(),
                    "w": r.width(),
                    "h": r.height()
                })

        return data

    def load_from_json(self, data: dict):
        self.clear()
        self._items.clear()
        self._wall_end_markers.clear()
        self._current_item = None
        self._next_door_id = 1
        self._next_window_id = 1

        for w in data.get("walls", []):
            p1 = QPointF(w["p1"][0], w["p1"][1])
            p2 = QPointF(w["p2"][0], w["p2"][1])
            wi = self.add_wall(p1, p2)
            self.addItem(wi)
            self._items.append(wi)

        for d in data.get("doors", []):
            p1 = QPointF(d["p1"][0], d["p1"][1])
            p2 = QPointF(d["p2"][0], d["p2"][1])
            ccw = bool(d.get("ccw", True))
            old = self._door_ccw
            self._door_ccw = ccw
            line, arc = self.add_door(p1, p2)
            self.addItem(line)
            self.addItem(arc)
            self._items.append((line, arc))
            self._door_ccw = old

        for w in data.get("windows", []):
            p1 = QPointF(w["p1"][0], w["p1"][1])
            p2 = QPointF(w["p2"][0], w["p2"][1])
            line, l1, l2 = self.add_window(p1, p2)
            self.addItem(line)
            self.addItem(l1)
            self.addItem(l2)
            self._items.append((line, l1, l2))

        for f in data.get("furniture", []):
            kind = f["kind"]
            center = QPointF(f["x"] + f["w"] / 2.0, f["y"] + f["h"] / 2.0)
            item = None
            if kind == "Bed":
                item = self.add_bed(center)
            elif kind == "Sofa":
                item = self.add_sofa(center)
            elif kind == "Table":
                item = self.add_table(center)
            elif kind == "Wardrobe":
                item = self.add_wardrobe(center)
            elif kind == "Chair":
                item = self.add_chair(center)
            elif kind == "Plant":
                item = self.add_plant(center)
            if item:
                item.setRect(0, 0, f["w"], f["h"])
                item.update_handles()
                self.addItem(item)
                self._items.append(item)

        self.show_wall_end_markers()
