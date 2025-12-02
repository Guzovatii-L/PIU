from PySide6.QtGui import QUndoCommand
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem

class AddItemCommand(QUndoCommand):

    def __init__(self, items: QGraphicsItem | tuple[QGraphicsItem, ...],
                 scene: QGraphicsScene, description: str):
        super().__init__(description)
        self.scene = scene
        self.items = items if isinstance(items, tuple) else (items,)
        self.added_to_scene = False

    def redo(self):

        if self.added_to_scene:
            return

        for item in self.items:
            if item.scene() is not self.scene:
                self.scene.addItem(item)

        self.added_to_scene = True

    def undo(self):
        if not self.added_to_scene:
            return

        for item in self.items:
            if item.scene() is self.scene:
                self.scene.removeItem(item)

        self.added_to_scene = False


class DeleteItemsCommand(QUndoCommand):

    def __init__(self, items: list[QGraphicsItem], scene: QGraphicsScene, description: str):
        super().__init__(description)
        self.scene = scene
        self.items_data = []

        for item in items:
            self.items_data.append({
                'item': item,
                'pos': item.scenePos(),
                'selected': item.isSelected(),
                'zValue': item.zValue()
            })

    def redo(self):
        for data in self.items_data:
            item = data['item']
            if item.scene() is self.scene:
                self.scene.removeItem(item)

    def undo(self):
        for data in self.items_data:
            item = data['item']
            self.scene.addItem(item)
            item.setPos(data['pos'])
            item.setZValue(data['zValue'])
            item.setSelected(data['selected'])
            if hasattr(item, '_show_handles') and item.isSelected():
                item._show_handles(True)
