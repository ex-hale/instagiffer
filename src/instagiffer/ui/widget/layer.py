from __future__ import annotations

import dataclasses
from enum import Enum

from PySide6 import QtCore, QtGui, QtWidgets

from instagiffer.project import IGLayer
from instagiffer.ui.widget.a2slider import A2Slider
from instagiffer.ui.widget.path import FileRow

LABEL_FONT = QtGui.QFont()
LABEL_FONT.setPointSize(14)
Qt = QtCore.Qt
_QIndex = QtCore.QModelIndex | QtCore.QPersistentModelIndex


class LayerList(QtWidgets.QWidget):
    layer_selected = QtCore.Signal(IGLayer)  # emits layer or None

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.model = _LayerListModel()

        self.list_view = QtWidgets.QListView(self)
        self.list_view.setModel(self.model)
        self.list_view.setEditTriggers(QtWidgets.QListView.EditTrigger.NoEditTriggers)
        self.list_view.setSelectionMode(QtWidgets.QListView.SelectionMode.SingleSelection)

        # splitter = QtWidgets.QSplitter(Qt.Orientation.Horizontal)
        # splitter.addWidget(self.list_view)
        # splitter.setStretchFactor(0, 1)
        # splitter.setStretchFactor(1, 2)
        # splitter.setSizes([220, 480])

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list_view)

        self.list_view.selectionModel().currentRowChanged.connect(self._on_current_changed)

        if self.model.rowCount() > 0:
            self.list_view.setCurrentIndex(self.model.index(0))

    def _on_current_changed(self, current: QtCore.QModelIndex, _previous: QtCore.QModelIndex):
        layer = self.model.data(current, Qt.ItemDataRole.UserRole) if current.isValid() else None
        self.layer_selected.emit(layer)

    def set_layers(self, layers: list[IGLayer]) -> None:
        """Call this whenever the underlying layer list changes."""
        current = self.current_layer()
        self.model.set_layers(layers)
        if current in layers:
            self.list_view.setCurrentIndex(self.model.index(layers.index(current)))
        elif layers:
            self.list_view.setCurrentIndex(self.model.index(0))

    def current_layer(self) -> IGLayer | None:
        idx = self.list_view.currentIndex()
        return self.model.data(idx, Qt.ItemDataRole.UserRole) if idx.isValid() else None


class LayerPrefs(QtWidgets.QScrollArea):
    add_source_requested = QtCore.Signal()
    add_text_requested = QtCore.Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.contents = QtWidgets.QWidget()
        self.v_layout = QtWidgets.QVBoxLayout(self.contents)
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        self._layer_widget: QtWidgets.QWidget | None = None
        self._spacer = QtWidgets.QSpacerItem(
            500,
            0,
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.v_layout.addSpacerItem(self._spacer)
        self.setWidget(self.contents)

    def draw(self, layer: IGLayer) -> None:
        if self._layer_widget is not None:
            self._layer_widget.deleteLater()
        self._layer_widget = make_widget(layer, self)
        self.v_layout.insertWidget(0, self._layer_widget)


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
                    if len(value) >= 2:
                        x_widget.setButtonSymbols(QtWidgets.QDoubleSpinBox.ButtonSymbols.NoButtons)
                    sub_layout.addWidget(x_widget)
                    x_widget.setValue(x)
                    x_widget.setMinimumWidth(20)
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError

        layout.addRow(key.title(), sub_widget)

    return widget


class _LayerListModel(QtCore.QAbstractListModel):
    def __init__(self, layers: list | None = None, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._layers: list[IGLayer] = list(layers or [])

    def rowCount(self, parent: _QIndex = QtCore.QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._layers)

    def data(self, index: _QIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._layers)):
            return None
        layer = self._layers[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            return f'{layer.name} ({layer.type})' if layer.name != layer.type else layer.name
        if role == Qt.ItemDataRole.UserRole:
            return layer
        return None

    def set_layers(self, layers: list) -> None:
        self.beginResetModel()
        self._layers = list(reversed(layers))
        self.endResetModel()

    def layer_at(self, row: int):
        return self._layers[row] if 0 <= row < len(self._layers) else None
