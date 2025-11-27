from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainter, QPen, QColor


class ResizeHandle(QtWidgets.QGraphicsRectItem):
    SIZE = 14

    def __init__(self, parent_item: 'FurnitureItem'):
        super().__init__(-self.SIZE / 2, -self.SIZE / 2, self.SIZE, self.SIZE, parent_item)
        self._parent = parent_item
        self._parent_was_movable = False

        self.setBrush(QtCore.Qt.white)
        self.setPen(QPen(QtCore.Qt.black, 1))
        self.setCursor(QtCore.Qt.SizeFDiagCursor)
        self.setZValue(1_000_000)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.setAcceptHoverEvents(True)

        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsMovable
            | QtWidgets.QGraphicsItem.ItemSendsGeometryChanges
            | QtWidgets.QGraphicsItem.ItemIgnoresParentOpacity
            | QtWidgets.QGraphicsItem.ItemIgnoresTransformations
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
        self.setBrush(QtCore.Qt.white)
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            p: QPointF = value
            new_w = max(self._parent._min_w, p.x())
            new_h = max(self._parent._min_h, p.y())
            return QtCore.QPointF(new_w, new_h)
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
            self._min_w, self._min_h = 80.0, 50.0
        elif self.kind == "Bed":
            self._min_w, self._min_h = 100.0, 80.0
        elif self.kind == "Sofa":
            self._min_w, self._min_h = 120.0, 50.0
        elif self.kind == "Wardrobe":
            self._min_w, self._min_h = 70.0, 40.0
        elif self.kind == "Chair":
            self._min_w, self._min_h = 30.0, 34.0
        elif self.kind == "Plant":
            self._min_w, self._min_h = 70.0, 80.0


        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsMovable
            | QtWidgets.QGraphicsItem.ItemIsSelectable
            | QtWidgets.QGraphicsItem.ItemSendsGeometryChanges
            | QtWidgets.QGraphicsItem.ItemIsFocusable
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
            painter.setPen(QPen(QtCore.Qt.black, 2))
            painter.setBrush(QColor(240, 240, 240))
            painter.drawRect(r)
            painter.setPen(QPen(QtCore.Qt.black, 1))
            painter.setBrush(QColor(220, 220, 220))
            head_h = min(20.0, h * 0.2)
            painter.drawRect(0, 0, w, head_h)
            painter.setBrush(QtCore.Qt.white)
            pw, ph = w * 0.2, h * 0.18
            painter.drawRect(10, 5, pw, ph)
            painter.drawRect(w - 10 - pw, 5, pw, ph)

        elif self.kind == "Sofa":
            painter.setPen(QPen(QtCore.Qt.black, 2))
            painter.setBrush(QColor(240, 240, 240))
            painter.drawRect(r)
            painter.setPen(QPen(QtCore.Qt.black, 1))
            painter.setBrush(QColor(220, 220, 220))
            painter.drawRect(0, 0, w, h * 0.2)
            painter.setBrush(QtCore.Qt.white)
            cw, ch = w * 0.2, h * 0.4
            painter.drawRect(12, h * 0.25, cw, ch)
            painter.drawRect(w - 12 - cw, h * 0.25, cw, ch)

        elif self.kind == "Table":
            painter.setPen(QPen(QtCore.Qt.black, 2))
            painter.setBrush(QtCore.Qt.white)
            m = max(6.0, min(w, h) * 0.08)
            table_w = max(40.0, w - 2 * m)
            table_h = max(30.0, h - 2 * m)
            table_x = (w - table_w) / 2.0
            table_y = (h - table_h) / 2.0
            path = QtGui.QPainterPath()
            path.addRoundedRect(QtCore.QRectF(table_x, table_y, table_w, table_h), 12, 12)
            painter.drawPath(path)

        elif self.kind == "Wardrobe":
            painter.setPen(QPen(QtCore.Qt.black, 2))
            painter.setBrush(QtCore.Qt.white)
            painter.drawRect(r)
            painter.setPen(QPen(QtCore.Qt.black, 1))
            painter.drawLine(w * 0.5, 0, w * 0.5, h)
            painter.setBrush(QColor(230, 230, 230))
            r = max(2.0, min(w, h) * 0.04)
            painter.drawEllipse(QtCore.QPointF(w * 0.5 - w * 0.15, h * 0.5), r, r)
            painter.drawEllipse(QtCore.QPointF(w * 0.5 + w * 0.15, h * 0.5), r, r)

        elif self.kind == "Chair":
            painter.setPen(QPen(QtCore.Qt.black, 2))
            painter.setBrush(QtCore.Qt.white)
            m = max(3.0, min(w, h) * 0.08)
            seat_w = max(20.0, w - 2 * m)
            seat_h = max(18.0, h * 0.5)
            seat_x = (w - seat_w) / 2.0
            seat_y = h - m - seat_h
            painter.drawRect(seat_x, seat_y, seat_w, seat_h)
            painter.setPen(QPen(QtCore.Qt.black, 1))
            back_h = max(6.0, h * 0.2)
            back_w = seat_w
            back_x = seat_x
            back_y = max(0.0, seat_y - back_h)
            painter.drawRect(back_x, back_y, back_w, back_h)

        elif self.kind == "Plant":
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(QtCore.Qt.black, max(1.5, min(w, h) * 0.02)))

            cx, cy = w / 2.0, h / 2.0
            R = min(w, h) * 0.25
            r = R * 0.5

            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawEllipse(QtCore.QPointF(cx, cy), R, R)
            painter.drawEllipse(QtCore.QPointF(cx, cy), r, r)

            painter.setBrush(QColor(140, 200, 140))
            leaf_w = r * 1.4
            leaf_h = r * 0.8
            center_up = cy - r * 0.05

            for ang in (-20, 100, 220):
                painter.save()
                painter.translate(cx, center_up)
                painter.rotate(ang)
                painter.drawEllipse(QtCore.QRectF(-leaf_w/2.0, -leaf_h/2.0, leaf_w, leaf_h))
                painter.restore()

            dot = r * 0.12
            painter.drawEllipse(QtCore.QPointF(cx, center_up), dot, dot)

        else:
            painter.setPen(QPen(QtCore.Qt.black, 1))
            painter.setBrush(QtCore.Qt.white)
            painter.drawRect(r)
