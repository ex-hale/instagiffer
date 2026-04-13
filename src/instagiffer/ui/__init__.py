from PySide6 import QtGui, QtWidgets

import instagiffer
import instagiffer.common


class InstagifferUI(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f'Instagiffer - {instagiffer.__version__}')
        self.setWindowIcon(QtGui.QIcon(str(instagiffer.common.ASSETS_PATH / 'instagiffer.ico')))


def show():
    app = QtWidgets.QApplication([])
    win = InstagifferUI()
    win.show()
    app.exec()


if __name__ == '__main__':
    show()
