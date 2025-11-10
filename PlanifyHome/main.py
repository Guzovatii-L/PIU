from __future__ import annotations

import math
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QToolBar, QDockWidget, QListWidget, QListWidgetItem, QMessageBox)

GRID_SIZE = 50
SCENE_MARGIN = 2000

TOOLS = ["Wall", "Door", "Window"]
FURNITURE = ["Bed", "Table", "Sofa", "Wardrobe"]

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

    def add_door(self, start: QPointF, end: QPointF):
        line_pen = QPen(Qt.blue, 3)
        line_item = self.addLine(start.x(), start.y(), end.x(), end.y(), line_pen)

        swing_radius = math.hypot(end.x() - start.x(), end.y() - start.y())
        path = QtGui.QPainterPath(start)
        path.arcTo(start.x() - swing_radius, start.y() - swing_radius,
                   swing_radius * 2, swing_radius * 2, 0, 90)
        arc_item = QtWidgets.QGraphicsPathItem(path)
        arc_item.setPen(QPen(Qt.blue, 1))
        arc_item.setBrush(QColor(0, 0, 255, 50))  # semi-transparent swing
        self.addItem(arc_item)

        return (line_item, arc_item)

    def add_window(self, start: QPointF, end: QPointF):
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

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        if event.button() == Qt.LeftButton and self.parent_widget._current_mode in ("Wall", "Door", "Window"):
            pos = self.snap_to_grid(event.scenePos())
            kind = self.parent_widget._current_mode

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
                line.setLine(line.line().x1(), line.line().y1(), end.x(), end.y())

                dx = end.x() - line.line().x1()
                dy = end.y() - line.line().y1()
                swing_radius = math.hypot(dx, dy)
                path = QtGui.QPainterPath(QPointF(line.line().x1(), line.line().y1()))
                path.arcTo(line.line().x1() - swing_radius, line.line().y1() - swing_radius,
                           swing_radius * 2, swing_radius * 2, 0, 90)
                arc.setPath(path)
            elif isinstance(self._current_item, QtWidgets.QGraphicsLineItem):
                line = self._current_item.line()
                line.setP2(end)
                self._current_item.setLine(line)

        super().mouseMoveEvent(event)
    def drawBackground(self, painter: QPainter, rect: QRectF):
        painter.save()
        painter.fillRect(rect, Qt.white)

        step = GRID_SIZE
        left = int(math.floor(rect.left() / step) * step)
        top = int(math.floor(rect.top() / step) * step)

        painter.setPen(QPen(QColor(0, 0, 0), 1))
        y = top
        while y < rect.bottom():
            painter.drawLine(rect.left(), y, rect.right(), y)
            y += step
        x = left
        while x < rect.right():
            painter.drawLine(x, rect.top(), x, rect.bottom())
            x += step

        painter.setPen(QPen(QColor(0, 0, 0), 1.4))
        for i in range(left, int(rect.right()), step * 5):
            painter.drawLine(i, rect.top(), i, rect.bottom())
        for j in range(top, int(rect.bottom()), step * 5):
            painter.drawLine(rect.left(), j, rect.right(), j)

        painter.restore()

    def color_for(self, kind: str) -> QColor:
        if kind == "Wall":
            return Qt.black
        elif kind == "Door":
            return Qt.blue
        elif kind == "Window":
            return Qt.red
        return Qt.gray


class CanvasView(QGraphicsView):
    mouse_moved = QtCore.Signal(QPointF)

    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(scene)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setMouseTracking(True)
        self.main_window = parent
        scene.parent_widget = parent

    def wheelEvent(self, e: QtGui.QWheelEvent):
        if QApplication.keyboardModifiers() & Qt.ControlModifier:
            factor = 1.25 if e.angleDelta().y() > 0 else 0.8
            self.scale(factor, factor)
            e.accept(); return
        super().wheelEvent(e)

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        if e.key() == Qt.Key_Space:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            e.accept(); return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e: QtGui.QKeyEvent):
        if e.key() == Qt.Key_Space:
            self.setDragMode(QGraphicsView.NoDrag)
            e.accept(); return
        super().keyReleaseEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        self.mouse_moved.emit(self.mapToScene(e.position().toPoint()))
        super().mouseMoveEvent(e)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Planify Home – UI")
        self.resize(1280, 800)

        self.scene = CanvasScene(parent=self)
        self.view = CanvasView(self.scene, parent=self)
        self.setCentralWidget(self.view)

        self.status = self.statusBar()
        self.view.mouse_moved.connect(self._on_mouse_moved)
        self._current_mode = "Select"
        self._update_status_ready()

        self._build_toolbar()

        self._build_right_palette()

    def _build_toolbar(self):
        tb = QToolBar("Main")
        tb.setIconSize(QtCore.QSize(20, 20))
        self.addToolBar(tb)

        self.act_new = QAction("New", self)
        self.act_open = QAction("Open", self)
        self.act_save = QAction("Save", self)
        self.act_export = QAction("Export", self)
        self.act_new.setShortcut(QKeySequence.New)
        self.act_open.setShortcut(QKeySequence.Open)
        self.act_save.setShortcut(QKeySequence.Save)

        self.act_undo = QAction("Undo", self)
        self.act_redo = QAction("Redo", self)
        self.act_undo.setShortcut(QKeySequence.Undo)
        self.act_redo.setShortcut(QKeySequence.Redo)

        tb.addActions([self.act_new, self.act_open, self.act_save, self.act_export])
        tb.addSeparator()
        tb.addActions([self.act_undo, self.act_redo])

        for a, name in [
            (self.act_new, "New"), (self.act_open, "Open"),
            (self.act_save, "Save"), (self.act_export, "Export"),
            (self.act_undo, "Undo"), (self.act_redo, "Redo")]:
            a.triggered.connect(lambda _=False, n=name: self._stub_action(n))

    def _build_right_palette(self):
        dock = QDockWidget("Palette", self)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.SingleSelection)

        header_tools = QListWidgetItem("— Tools —")
        header_tools.setFlags(Qt.ItemIsEnabled)
        self.list.addItem(header_tools)
        for name in TOOLS:
            it = QListWidgetItem(name)
            it.setData(Qt.UserRole, ("tool", name))
            self.list.addItem(it)

        header_f = QListWidgetItem("— Furniture —")
        header_f.setFlags(Qt.ItemIsEnabled)
        self.list.addItem(header_f)
        for name in FURNITURE:
            it = QListWidgetItem(name)
            it.setData(Qt.UserRole, ("furniture", name))
            self.list.addItem(it)

        self.list.itemClicked.connect(self._palette_clicked)
        dock.setWidget(self.list)

    def _stub_action(self, name: str):
        QMessageBox.information(self, name, f"'{name}' is not implemented yet. (UI only)")

    @QtCore.Slot(QListWidgetItem)
    def _palette_clicked(self, item: QListWidgetItem):
        payload = item.data(Qt.UserRole)
        if not payload:
            return
        kind, name = payload
        if kind == "tool":
            self._current_mode = name
        else:
            self._current_mode = f"Furniture: {name}"
        self._update_status_ready()

    def _update_status_ready(self):
        self.status.showMessage(f"Mode: {self._current_mode} | Zoom: Ctrl+Wheel | Pan: Space+Drag")

    @QtCore.Slot(QPointF)
    def _on_mouse_moved(self, p: QPointF):
        self.status.showMessage(
            f"x={p.x():.0f} y={p.y():.0f} | Mode: {self._current_mode} | Zoom: Ctrl+Wheel | Pan: Space+Drag"
        )


def main():
    app = QApplication([])
    w = MainWindow()
    w.show()
    app.exec()


if __name__ == "__main__":
    main()