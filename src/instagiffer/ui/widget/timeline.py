import math

from PySide6 import QtGui, QtWidgets


class TimeLine(QtWidgets.QWidget):
    def __init__(self, parent, height=30):
        super().__init__(parent)
        self.setFixedHeight(height)
        self._chunks = {}

    def initial_frames(self, original_width: int, original_height: int) -> tuple[int, int, int]:
        """Given the width and height of source footage return number of
        needed frames to cover the timeline initially."""
        scale_factor = self.height() / original_height
        thumb_width = int(original_width * scale_factor)
        num_thumbs = math.ceil(self.width() / thumb_width)
        return thumb_width, self.height(), num_thumbs

    def set_chunk_data(self, width, num_chunks):
        self._num_chunks = num_chunks
        self._chunks_width = width

    def push_chunk(self, index: int, chunk: bytes):
        # if not len(self._chunks) == index:
        #     print(f'{len(self._chunks) = } / {index = }')
        w = self._chunks_width
        h = self.height()
        img = QtGui.QImage(chunk, w, h, w * 3, QtGui.QImage.Format.Format_RGB888)
        self._chunks[index] = QtGui.QPixmap.fromImage(img)

    def paintEvent(self, event):
        w = self.width() / self._num_chunks
        with QtGui.QPainter(self) as painter:
            for i, chunk in self._chunks.items():
                painter.drawPixmap(w * i, 0, chunk)
