from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from instagiffer.project import IGLayer, SourceLayer, TextLayer


class IgfStack(QtWidgets.QScrollArea):
    add_source_requested = QtCore.Signal()
    add_text_requested = QtCore.Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.contents = QtWidgets.QWidget(self)
        self.v_layout = QtWidgets.QVBoxLayout(self.contents)

    def add_source(self) -> None:
        self.add_source_requested.emit()

    def add_text(self) -> None:
        self.add_text_requested.emit()

    def list_layers(self, layers: list):
        pass
