"""
Root module for all Instagiffer Layers.

Each Layer has a `draw` function that accepts a `RenderContext` and
returns a new list of PIL Images.
"""

import dataclasses
import sys
from enum import Enum

from instagiffer.layer import source, text

SourceLayer = source.SourceLayer
TextLayer = text.TextLayer

type IGLayer = SourceLayer | TextLayer

ALL: tuple[str, ...] = text.TYPE, source.TYPE


def from_dicts(data: list[dict]) -> list[IGLayer]:
    """Create list of IGLayer objects from serialized data."""
    layer_objects = []
    for layer_data in data:
        d = layer_data.copy()
        try:
            typ = d.pop('type')
        except KeyError as error:
            raise KeyError(
                f'Could not get type from layer data!\n {error = }\n data = {d}'
            ) from error

        try:
            layer_objects.append(globals()[typ].from_dict(d))
        except (KeyError, AttributeError) as error:
            raise Exception(f'Error deserializing layer "{typ}"!\n {error = }') from error
    return layer_objects


def to_dicts(layers: list[IGLayer]) -> list[dict]:
    """Serialize layer objects to dictionaries."""
    dicts = []
    for layer in layers:
        data = dataclasses.asdict(layer)
        for key, value in data.items():
            if isinstance(value, Enum):
                data[key] = value.value
        data['type'] = sys.modules[layer.__class__.__module__].TYPE
        dicts.append(data)
    return dicts
