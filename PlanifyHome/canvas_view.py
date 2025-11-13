from PySide6 import QtCore, QtGui
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsView, QApplication

from canvas_scene import CanvasScene 


class CanvasView(QGraphicsView):
    mouse_moved = QtCore.Signal(QPointF)

    def __init__(self, scene: CanvasScene, parent=None):
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
        sc: CanvasScene = self.scene() 
        
        if e.key() == Qt.Key_Space:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            e.accept(); return
        
        if e.key() == Qt.Key_Escape:
            if sc._current_item is not None:
                 if isinstance(sc._current_item, tuple):
                    for item in sc._current_item:
                        sc.removeItem(item)
                 else:
                     sc.removeItem(sc._current_item)
                 sc._current_item = None
            
            if self.main_window:
                self.main_window.set_mode("Select")
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