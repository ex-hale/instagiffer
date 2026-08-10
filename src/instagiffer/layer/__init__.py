import dataclasses

from instagiffer.layer import source, text

SourceLayer = source.SourceLayer
TextLayer = text.TextLayer

type IGLayer = SourceLayer | TextLayer


_LAYER_MAP = {
    text.TYPE: text.from_dict,
    source.TYPE: source.from_dict,
}


def from_dicts(data: list[dict]) -> list[IGLayer]:
    """Create list of IGLayer objects from serialized data."""
    layer_objects = []
    for layer_data in data:
        d = layer_data.copy()
        try:
            layer_objects.append(_LAYER_MAP[d.pop('type')](d))
        except KeyError as error:
            raise KeyError(f'Unknown layer type! {error}') from error
    return layer_objects


def to_dicts(layers: list[IGLayer]) -> list[dict]:
    """Serialize layer objects to dictionaries."""
    dicts = []
    for layer in layers:
        d = dataclasses.asdict(layer)
        if isinstance(layer, TextLayer):
            d['align_horizontal'] = layer.align_horizontal.value
            d['align_vertical'] = layer.align_vertical.value
            d['type'] = 'text'
        else:
            d['fit'] = layer.fit.value
            d['type'] = 'source'
        dicts.append(d)
    return dicts
