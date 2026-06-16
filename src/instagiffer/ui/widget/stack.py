from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6 import QtCore, QtWidgets


class IgfStack(QtWidgets.QScrollArea):
    def __init__(self, parent):
        super().__init__(parent)
        self.contents = QtWidgets.QWidget(self)
        self.v_layout = QtWidgets.QVBoxLayout(self.contents)
        self.setMinimumWidth(150)
        self.setMaximumWidth(250)
