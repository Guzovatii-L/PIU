from PySide6.QtGui import QUndoCommand
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem


class AddItemCommand(QUndoCommand):
    def __init__(self, items: QGraphicsItem | tuple[QGraphicsItem, ...], scene: QGraphicsScene, description: str):
        super().__init__(description)
        self.scene = scene
        self.items = items if isinstance(items, tuple) else (items,)
        self.added_to_scene = False

    def redo(self):
        for item in self.items:
            if item.scene() is not self.scene:
                self.scene.addItem(item)
        self.added_to_scene = True
        if hasattr(self.scene, "show_wall_end_markers"):
            self.scene.show_wall_end_markers()

    def undo(self):
        if not self.added_to_scene:
            return
        for item in self.items:
            if item.scene() is self.scene:
                if hasattr(item, "prepare_for_delete"):
                    item.prepare_for_delete()
                self.scene.removeItem(item)
        self.added_to_scene = False
        if hasattr(self.scene, "show_wall_end_markers"):
            self.scene.show_wall_end_markers()


class DeleteItemsCommand(QUndoCommand):
    def __init__(self, items: list[QGraphicsItem], scene: QGraphicsScene, description: str):
        super().__init__(description)
        self.scene = scene
        self.items_data = []
        for item in items:
            self.items_data.append(
                {
                    "item": item,
                    "pos": item.scenePos(),
                    "selected": item.isSelected(),
                    "zValue": item.zValue(),
                }
            )

    def redo(self):
        for data in self.items_data:
            item = data["item"]
            if item.scene() is self.scene:
                if hasattr(item, "prepare_for_delete"):
                    item.prepare_for_delete()
                self.scene.removeItem(item)
        if hasattr(self.scene, "show_wall_end_markers"):
            self.scene.show_wall_end_markers()

    def undo(self):
        for data in self.items_data:
            item = data["item"]
            self.scene.addItem(item)
            item.setPos(data["pos"])
            item.setZValue(data["zValue"])
            item.setSelected(data["selected"])
            if hasattr(item, "_show_handles") and item.isSelected():
                item._show_handles(True)
        if hasattr(self.scene, "show_wall_end_markers"):
            self.scene.show_wall_end_markers()


class ResizeItemCommand(QUndoCommand):
    def __init__(self, item: QGraphicsItem, old_rect, new_rect, description: str):
        super().__init__(description)
        self.item = item
        self.old_rect = old_rect
        self.new_rect = new_rect

    def _apply_rect(self, rectf):
        if hasattr(self.item, "prepareGeometryChange"):
            self.item.prepareGeometryChange()
        if hasattr(self.item, "setRect"):
            self.item.setRect(0, 0, rectf.width(), rectf.height())
        if hasattr(self.item, "update_handles"):
            self.item.update_handles()
        if hasattr(self.item, "update"):
            self.item.update()

    def redo(self):
        self._apply_rect(self.new_rect)

    def undo(self):
        self._apply_rect(self.old_rect)
