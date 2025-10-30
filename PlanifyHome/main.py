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

class CanvasScene(QGraphicsScene):
    def __init__(self):
        super().__init__(-SCENE_MARGIN, -SCENE_MARGIN, 2 * SCENE_MARGIN, 2 * SCENE_MARGIN)

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


class CanvasView(QGraphicsView):
    mouse_moved = QtCore.Signal(QPointF)

    def __init__(self, scene: QGraphicsScene):
        super().__init__(scene)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setMouseTracking(True)

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

        self.scene = CanvasScene()
        self.view = CanvasView(self.scene)
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
