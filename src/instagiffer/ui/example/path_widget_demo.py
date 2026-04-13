from PySide6 import QtWidgets

from instagiffer.ui.widget.path import DirRow, FileRow


class PathWidgetDemo(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('Path Widget Demo')
        self.setMinimumWidth(600)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(FileRow('Executable', 'Pick any file...'))
        layout.addWidget(
            FileRow(
                'Video file',
                'Pick a video...',
                file_filter='Videos (*.mp4 *.mkv *.avi *.mov *.webm);;All files (*)',
            )
        )
        layout.addWidget(DirRow('Output folder', 'Pick a directory...'))
        layout.addStretch()


def main() -> None:
    app = QtWidgets.QApplication([])
    win = PathWidgetDemo()
    win.show()
    app.exec()


if __name__ == '__main__':
    main()
