from PySide6 import QtCore, QtGui, QtWidgets

import instagiffer
import instagiffer.common

# from instagiffer.config import Config, UiSettings
from instagiffer.ui.widget.stack import IgfStack
from instagiffer.ui.widget.timeline import TimeLine
from instagiffer.ui.widget.view import IgfView

DEFAULT_WIN_SIZE = (800, 500)


class InstagifferUI(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._initial_draw_finished = False

        self.setWindowTitle(f'Instagiffer - {instagiffer.__version__}')
        self.setWindowIcon(QtGui.QIcon(str(instagiffer.common.ASSETS_PATH / 'instagiffer.ico')))

        self.splitter = QtWidgets.QSplitter(self)
        self.splitter.setChildrenCollapsible(False)
        self.setCentralWidget(self.splitter)
        self.stack = IgfStack(self.splitter)

        self.view_widget = QtWidgets.QWidget(self)
        self.view_layout = QtWidgets.QVBoxLayout(self.view_widget)
        self.splitter.addWidget(self.view_widget)

        self.view = IgfView(self)
        self.timeline = TimeLine(self)
        self.view_layout.addWidget(self.view)
        self.view_layout.addWidget(self.timeline)

    def _restore_ui(self):
        """WIP - Restore window position and size or initialize these if unset."""
        # if not hasattr(UiSettings, 'splitter_size'):
        self._init_window_geometry()

    def _init_window_geometry(self):
        geometry = self.geometry()
        scale = 1.0
        geometry.setSize(
            QtCore.QSize(
                int(DEFAULT_WIN_SIZE[0] * scale),
                int(DEFAULT_WIN_SIZE[1] * scale),
            )
        )

        center = geometry.center()
        pointer_pos = QtGui.QCursor.pos()

        for screen in QtWidgets.QApplication.screens():
            if screen.geometry().contains(center):
                break
            if screen.geometry().contains(pointer_pos):
                break
        else:
            raise RuntimeError('Could not get screen!?')

        geometry.moveCenter(screen.geometry().center())
        self.setGeometry(geometry)

    def showEvent(self, event):
        if self._initial_draw_finished:
            return super().showEvent(event)

        self._restore_ui()


def show():
    app = QtWidgets.QApplication([])
    win = InstagifferUI()
    win.show()
    app.exec()


if __name__ == '__main__':
    show()
