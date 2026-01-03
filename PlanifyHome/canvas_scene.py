import math
import command
from typing import Tuple, List
from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtCore import Qt, QPointF, QRectF, QLineF, QMarginsF
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QTransform, QFont, QPainterPath, QUndoStack, QPolygonF
from PySide6.QtWidgets import QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsLineItem, QGraphicsPathItem, QMessageBox
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
        self.wall_item._resizing = True
        self._start_line = QLineF(self.wall_item.line())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        self.wall_item._resizing = False
        if self._start_line is not None:
            end_line = QLineF(self.wall_item.line())
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
            if sc and hasattr(sc, "show_wall_end_markers"): 
                sc.show_wall_end_markers()
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
        self._resizing = False
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
        if not self.scene(): return
        line = self.line()
        length = self._get_wall_length()
        mid_scene = self.mapToScene((line.p1() + line.p2()) / 2)
        text = f"{length:.0f}"
        if self.dimension_text is None:
            self.dimension_text = QGraphicsSimpleTextItem(text)
            self.dimension_text.setBrush(QBrush(Qt.black))
            font = QFont("Arial", 10, QFont.Bold)
            self.dimension_text.setFont(font)
            self.dimension_text.setZValue(15)
            self.scene().addItem(self.dimension_text)
        self.dimension_text.setText(text)
        angle = math.degrees(math.atan2(line.dy(), line.dx()))
        t = QTransform().translate(mid_scene.x(), mid_scene.y()).rotate(angle).translate(0, -15)
        if 85 < abs(angle) < 95: t.rotate(180)
        self.dimension_text.setTransform(t)

    def _show_dimension_text(self, show: bool):
        if self.dimension_text: self.dimension_text.setVisible(show)

    def _update_handles(self):
        if not self.scene(): return
        line = self.line()
        if not self.handles:
            self.handles = [WallHandle(self, 1), WallHandle(self, 2)]
            for h in self.handles:
                self.scene().addItem(h)
                h.setVisible(self.isSelected())
        self.handles[0].setPos(self.mapToScene(line.p1()))
        self.handles[1].setPos(self.mapToScene(line.p2()))
        if self.isSelected(): self._update_dimension_text()

    def _show_handles(self, show: bool):
        if not self.handles and show: self._update_handles()
        for h in self.handles: h.setVisible(show)
        self._show_dimension_text(show)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemSelectedChange:
            self._show_handles(bool(value))
        elif change == QtWidgets.QGraphicsItem.ItemPositionChange:
            if self._resizing: 
                return self.pos()
            sc = self.scene()
            return sc.snap_to_grid(value) if sc and hasattr(sc, 'snap_to_grid') else value
        elif change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            self._update_handles()
        return super().itemChange(change, value)

    def prepare_for_delete(self):
        sc = self.scene()
        if sc:
            for h in self.handles: 
                if h.scene() == sc: sc.removeItem(h)
            self.handles.clear()
            if self.dimension_text and self.dimension_text.scene() == sc: sc.removeItem(self.dimension_text)
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
        return self.parent_widget.undo_stack if self.parent_widget and hasattr(self.parent_widget, 'undo_stack') else None

    def snap_to_grid(self, pos: QPointF) -> QPointF:
        return QPointF(round(pos.x() / GRID_SIZE) * GRID_SIZE, round(pos.y() / GRID_SIZE) * GRID_SIZE)

    def _door_path(self, hinge: QPointF, end: QPointF) -> QPainterPath:
        dx, dy = end.x() - hinge.x(), end.y() - hinge.y()
        r = max(1.0, math.hypot(dx, dy))
        theta = math.degrees(math.atan2(-dy, dx))
        path = QPainterPath(hinge)
        path.arcTo(hinge.x() - r, hinge.y() - r, 2 * r, 2 * r, theta, 90 if self._door_ccw else -90)
        return path

    def get_room_polygons(self) -> List[QPolygonF]:
        lines = []
        for it in self.items():
            if isinstance(it, WallItem): 
                l = it.line()
                lines.append(QLineF(it.mapToScene(l.p1()), it.mapToScene(l.p2())))
            elif isinstance(it, QGraphicsLineItem) and it.data(0) in ("door", "window"):
                l = it.line()
                lines.append(QLineF(it.mapToScene(l.p1()), it.mapToScene(l.p2())))
        if not lines: return []
        path = QPainterPath()
        temp_lines = lines.copy()
        while temp_lines:
            current_line = temp_lines.pop(0)
            path.moveTo(current_line.p1())
            path.lineTo(current_line.p2())
            last_p = current_line.p2()
            searching = True
            while searching:
                found = False
                for i, l in enumerate(temp_lines):
                    if (l.p1() - last_p).manhattanLength() < 5:
                        path.lineTo(l.p2()); last_p = l.p2(); temp_lines.pop(i); found = True; break
                    elif (l.p2() - last_p).manhattanLength() < 5:
                        path.lineTo(l.p1()); last_p = l.p1(); temp_lines.pop(i); found = True; break
                if not found: searching = False
        return path.toFillPolygons()

    def is_point_inside_room(self, point: QPointF) -> bool:
        polys = self.get_room_polygons()
        return any(poly.containsPoint(point, Qt.OddEvenFill) for poly in polys)

    def is_item_inside_room(self, item_rect_scene: QRectF) -> bool:
        polys = self.get_room_polygons()
        if not polys: return False
        inflated_rect = item_rect_scene.marginsAdded(QMarginsF(-0.5, -0.5, -0.5, -0.5))
        for poly in polys:
            if all(poly.containsPoint(p, Qt.OddEvenFill) for p in [inflated_rect.topLeft(), inflated_rect.topRight(), inflated_rect.bottomLeft(), inflated_rect.bottomRight()]):
                return True
        return False

    def is_colliding_with_furniture(self, rect: QRectF, exclude_item=None) -> bool:
        test_rect = rect.marginsAdded(QMarginsF(-0.5, -0.5, -0.5, -0.5))
        for it in self.items():
            if isinstance(it, FurnitureItem) and it is not exclude_item:
                if it.sceneBoundingRect().intersects(test_rect):
                    return True
        return False

    def is_point_on_wall(self, point: QPointF) -> bool:
        for it in self.items():
            if isinstance(it, WallItem):
                l = it.line()
                p1, p2 = it.mapToScene(l.p1()), it.mapToScene(l.p2())
                line = QLineF(p1, p2)
                if line.length() == 0: continue
                dist = abs((p2.y()-p1.y())*point.x() - (p2.x()-p1.x())*point.y() + p2.x()*p1.y() - p2.y()*p1.x()) / line.length()
                if dist < 12 and min(p1.x(), p2.x())-10 <= point.x() <= max(p1.x(), p2.x())+10 and min(p1.y(), p2.y())-10 <= point.y() <= max(p1.y(), p2.y())+10:
                    return True
        return False

    def add_wall(self, start: QPointF, end: QPointF) -> WallItem:
        item = WallItem()
        item.setLine(start.x(), start.y(), end.x(), end.y())
        item.setData(0, "wall")
        return item

    def add_door(self, start: QPointF, end: QPointF) -> Tuple[QGraphicsLineItem, QGraphicsPathItem]:
        l_item = QGraphicsLineItem(start.x(), start.y(), end.x(), end.y())
        l_item.setPen(QPen(Qt.blue, 3))
        a_item = QGraphicsPathItem()
        a_item.setPen(QPen(Qt.blue, 1)); a_item.setBrush(QColor(0, 0, 255, 50))
        a_item.setPath(self._door_path(start, end))
        for it in (l_item, a_item):
            it.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
            it.setData(0, "door"); it.setData(1, self._next_door_id); it.setData(2, 1 if self._door_ccw else 0)
        self._next_door_id += 1
        return (l_item, a_item)

    def add_window(self, start: QPointF, end: QPointF) -> Tuple[QGraphicsLineItem, QGraphicsLineItem, QGraphicsLineItem]:
        l_item = QGraphicsLineItem(start.x(), start.y(), end.x(), end.y())
        l_item.setPen(QPen(Qt.red, 3, Qt.DashLine)); l_item.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        l_item.setData(0, "window"); l_item.setData(1, self._next_window_id)
        l1, l2 = QGraphicsLineItem(), QGraphicsLineItem()
        for deco in (l1, l2):
            deco.setPen(QPen(Qt.red, 2)); deco.setData(0, "window_deco"); deco.setData(1, self._next_window_id)
        self._next_window_id += 1
        return (l_item, l1, l2)

    def add_bed(self, p: QPointF) -> FurnitureItem: return FurnitureItem("Bed", p.x()-50, p.y()-40, 100, 80)
    def add_table(self, p: QPointF) -> FurnitureItem: return FurnitureItem("Table", p.x()-40, p.y()-25, 80, 50)
    def add_sofa(self, p: QPointF) -> FurnitureItem: return FurnitureItem("Sofa", p.x()-60, p.y()-25, 120, 50)
    def add_wardrobe(self, p: QPointF) -> FurnitureItem: return FurnitureItem("Wardrobe", p.x()-35, p.y()-20, 70, 40)
    def add_chair(self, p: QPointF) -> FurnitureItem: return FurnitureItem("Chair", p.x()-15, p.y()-17, 30, 35)
    def add_plant(self, p: QPointF) -> FurnitureItem: return FurnitureItem("Plant", p.x()-15, p.y()-15, 30, 30)

    def clear_wall_end_markers(self):
        for m in self._wall_end_markers: self.removeItem(m)
        self._wall_end_markers.clear()

    def show_wall_end_markers(self):
        self.clear_wall_end_markers()
        for it in self.items():
            if isinstance(it, WallItem):
                l = it.line()
                for pt in [it.mapToScene(l.p1()), it.mapToScene(l.p2())]:
                    m = self.addEllipse(pt.x()-4, pt.y()-4, 8, 8, QPen(Qt.darkGray), QBrush(Qt.green))
                    m.setZValue(1000); self._wall_end_markers.append(m)

    def _exit_drawing_mode(self):
        if self._current_item:
            if isinstance(self._current_item, WallItem): self._current_item.prepare_for_delete(); self.removeItem(self._current_item)
            elif isinstance(self._current_item, tuple):
                for it in self._current_item: self.removeItem(it)
        self._current_item = None; self.show_wall_end_markers()
        if self.parent_widget: self.parent_widget.set_mode("Select")

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        from furniture import ResizeHandle
        us = self._get_undo_stack()
        if event.button() == Qt.RightButton: self._exit_drawing_mode(); return
        hit = self.itemAt(event.scenePos(), QTransform())
        if isinstance(hit, (ResizeHandle, WallHandle, FurnitureItem)): super().mousePressEvent(event); return
        mode = getattr(self.parent_widget, "_current_mode", "Select")
        pos = self.snap_to_grid(event.scenePos())
        if mode == "Wall":
            if self._current_item is None:
                self._current_item = self.add_wall(pos, pos); self.addItem(self._current_item); self.clear_wall_end_markers()
            else:
                if self._current_item._get_wall_length() >= GRID_SIZE/2:
                    self._items.append(self._current_item)
                    if us: us.push(command.AddItemCommand(self._current_item, self, "Add Wall"))
                else: self._current_item.prepare_for_delete(); self.removeItem(self._current_item)
                self._current_item = None; self.show_wall_end_markers()
        elif mode in ("Door", "Window"):
            if self._current_item is None:
                if not self.is_point_on_wall(pos):
                    QMessageBox.warning(None, "Atentie", "Trebuie sa incepeti pozitionarea pe un perete.")
                    return
                self._current_item = self.add_door(pos, pos) if mode == "Door" else self.add_window(pos, pos)
                for it in (self._current_item if isinstance(self._current_item, tuple) else (self._current_item,)): self.addItem(it)
            else:
                main = self._current_item[0] if isinstance(self._current_item, tuple) else self._current_item
                end_p = main.mapToScene(main.line().p2())
                if self.is_point_on_wall(end_p) and main.line().length() >= GRID_SIZE/2:
                    self._items.append(self._current_item)
                    if us: us.push(command.AddItemCommand(self._current_item, self, f"Add {mode}"))
                    self._current_item = None
                else:
                    QMessageBox.warning(None, "Atentie", "Ambele capete trebuie sa fie pe perete.")
                    self._exit_drawing_mode()
        elif mode.startswith("Furniture: "):
            if not self.is_point_inside_room(pos):
                QMessageBox.warning(None, "Constraint", "Mobilierul trebuie pus intr-o camera inchisa.")
                return
            kind = mode.split(": ")[1]
            item = getattr(self, f"add_{kind.lower()}")(pos)
            if item:
                original_pos = item.pos()
                found = False
                for d in range(0, 31, 1):
                    for dx, dy in [(0,0),(d,0),(-d,0),(0,d),(0,-d),(d,d),(-d,-d),(d,-d),(-d,d)]:
                        item.setPos(original_pos + QPointF(dx, dy))
                        if self.is_item_inside_room(item.sceneBoundingRect()) and not self.is_colliding_with_furniture(item.sceneBoundingRect(), exclude_item=item):
                            found = True; break
                    if found: break
                if not found:
                    QMessageBox.warning(None, "Constraint", "Nu este loc aici.")
                    return
                self.addItem(item); self._items.append(item)
                if us: us.push(command.AddItemCommand(item, self, f"Add {kind}"))
                self.parent_widget.set_mode("Select")
        else: super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        if self._current_item:
            end = self.snap_to_grid(event.scenePos())
            if isinstance(self._current_item, WallItem):
                l = self._current_item.line(); l.setP2(end); self._current_item.setLine(l); self._current_item._update_dimension_text()
            elif isinstance(self._current_item, tuple):
                main = self._current_item[0]
                l = main.line(); l.setP2(end); main.setLine(l)
                if main.data(0) == "door": self._current_item[1].setPath(self._door_path(l.p1(), end))
                elif main.data(0) == "window":
                    dx = end.x() - l.x1()
                    self._current_item[1].setLine(l.x1()-(5 if dx==0 else 0), l.y1()-(0 if dx==0 else 5), l.x1()+(5 if dx==0 else 0), l.y1()+(0 if dx==0 else 5))
                    self._current_item[2].setLine(end.x()-(5 if dx==0 else 0), end.y()-(0 if dx==0 else 5), end.x()+(5 if dx==0 else 0), end.y()+(0 if dx==0 else 5))
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == Qt.Key_Escape: self._exit_drawing_mode(); return
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace): self.delete_selected(); return
        if event.key() == Qt.Key_R:
            for it in self.selectedItems():
                if isinstance(it, FurnitureItem):
                    old_rot = it.rotation(); it.setRotation(old_rot + 90)
                    if not self.is_item_inside_room(it.sceneBoundingRect()) or self.is_colliding_with_furniture(it.sceneBoundingRect(), exclude_item=it):
                        it.setRotation(old_rot)
            return
        super().keyPressEvent(event)

    def drawBackground(self, painter: QPainter, rect: QRectF):
        painter.save()
        painter.fillRect(rect, Qt.white)
        step = GRID_SIZE
        painter.setPen(QPen(QColor(0, 0, 0, 80), 1))
        left = int(math.floor(rect.left() / step) * step)
        top = int(math.floor(rect.top() / step) * step)
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
        if not selected: return
        to_del = []
        for it in selected:
            if isinstance(it, (WallItem, FurnitureItem)): to_del.append(it)
            elif it.data(0) in ("door", "window", "window_deco"):
                gid = it.data(1); to_del.extend([o for o in self.items() if o.data(1) == gid])
        unique = list(set(to_del)); self.clear_wall_end_markers()
        us = self._get_undo_stack()
        if us and unique: us.push(command.DeleteItemsCommand(unique, self, "Delete Items"))
        self.show_wall_end_markers()

    def to_json(self) -> dict:
        d = {"walls": [], "doors": [], "windows": [], "furniture": []}
        for it in self.items():
            if isinstance(it, WallItem): l = it.line(); d["walls"].append({"p1": [l.x1(), l.y1()], "p2": [l.x2(), l.y2()]})
        seen_d, seen_w = set(), set()
        for it in self.items():
            if isinstance(it, QGraphicsLineItem):
                gid = it.data(1)
                if it.data(0) == "door" and gid not in seen_d:
                    seen_d.add(gid); l = it.line(); d["doors"].append({"p1": [l.x1(), l.y1()], "p2": [l.x2(), l.y2()], "ccw": bool(it.data(2))})
                elif it.data(0) == "window" and gid not in seen_w:
                    seen_w.add(gid); l = it.line(); d["windows"].append({"p1": [l.x1(), l.y1()], "p2": [l.x2(), l.y2()]})
        for it in self.items():
            if isinstance(it, FurnitureItem):
                r = it.rect(); d["furniture"].append({"kind": it.kind, "x": it.x(), "y": it.y(), "w": r.width(), "h": r.height(), "rotation": it.rotation()})
        return d

    def load_from_json(self, d: dict):
        self.clear(); self._items.clear(); self._wall_end_markers.clear()
        for w in d.get("walls", []):
            i = self.add_wall(QPointF(*w["p1"]), QPointF(*w["p2"])); self.addItem(i); self._items.append(i)
        for dr in d.get("doors", []):
            self._door_ccw = dr.get("ccw", True); line, arc = self.add_door(QPointF(*dr["p1"]), QPointF(*dr["p2"]))
            self.addItem(line); self.addItem(arc); self._items.append((line, arc))
        for w in d.get("windows", []):
            line, l1, l2 = self.add_window(QPointF(*w["p1"]), QPointF(*w["p2"]))
            self.addItem(line); self.addItem(l1); self.addItem(l2); self._items.append((line, l1, l2))
        for f in d.get("furniture", []):
            item = getattr(self, f"add_{f['kind'].lower()}")(QPointF(f["x"]+f["w"]/2, f["y"]+f["h"]/2))
            if item:
                item.setRect(0, 0, f["w"], f["h"]); item.setRotation(f.get("rotation", 0))
                item.update_handles(); self.addItem(item); self._items.append(item)
        self.show_wall_end_markers()