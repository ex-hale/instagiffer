from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from instagiffer.project import IGLayer, SourceLayer, TextLayer


class IgfStack(QtWidgets.QScrollArea):
    add_source_requested = QtCore.Signal(str)
    add_text_requested = QtCore.Signal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.contents = QtWidgets.QWidget(self)
        self.v_layout = QtWidgets.QVBoxLayout(self.contents)

    def add_source(self, url: str = '') -> None:
        self.add_source_requested.emit(url)

    def add_text(self, text: str = '') -> None:
        self.add_text_requested.emit(text)

    def list_layers(self, layers: list):
        pass
