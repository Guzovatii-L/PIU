from __future__ import annotations
from PySide6.QtGui import QUndoCommand
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem
from PySide6.QtCore import QRectF

class AddItemCommand(QUndoCommand):
    def __init__(self, items: QGraphicsItem | tuple[QGraphicsItem, ...], scene: QGraphicsScene, description: str):
        super().__init__(description)
        self.scene = scene
        self.items = items if isinstance(items, tuple) else (items,)
        self.added = False

    def redo(self):
        if self.added:
            return
        for it in self.items:
            if it.scene() is not self.scene:
                self.scene.addItem(it)
            if it.__class__.__name__ == "WallItem":
                if it.__class__.__name__ == "WallItem": 
                    it.setFlag(QGraphicsItem.ItemIsSelectable, True) 
                    it.setFlag(QGraphicsItem.ItemIsMovable, True)
                    it._old_pos_for_undo = None
                    it._suppress_move_command = False  
                if hasattr(it, "_update_handles"):
                    it._update_handles() 
                if hasattr(it, "_update_dimension_text"): 
                    it._update_dimension_text()       
        self.added = True
        if hasattr(self.scene, "show_wall_end_markers"): 
            self.scene.show_wall_end_markers() 

    def undo(self):
        if not self.added:
            return
        if hasattr(self.scene, "clear_wall_end_markers"): 
            self.scene.clear_wall_end_markers()
        for it in self.items:
            if it.scene() is self.scene:
                if it.__class__.__name__ == "WallItem" and hasattr(it, "prepare_for_delete"): 
                    it.prepare_for_delete()
                self.scene.removeItem(it)
        self.added = False
        if hasattr(self.scene, "show_wall_end_markers"): 
            self.scene.show_wall_end_markers()


class DeleteItemsCommand(QUndoCommand):
    def __init__(self, items: list[QGraphicsItem], scene: QGraphicsScene, description: str):
        super().__init__(description)
        self.scene = scene
        self.items_data: list[dict] = []
        for it in items:
            self.items_data.append({
                "item": it,
                "pos": it.scenePos(),
                "z": it.zValue(),
                "selected": it.isSelected()
            })

    def redo(self):
        if hasattr(self.scene, "clear_wall_end_markers"): 
            self.scene.clear_wall_end_markers()
        for d in self.items_data:
            it = d["item"]
            if it.__class__.__name__ == "WallItem":
                if hasattr(it, "prepare_for_delete"):
                    it.prepare_for_delete()
            if it.scene() is self.scene:
                self.scene.removeItem(it)

    def undo(self):
        for d in self.items_data:
            it = d["item"]
            self.scene.addItem(it)
            it.setPos(d["pos"])
            it.setZValue(d["z"])
            it.setSelected(d["selected"])
            if it.__class__.__name__ == "WallItem":
                it.setFlag(QGraphicsItem.ItemIsSelectable, True) 
                it.setFlag(QGraphicsItem.ItemIsMovable, True) 
                it._update_handles() 
                it._update_dimension_text()
                it._old_pos_for_undo = None 
                it._suppress_move_command = False
            if hasattr(it, "_show_handles") and it.isSelected():
                it._show_handles(True)
        if hasattr(self.scene, "show_wall_end_markers"): 
            self.scene.show_wall_end_markers()


class ResizeItemCommand(QUndoCommand):
    def __init__(self, item: QGraphicsItem, start_rect: QRectF, end_rect: QRectF, description: str):
        super().__init__(description)
        self.item = item
        self.start_rect = QRectF(start_rect)
        self.end_rect = QRectF(end_rect)

    def redo(self):
        if hasattr(self.item, "prepareGeometryChange"):
            self.item.prepareGeometryChange()
        if hasattr(self.item, "setRect"):
            self.item.setRect(self.end_rect)

        if hasattr(self.item, "update_handles"):
            self.item.update_handles()
        if hasattr(self.item, "update"):
            self.item.update()

    def undo(self):
        if hasattr(self.item, "prepareGeometryChange"):
            self.item.prepareGeometryChange()
        if hasattr(self.item, "setRect"):
            self.item.setRect(self.start_rect)

        if hasattr(self.item, "update_handles"):
            self.item.update_handles()
        if hasattr(self.item, "update"):
            self.item.update()


class WallResizeCommand(QUndoCommand):
    def __init__(self, wall_item, old_line, new_line, description: str):
        super().__init__(description)
        self.wall = wall_item
        self.old = old_line
        self.new = new_line

    def _apply(self, line):
        self.wall.setLine(line)
        if hasattr(self.wall, "_update_handles"):
            self.wall._update_handles()
        if hasattr(self.wall, "_update_dimension_text"):
            self.wall._update_dimension_text()
        sc = self.wall.scene()
        if sc and hasattr(sc, "show_wall_end_markers"):
            sc.show_wall_end_markers()

    def redo(self):
        self._apply(self.new)

    def undo(self):
        self._apply(self.old)


class MoveItemCommand(QUndoCommand):
    def __init__(self, item, old_pos, new_pos, description="Move Item"):
        super().__init__(description)
        self.item = item
        self.old_pos = old_pos
        self.new_pos = new_pos

    def undo(self):
        self.item._suppress_move_command = True
        self.item.setPos(self.old_pos)
        if hasattr(self.item, "_update_handles"):
            self.item._update_handles()
        if hasattr(self.item, "_update_dimension_text"):
            self.item._update_dimension_text()
        self.item._suppress_move_command = False

    def redo(self):
        self.item._suppress_move_command = True
        self.item.setPos(self.new_pos)
        if hasattr(self.item, "_update_handles"):
            self.item._update_handles()
        if hasattr(self.item, "_update_dimension_text"):
            self.item._update_dimension_text()
        self.item._suppress_move_command = False


class RotateItemCommand(QUndoCommand):
    def __init__(self, item, old_rot, new_rot, text="Rotate Item"):
        super().__init__(text)
        self.item = item
        self.old_rot = old_rot
        self.new_rot = new_rot

    def undo(self):
        self.item.setRotation(self.old_rot)

    def redo(self):
        self.item.setRotation(self.new_rot)

