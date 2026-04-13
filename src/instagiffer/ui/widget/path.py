"""Path-picker row widgets."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6 import QtCore, QtWidgets


class _BasePathRow(QtWidgets.QWidget):
    """Shared base: label + line-edit + Browse button + Explore button."""

    path_changed = QtCore.Signal(Path)

    def __init__(
        self,
        label: str,
        placeholder: str = '',
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.label_widget = QtWidgets.QLabel(label)
        self.label_widget.setMinimumWidth(120)
        self.edit = QtWidgets.QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.textChanged.connect(lambda _: self.path_changed.emit(self.path))

        self.browse_btn = QtWidgets.QPushButton('Browse...')
        self.browse_btn.setFixedWidth(80)
        self.browse_btn.clicked.connect(self._on_browse)

        self.explore_btn = QtWidgets.QPushButton('Explore')
        self.explore_btn.setFixedWidth(64)
        self.explore_btn.setToolTip('Open in file manager')
        self.explore_btn.clicked.connect(self._on_explore)

        layout.addWidget(self.label_widget)
        layout.addWidget(self.edit)
        layout.addWidget(self.browse_btn)
        layout.addWidget(self.explore_btn)

    def _on_browse(self) -> None:
        raise NotImplementedError

    def _explore_target(self) -> Path:
        """Return the path that 'Explore' should open in the file manager."""
        raise NotImplementedError

    def _on_explore(self) -> None:
        target = self._explore_target()

        # Walk up to the nearest existing ancestor so Explore never silently fails
        while target != target.parent and not target.exists():
            target = target.parent

        if not target.exists():
            QtWidgets.QMessageBox.information(self, 'Explore', 'Path does not exist yet.')
            return

        target_str = str(target)
        if sys.platform == 'win32':
            subprocess.Popen(['explorer', target_str])
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', target_str])
        else:
            subprocess.Popen(['xdg-open', target_str])

    @property
    def path(self) -> Path:
        return Path(self.edit.text().strip())

    def set_path(self, path: Path) -> None:
        self.edit.setText(str(path))


class FileRow(_BasePathRow):
    """Path row for selecting a single file."""

    def __init__(
        self,
        label: str,
        placeholder: str = '',
        file_filter: str = 'All files (*)',
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(label, placeholder, parent)
        self._file_filter = file_filter

    def _on_browse(self) -> None:
        start_dir = str(self.path.parent) if self.path.parent.exists() else ''
        chosen, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Select file', start_dir, self._file_filter
        )
        if chosen:
            self.edit.setText(chosen)

    def _explore_target(self) -> Path:
        """Open the folder containing the selected file."""
        return self.path.parent


class DirRow(_BasePathRow):
    """Path row for selecting a directory."""

    def _on_browse(self) -> None:
        start_dir = str(self.path) if self.path.exists() else ''
        chosen = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select folder', start_dir)
        if chosen:
            self.edit.setText(chosen)

    def _explore_target(self) -> Path:
        """Open the directory itself."""
        return self.path


if __name__ == '__main__':
    from instagiffer.ui.example import path_widget_demo

    path_widget_demo.main()
