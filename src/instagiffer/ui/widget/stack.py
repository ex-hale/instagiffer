from __future__ import annotations

import dataclasses
from enum import Enum

from PySide6 import QtCore, QtGui, QtWidgets

from instagiffer.project import IGLayer, SourceLayer
from instagiffer.ui.widget.a2slider import A2Slider
from instagiffer.ui.widget.path import FileRow

LABEL_FONT = QtGui.QFont()
LABEL_FONT.setPointSize(14)


class IgfStack(QtWidgets.QScrollArea):
    add_source_requested = QtCore.Signal()
    add_text_requested = QtCore.Signal()
    layer_selected = QtCore.Signal(SourceLayer)

    def __init__(self, parent):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.contents = QtWidgets.QWidget()
        self.v_layout = QtWidgets.QVBoxLayout(self.contents)
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        self._layer_widgets: list[QtWidgets.QWidget] = []
        self.setWidget(self.contents)

    def draw(self, layers: list[IGLayer]) -> None:
        for widget in reversed(self._layer_widgets):
            widget.deleteLater()
            self._layer_widgets.remove(widget)

        for layer in reversed(layers):
            widget = make_widget(layer, self)
            self._layer_widgets.append(widget)
            self.v_layout.addWidget(widget)
        self._spacer = QtWidgets.QSpacerItem(
            500,
            0,
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.v_layout.addSpacerItem(self._spacer)

    def add_source(self) -> None:
        self.add_source_requested.emit()

    def add_text(self) -> None:
        self.add_text_requested.emit()

    def list_layers(self, layers: list):
        pass


def make_widget(layer: IGLayer, parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    widget = QtWidgets.QWidget(parent)
    layout = QtWidgets.QFormLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    label = QtWidgets.QLabel(layer.__class__.__name__)
    label.setFont(LABEL_FONT)
    layout.addRow(label, QtWidgets.QWidget())
    for key, value in dataclasses.asdict(layer).items():
        if isinstance(value, str):
            sub_widget = FileRow() if key.lower() == 'path' else QtWidgets.QLineEdit(value, widget)
        elif isinstance(value, float):
            sub_widget = A2Slider(widget, value=value)
        elif isinstance(value, int):
            sub_widget = A2Slider(widget, value=value, decimals=0)
        elif isinstance(value, Enum):
            sub_widget = QtWidgets.QComboBox(widget)
            sub_widget.addItems([v.name.title() for v in value.__class__])
            sub_widget.setCurrentText(value.name.title())
        elif isinstance(value, tuple):
            if all(isinstance(x, int) for x in value):
                sub_widget = QtWidgets.QWidget(widget)
                sub_layout = QtWidgets.QHBoxLayout(sub_widget)
                sub_layout.setContentsMargins(0, 0, 0, 0)
                for x in value:
                    x_widget = QtWidgets.QDoubleSpinBox(widget)
                    sub_layout.addWidget(x_widget)
                    x_widget.setValue(x)
        #     else:
        #         value
        # else:
        #     value

        layout.addRow(key.title(), sub_widget)

    return widget
