from PySide6 import QtCore, QtGui, QtWidgets

import instagiffer.common

# from instagiffer.config import Config, UiSettings
import instagiffer.project
from instagiffer.ui.widget.layer import LayerList, LayerPrefs
from instagiffer.ui.widget.timeline import TimeLine
from instagiffer.ui.widget.view import IgfView

DEFAULT_WIN_SIZE = (1000, 700)


class InstagifferUI(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._project = None
        self._initial_draw_finished = False

        self.setWindowTitle(f'Instagiffer - {instagiffer.__version__}')
        self.setWindowIcon(QtGui.QIcon(str(instagiffer.common.ASSETS_DIR / 'instagiffer.ico')))

        self._setup_ui()
        self._setup_project()

    def _setup_project(self):
        """Load up the a initial project. Might be from:
        * built-in default project
        * last open project (based on prefs)
        * from project file path given via commandline
        * user defined default
        """
        # TODO: if config.reopen_last: load last from recent stack
        self._project = instagiffer.project.get_default()
        self._init_project_ui()

    def _init_project_ui(self):
        """Cleanup ui and refill things with currently loaded project things."""
        if self._project is None:
            self.layer_list.set_layers(None)
            return

        self.layer_list.set_layers(self._project.layers)

    def _setup_ui(self):
        self.h_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.h_splitter.setChildrenCollapsible(False)
        self.setCentralWidget(self.h_splitter)

        self.v_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self.h_splitter.addWidget(self.v_splitter)
        self.layer_list = LayerList(self)

        self.layer_prefs = LayerPrefs(self)
        self.layer_list.layer_selected.connect(self.layer_prefs.draw)
        self.v_splitter.addWidget(self.layer_list)
        self.v_splitter.addWidget(self.layer_prefs)

        self.view_widget = QtWidgets.QWidget(self)
        self.view_layout = QtWidgets.QVBoxLayout(self.view_widget)
        self.h_splitter.addWidget(self.view_widget)

        self.view = IgfView(self)
        self.timeline = TimeLine(self)
        self.view_layout.addWidget(self.view)
        self.view_layout.addWidget(self.timeline)

    def _restore_ui(self):
        """WIP - Restore window position and size or initialize these if unset."""
        # if not hasattr(UiSettings, 'splitter_size'):
        self._init_window()

    def _init_window(self):
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

        self.h_splitter.setSizes([int(DEFAULT_WIN_SIZE[0] * .333), int(DEFAULT_WIN_SIZE[0] * .666)])
        self.v_splitter.setSizes([int(DEFAULT_WIN_SIZE[1] * .25), int(DEFAULT_WIN_SIZE[1] * .75)])

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
