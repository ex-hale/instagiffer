from PySide6 import QtCore, QtGui, QtWidgets


class TimeLine(QtWidgets.QWidget):
    seeked = QtCore.Signal(float)

    def __init__(self, parent=None, height=30):
        super().__init__(parent)
        self.setFixedHeight(height)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._chunks: dict[int, QtGui.QPixmap] = {}
        self._num_chunks = 0
        self._chunk_width = 0
        self._duration = 0.0
        self._position = 0.0
        self._strip: QtGui.QPixmap | None = None
        self._dirty = True
        self._dragging = False

    def set_timeline(self, duration: float, num_chunks: int, chunk_width: int):
        self._duration, self._num_chunks, self._chunk_width = duration, num_chunks, chunk_width
        self._chunks.clear()
        self._dirty = True
        self.update()

    def push_chunk(self, index: int, data: bytes):
        h = self.height()
        img = QtGui.QImage(
            data, self._chunk_width, h, self._chunk_width * 3, QtGui.QImage.Format.Format_RGB888
        )
        self._chunks[index] = QtGui.QPixmap.fromImage(img)
        self._dirty = True
        self.update()

    def set_position(self, seconds: float):
        self._position = max(0.0, min(seconds, self._duration))
        self.update()

    def _fraction_at(self, x: float) -> float:
        return max(0.0, min(1.0, x / max(1, self.width())))

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._dragging = True
            self.seeked.emit(self._fraction_at(event.position().x()))

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.seeked.emit(self._fraction_at(event.position().x()))

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._dragging = False

    def _compose_strip(self):
        """Compose all chunks into one pixmap once; paintEvent then just blits it."""
        w, h = self.width(), self.height()
        strip = QtGui.QPixmap(w, h)
        strip.fill(QtGui.QColor('#202020'))
        p = QtGui.QPainter(strip)
        cw = w / self._num_chunks if self._num_chunks else 0
        for i in range(self._num_chunks):
            x = cw * i
            chunk = self._chunks.get(i)
            if chunk is not None:
                p.drawPixmap(QtCore.QRectF(x, 0, cw, h), chunk, QtCore.QRectF(chunk.rect()))
            else:
                p.fillRect(QtCore.QRectF(x, 0, cw, h), QtGui.QColor('#333333'))
        p.end()
        self._strip = strip
        self._dirty = False

    def paintEvent(self, event):
        if self._num_chunks and (self._dirty or self._strip is None):
            self._compose_strip()
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        if self._strip is not None:
            p.drawPixmap(0, 0, self._strip)
        else:
            p.fillRect(self.rect(), QtGui.QColor('#202020'))
        if self._duration > 0:  # playhead + handle
            x = self._position / self._duration * self.width()
            p.setPen(QtGui.QPen(QtGui.QColor('#ff5252'), 2))
            p.drawLine(QtCore.QPointF(x, 0), QtCore.QPointF(x, self.height()))
            p.setBrush(QtGui.QColor('#ff5252'))
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.drawPolygon(
                # QtCore.QMetaType.Type.QPolygonF(
                [QtCore.QPointF(x - 5, 0), QtCore.QPointF(x + 5, 0), QtCore.QPointF(x, 8)]
                # )
            )
        p.end()

    def resizeEvent(self, event):
        self._dirty = True
        super().resizeEvent(event)
