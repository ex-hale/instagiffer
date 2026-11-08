from PySide6 import QtCore, QtGui, QtWidgets


class IgfView(QtWidgets.QGraphicsView):
    def __init__(self, parent):
        super().__init__(parent)
        self._scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self._scene)
        self._item = self._scene.addPixmap(QtGui.QPixmap())
        self.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        self.setBackgroundBrush(QtGui.QColor("#101010"))
        # zoom centered on cursor, pan by dragging
        self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)

    def set_frame(self, image: QtGui.QImage):
        first = self._item.pixmap().isNull()
        self._item.setPixmap(QtGui.QPixmap.fromImage(image))
        if first:
            self.fitInView(self._item, QtCore.Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)
        event.accept()
