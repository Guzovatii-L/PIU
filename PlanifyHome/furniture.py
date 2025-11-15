from __future__ import annotations
from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QPainterPath

class ResizeHandle(QtWidgets.QGraphicsRectItem):
    SIZE = 14 
    def __init__(self, parent_item: 'FurnitureItem'):
        super().__init__(-self.SIZE/2, -self.SIZE/2, self.SIZE, self.SIZE, parent_item)
        self._parent = parent_item
        self._parent_was_movable = False

        self.setBrush(Qt.white)
        self.setPen(QPen(Qt.black, 1))
        self.setCursor(Qt.SizeFDiagCursor)
        self.setZValue(1_000_000) 
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setAcceptHoverEvents(True)

        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsMovable |
            QtWidgets.QGraphicsItem.ItemSendsGeometryChanges |
            QtWidgets.QGraphicsItem.ItemIgnoresParentOpacity |
            QtWidgets.QGraphicsItem.ItemIgnoresTransformations
        )

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        self._parent_was_movable = bool(self._parent.flags() & QtWidgets.QGraphicsItem.ItemIsMovable)
        if self._parent_was_movable:
            self._parent.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
        event.accept()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        if self._parent_was_movable:
            self._parent.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        event.accept()
        super().mouseReleaseEvent(event)

    def hoverEnterEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent):
        self.setBrush(QColor(230, 230, 230))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent):
        self.setBrush(Qt.white)
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            p: QPointF = value
            new_w = max(self._parent._min_w, p.x())
            new_h = max(self._parent._min_h, p.y())
            return QPointF(new_w, new_h) 
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            p = self.pos()
            self._parent.resize_to(p.x(), p.y())
        return super().itemChange(change, value)


class FurnitureItem(QtWidgets.QGraphicsRectItem):
    def __init__(self, kind: str, x: float, y: float, w: float, h: float):
        super().__init__(0, 0, w, h)
        self.kind = kind
        self.setPos(x, y)

        self._min_w, self._min_h = 60.0, 40.0

        if self.kind == "Table":
            self._min_w = 100.0
            self._min_h = 90.0
        elif self.kind == "Bed":
            self._min_w, self._min_h = 100.0, 80.0
        elif self.kind == "Sofa":
            self._min_w, self._min_h = 120.0, 50.0
        elif self.kind=="Wardrobe":
            self._min_w, self._min_h = 90.0, 60.0

        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsMovable |
            QtWidgets.QGraphicsItem.ItemIsSelectable |
            QtWidgets.QGraphicsItem.ItemSendsGeometryChanges |
            QtWidgets.QGraphicsItem.ItemIsFocusable
        )
    
        self.handle = ResizeHandle(self)
        self.handle.hide()
        self.update_handles()

    def resize_to(self, new_w: float, new_h: float):
        new_w = max(self._min_w, new_w)
        new_h = max(self._min_h, new_h)
        r = self.rect()
        if abs(new_w - r.width()) > 0.1 or abs(new_h - r.height()) > 0.1:
            self.prepareGeometryChange()
            self.setRect(0, 0, new_w, new_h)
            self.update_handles()
            self.update()

    def update_handles(self):
        r = self.rect()
        self.handle.setPos(r.width(), r.height())

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemSelectedHasChanged:
            if self.isSelected():
                self.handle.show()
            else:
                self.handle.hide()
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        w, h = r.width(), r.height()

        if self.kind == "Bed":
            painter.setPen(QPen(Qt.black, 2))
            painter.setBrush(QColor(240, 240, 240)) 
            painter.drawRect(r)

            painter.setPen(QPen(Qt.black, 1))
            painter.setBrush(QColor(220, 220, 220)) 
            head_h = min(20.0, h * 0.2)
            painter.drawRect(0, 0, w, head_h)

            painter.setBrush(Qt.white) 
            pw, ph = w * 0.2, h * 0.18
            painter.drawRect(10, 5, pw, ph)
            painter.drawRect(w - 10 - pw, 5, pw, ph)

        elif self.kind == "Sofa":
            painter.setPen(QPen(Qt.black, 2))
            painter.setBrush(QColor(240, 240, 240)) 
            painter.drawRect(r)

            painter.setPen(QPen(Qt.black, 1))
            painter.setBrush(QColor(220, 220, 220)) 
            painter.drawRect(0, 0, w, h * 0.2)

            painter.setBrush(Qt.white) 
            cw, ch = w * 0.2, h * 0.4
            painter.drawRect(12, h * 0.25, cw, ch)
            painter.drawRect(w - 12 - cw, h * 0.25, cw, ch)

        elif self.kind == "Table":
            r = self.rect()
            w, h = r.width(), r.height()

            painter.setPen(QPen(Qt.black, 2))
            painter.setBrush(QColor(240, 240, 240))

            m = max(6.0, min(w, h) * 0.08)
            seat_h = max(18.0, h * 0.16)
            back_h = max(6.0, seat_h * 0.3)

            top_gap = max(6.0, h * 0.08)
            table_w = max(40.0, w - 2 * m)
            table_h = max(30.0, h - 2 * (m + seat_h + back_h))
            table_x = (w - table_w) / 2.0
            table_y = m + seat_h + back_h

            path = QtGui.QPainterPath()
            path.addRoundedRect(QtCore.QRectF(table_x, table_y, table_w, table_h), 12, 12)
            painter.drawPath(path)

            painter.setPen(QPen(Qt.black, 1))
            painter.setBrush(Qt.white)
            seat_w = max(24.0, table_w * 0.18)
            gaps = 4.0
            spacing = max(4.0, (table_w - 3 * seat_w) / gaps)
            cx = table_x + spacing

            y_top_seat = m + back_h - top_gap
            y_top_back = m - top_gap
            y_bot_seat = table_y + table_h + m
            y_bot_back = y_bot_seat + seat_h

            for _ in range(3):
                painter.drawRect(cx, y_top_seat, seat_w, seat_h) 
                painter.drawRect(cx, y_top_back, seat_w, back_h) 
                painter.drawRect(cx, y_bot_seat, seat_w, seat_h) 
                painter.drawRect(cx, y_bot_back, seat_w, back_h) 
                cx += seat_w + spacing

        elif self.kind=="Wardrobe":
            painter.setPen(QPen(QtGui.Qt.black, 2))
            painter.setBrush(QColor(240, 240, 240))
            painter.drawRect(r) 

            painter.setPen(QPen(QtGui.Qt.black, 1))
            margin = max(4.0, min(w, h) * 0.05)
            painter.drawLine(w * 0.5, margin, w * 0.5, h - margin)


            base_h = max(4.0, h * 0.06)
            painter.setBrush(QColor(220, 220, 220))
            painter.drawRect(0, h - base_h, w, base_h)

            painter.setBrush(QtGui.Qt.white)
            handle_h = max(12.0, h * 0.18)
            handle_w = max(4.0,  w * 0.06)
            handle_gap = max(6.0, w * 0.06)

            y = (h - handle_h) / 2.0
            x_left  = (w * 0.5) - handle_gap - handle_w
            x_right = (w * 0.5) + handle_gap
            painter.drawRoundedRect(x_left,  y, handle_w, handle_h, 2, 2)
            painter.drawRoundedRect(x_right, y, handle_w, handle_h, 2, 2)
            
        else:
            painter.setPen(QPen(Qt.black, 1))
            painter.setBrush(Qt.white)
            painter.drawRect(r)