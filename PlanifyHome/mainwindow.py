from PySide6 import QtCore
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QAction, QKeySequence, QUndoStack, QImage, QPainter
from PySide6.QtWidgets import (
    QMainWindow, QToolBar, QDockWidget, QListWidget, QListWidgetItem,
    QMessageBox, QFileDialog
)
import json

from constants import TOOLS, FURNITURE
from canvas_scene import CanvasScene
from canvas_view import CanvasView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Planify Home – UI")
        self.resize(1280, 800)

        self.scene = CanvasScene(parent=self)
        self.view = CanvasView(self.scene, parent=self)
        self.setCentralWidget(self.view)

        self.undo_stack = QUndoStack(self)

        self.status = self.statusBar()
        self.view.mouse_moved.connect(self._on_mouse_moved)
        self._current_mode = "Select"
        self._update_status_ready()

        self._build_toolbar()
        self._build_right_palette()

    def set_mode(self, label: str):
        self._current_mode = label
        self._update_status_ready()
        if hasattr(self, "scene"):
            if label == "Wall":
                self.scene.show_wall_end_markers()
            else:
                self.scene.clear_wall_end_markers()

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

        self.act_undo = self.undo_stack.createUndoAction(self, "Undo")
        self.act_redo = self.undo_stack.createRedoAction(self, "Redo")
        self.act_undo.setShortcut(QKeySequence.Undo)
        self.act_redo.setShortcut(QKeySequence.Redo)
        self.undo_stack.canUndoChanged.connect(self.act_undo.setEnabled)
        self.undo_stack.canRedoChanged.connect(self.act_redo.setEnabled)
        self.act_undo.setEnabled(self.undo_stack.canUndo())
        self.act_redo.setEnabled(self.undo_stack.canRedo())

        tb.addActions([self.act_new, self.act_open, self.act_save, self.act_export])
        tb.addSeparator()
        tb.addActions([self.act_undo, self.act_redo])

        self.act_new.triggered.connect(self._action_new)
        self.act_open.triggered.connect(self._action_open)
        self.act_save.triggered.connect(self._action_save)
        self.act_export.triggered.connect(self._action_export)

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

    def _action_new(self):
        try:
            self.scene.load_from_json({"walls": [], "doors": [], "windows": [], "furniture": []})
            self.set_mode("Select")
        except Exception as e:
            QMessageBox.critical(self, "New failed", str(e))

    def _action_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open", "", "Planify (*.json);;All files (*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.scene.load_from_json(data)
            self.set_mode("Select")
        except Exception as e:
            QMessageBox.critical(self, "Open failed", str(e))

    def _action_save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save", "plan.json", "Planify (*.json);;All files (*)")
        if not path:
            return
        try:
            data = self.scene.to_json()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))

    def _action_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export image", "plan.png", "PNG Image (*.png)")
        if not path:
            return
        try:
            self._export_png(path)
            QMessageBox.information(self, "Export", "Image exported.")
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))

    def _export_png(self, path: str, scale: float = 2.0):
        self.scene.clearSelection()
        self.scene.clear_wall_end_markers()

        rect = self.scene.itemsBoundingRect()
        if rect.isEmpty():
            rect = self.scene.sceneRect()
        rect = rect.marginsAdded(QtCore.QMarginsF(10, 10, 10, 10))

        w = max(1, int(rect.width() * scale))
        h = max(1, int(rect.height() * scale))

        img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.white)

        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing, True)

        target = QtCore.QRectF(0, 0, w, h)
        self.scene.render(p, target, rect)

        p.end()
        img.save(path)


    @QtCore.Slot(QListWidgetItem)
    def _palette_clicked(self, item: QListWidgetItem):
        payload = item.data(Qt.UserRole)
        if not payload:
            return
        kind, name = payload
        if kind == "tool":
            self.set_mode(name)
        else:
            self.set_mode(f"Furniture: {name}")

    def _update_status_ready(self):
        self.status.showMessage(f"Mode: {self._current_mode} | Zoom: Ctrl+Wheel | Pan: Space+Drag")

    @QtCore.Slot(QPointF)
    def _on_mouse_moved(self, p: QPointF):
        self.status.showMessage(
            f"x={p.x():.0f} y={p.y():.0f} | Mode: {self._current_mode} | Zoom: Ctrl+Wheel | Pan: Space+Drag"
        )
