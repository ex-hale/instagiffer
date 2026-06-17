import pytest
from PIL import Image

from instagiffer.project import (
    Fit,
    HAlign,
    IGOutput,
    IGProject,
    SourceLayer,
    TextLayer,
    VAlign,
    _fit_frame,
)


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A fully configured project whose save directory is redirected to tmp_path."""
    import instagiffer.project as proj_mod

    monkeypatch.setattr(proj_mod, 'PROJECTS_DIR', tmp_path)

    p = IGProject.new()
    p.output = IGOutput(width=320, height=240, fps=12.0, colors=128, loop=1, format='mp4')

    p.add_source('/some/local/clip.mp4', fps=12.0, start_time=1.5, duration=4.0, scale=0.5, fit=Fit.contain)
    p.add_text(
        'Test caption',
        font='Arial.ttf',
        size=36,
        color='#ff0000',
        outline_color='#0000ff',
        outline_size=3,
        position=(10, 20),
        align_horizontal=HAlign.right,
        align_vertical=VAlign.top,
        margins=(5, 10, 15, 20),
    )
    return p


def test_save_creates_file(project):
    project.save()
    assert (project.project_dir / 'project.json').is_file()


def test_roundtrip_output(project):
    project.save()
    loaded = IGProject.load(project.project_id)

    assert loaded.output.width == project.output.width
    assert loaded.output.height == project.output.height
    assert loaded.output.fps == project.output.fps
    assert loaded.output.colors == project.output.colors
    assert loaded.output.loop == project.output.loop
    assert loaded.output.format == project.output.format


def test_roundtrip_layer_count(project):
    project.save()
    loaded = IGProject.load(project.project_id)
    assert len(loaded.layers) == len(project.layers)


def test_roundtrip_source_layer(project):
    project.save()
    loaded = IGProject.load(project.project_id)

    orig = project.layers[0]
    back = loaded.layers[0]
    assert isinstance(back, SourceLayer)
    assert back.path == orig.path
    assert back.fps == orig.fps
    assert back.start_time == orig.start_time
    assert back.duration == orig.duration
    assert back.scale == orig.scale
    assert back.fit == orig.fit


def test_roundtrip_text_layer(project):
    project.save()
    loaded = IGProject.load(project.project_id)

    orig = project.layers[1]
    back = loaded.layers[1]
    assert isinstance(back, TextLayer)
    assert back.text == orig.text
    assert back.font == orig.font
    assert back.size == orig.size
    assert back.color == orig.color
    assert back.outline_color == orig.outline_color
    assert back.outline_size == orig.outline_size
    assert back.position == orig.position
    assert back.align_horizontal == orig.align_horizontal
    assert back.align_vertical == orig.align_vertical
    assert back.margins == orig.margins


def test_load_missing_raises(tmp_path, monkeypatch):
    import instagiffer.project as proj_mod

    monkeypatch.setattr(proj_mod, 'PROJECTS_DIR', tmp_path)
    with pytest.raises(FileNotFoundError):
        IGProject.load('nonexistent-id')


def _solid(w: int, h: int, color: tuple[int, int, int] = (200, 100, 50)) -> Image.Image:
    img = Image.new('RGB', (w, h), color)
    return img


def test_fit_crop_output_size():
    # 16:9 source → 4:3 target: crop mode must produce exactly the target size
    img = _solid(160, 90)
    out = _fit_frame(img, (120, 90), Fit.crop)
    assert out.size == (120, 90)


def test_fit_crop_no_black_bars():
    # crop mode fills the frame — no black pixels from padding
    img = _solid(160, 90, color=(200, 100, 50))
    out = _fit_frame(img, (120, 90), Fit.crop)
    pixels = list(out.get_flattened_data())
    assert all(p != (0, 0, 0) for p in pixels)


def test_fit_contain_output_size():
    # contain mode must also produce exactly the target size
    img = _solid(160, 90)
    out = _fit_frame(img, (120, 90), Fit.contain)
    assert out.size == (120, 90)


def test_fit_contain_has_black_bars():
    # 16:9 source into 4:3 target → letterbox bars on top and bottom
    img = _solid(160, 90, color=(200, 100, 50))
    out = _fit_frame(img, (120, 90), Fit.contain)
    # Top-left corner pixel must be black padding
    assert out.getpixel((0, 0)) == (0, 0, 0)


def test_fit_crop_uniform_scale():
    # A uniform-color source must stay that color after crop (no interpolation artifacts at edges)
    img = _solid(320, 180, color=(128, 64, 32))
    out = _fit_frame(img, (240, 180), Fit.crop)
    center = out.getpixel((120, 90))
    assert center == (128, 64, 32)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
