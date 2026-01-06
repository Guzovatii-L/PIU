from __future__ import annotations
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QPointF, Qt, QMarginsF
from PySide6.QtGui import QPainter, QPen, QColor

class ResizeHandle(QtWidgets.QGraphicsRectItem):
    SIZE = 14
    def __init__(self, parent: 'FurnitureItem'):
        super().__init__(-self.SIZE / 2, -self.SIZE / 2, self.SIZE, self.SIZE, parent)
        self._parent = parent
        self.setBrush(Qt.white); self.setPen(QPen(Qt.black, 1))
        self.setCursor(Qt.SizeFDiagCursor); self.setZValue(1e6)
        self.setFlags(QtWidgets.QGraphicsItem.ItemIsMovable | QtWidgets.QGraphicsItem.ItemSendsGeometryChanges | QtWidgets.QGraphicsItem.ItemIgnoresTransformations)

    def mousePressEvent(self, e):
        self._start_rect = self._parent.rect(); self._parent.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False); super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._parent.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        if hasattr(self, '_start_rect'):
            er = self._parent.rect()
            if abs(er.width()-self._start_rect.width()) > 0.1 or abs(er.height()-self._start_rect.height()) > 0.1:
                sc = self._parent.scene()
                if sc and hasattr(sc, "_get_undo_stack"):
                    us = sc._get_undo_stack()
                    if us: 
                        import command
                        us.push(command.ResizeItemCommand(self._parent, self._start_rect, er, f"Resize {self._parent.kind}"))
        super().mouseReleaseEvent(e)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            sc = self._parent.scene()
            nw, nh = max(self._parent._min_w, value.x()), max(self._parent._min_h, value.y())
            if sc and hasattr(sc, "is_item_inside_room"):
                new_rect = QtCore.QRectF(self._parent.x(), self._parent.y(), nw, nh)
                collides = sc.is_colliding_with_furniture(new_rect, exclude_item=self._parent) if hasattr(sc, "is_colliding_with_furniture") else False
                if not sc.is_item_inside_room(new_rect) or collides:
                    return QPointF(self._parent.rect().width(), self._parent.rect().height())
            return QPointF(nw, nh)
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged: self._parent.resize_to(self.pos().x(), self.pos().y())
        return super().itemChange(change, value)

class FurnitureItem(QtWidgets.QGraphicsRectItem):
    def __init__(self, kind, x, y, w, h):
        super().__init__(0, 0, w, h)
        self.setTransformOriginPoint(w / 2, h / 2)
        self.kind = kind; self.setPos(x, y); self._min_w, self._min_h = 30.0, 30.0
        self.setFlags(QtWidgets.QGraphicsItem.ItemIsMovable | QtWidgets.QGraphicsItem.ItemIsSelectable | QtWidgets.QGraphicsItem.ItemSendsGeometryChanges | QtWidgets.QGraphicsItem.ItemIsFocusable)
        self.handle = ResizeHandle(self); self.handle.hide(); self.update_handles()
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.AllButtons)

    def resize_to(self, nw, nh):
        self.prepareGeometryChange(); self.setRect(0, 0, nw, nh); self.update_handles(); self.update()

    def update_handles(self): self.handle.setPos(self.rect().width(), self.rect().height())

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemSelectedHasChanged: self.handle.setVisible(bool(value))
        elif change == QtWidgets.QGraphicsItem.ItemPositionChange:
            self._old_pos_for_undo = self.pos()
            return value
        elif change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            sc = self.scene()
            if sc:
                new_rect = self.sceneBoundingRect()
                if len(sc.selectedItems()) == 1:
                    inside = sc.is_item_inside_room(new_rect)
                    collides = sc.is_colliding_with_furniture(new_rect, exclude_item=self)
                    if not inside or collides:
                        self.setPos(self._old_pos_for_undo)
                        self._old_pos_for_undo = None
                        return super().itemChange(change, value)
            self._old_pos_for_undo = None
        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing); r = self.rect(); w, h = r.width(), r.height()
        painter.setPen(QPen(Qt.black, 2)); painter.setBrush(QColor(240, 240, 240))
        if self.kind == "Bed":
            painter.drawRect(r); head_h = min(20.0, h*0.2); painter.setBrush(QColor(220, 220, 220)); painter.drawRect(0, 0, w, head_h)
            painter.setBrush(Qt.white); painter.drawRect(10, 5, w*0.2, h*0.18); painter.drawRect(w-10-w*0.2, 5, w*0.2, h*0.18)
        elif self.kind == "Sofa":
            painter.drawRect(r); painter.setBrush(QColor(220, 220, 220)); painter.drawRect(0, 0, w, h*0.2)
            painter.setBrush(Qt.white); painter.drawRect(12, h*0.25, w*0.2, h*0.4); painter.drawRect(w-12-w*0.2, h*0.25, w*0.2, h*0.4)
        elif self.kind == "Table":
            m = max(6.0, min(w, h)*0.08); path = QtGui.QPainterPath()
            path.addRoundedRect(QtCore.QRectF(m, m, w-2*m, h-2*m), 12, 12); painter.setBrush(Qt.white); painter.drawPath(path)
        elif self.kind == "Wardrobe":
            painter.drawRect(r); painter.drawLine(w*0.5, 0, w*0.5, h); painter.setBrush(QColor(230, 230, 230))
            rr = max(2.0, min(w, h)*0.04); painter.drawEllipse(QtCore.QPointF(w*0.4, h*0.5), rr, rr); painter.drawEllipse(QtCore.QPointF(w*0.6, h*0.5), rr, rr)
        elif self.kind == "Chair":
            m = max(3.0, min(w, h)*0.08); seat_w, seat_h = max(5.0, w-2*m), max(5.0, h*0.5)
            painter.drawRect((w-seat_w)/2, h-m-seat_h, seat_w, seat_h); painter.setBrush(Qt.white)
            back_h = max(2.0, h * 0.2); painter.drawRect((w-seat_w)/2, max(0.0, h-m-seat_h-back_h), seat_w, back_h)
        elif self.kind == "Plant":
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(QtCore.Qt.black, max(1.5, min(w, h) * 0.02)))
            cx, cy = w / 2.0, h / 2.0
            R = min(w, h) * 0.25
            r2 = R * 0.5
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawEllipse(QtCore.QPointF(cx, cy), R, R)
            painter.drawEllipse(QtCore.QPointF(cx, cy), r2, r2)
            painter.setBrush(QColor(140, 200, 140))
            leaf_w = r2 * 1.4
            leaf_h = r2 * 0.8
            center_up = cy - r2 * 0.05
            for ang in (-20, 100, 220):
                painter.save()
                painter.translate(cx, center_up)
                painter.rotate(ang)
                painter.drawEllipse(QtCore.QRectF(-leaf_w / 2.0, -leaf_h / 2.0, leaf_w, leaf_h))
                painter.restore()
            dot = r2 * 0.12
            painter.drawEllipse(QtCore.QPointF(cx, center_up), dot, dot)
        else: painter.drawRect(r)
    
    def wheelEvent(self, event):
        step = 10
        old_rot = self.rotation()
        new_rot = old_rot + (step if event.delta() > 0 else -step)
        self.setRotation(new_rot)
        sc = self.scene()
        if sc:
            rect = self.sceneBoundingRect()
            inside = sc.is_item_inside_room(rect)
            collides = sc.is_colliding_with_furniture(rect, exclude_item=self)
            if not inside or collides:
                self.setRotation(old_rot)
                return
            us = sc._get_undo_stack()
            if us:
                import command
                us.push(command.RotateItemCommand(self, old_rot, new_rot))
        event.accept()

    def mousePressEvent(self, event):
        self._undo_start_pos = self.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        old = getattr(self, "_undo_start_pos", None)
        new = self.pos()
        if old is not None and old != new:
            sc = self.scene()
            if sc:
                us = sc._get_undo_stack()
                if us:
                    import command
                    us.push(command.MoveItemCommand(self, old, new))
        super().mouseReleaseEvent(event)
