from __future__ import annotations

import hashlib
import json
import sys
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol

from PIL import Image, ImageDraw, ImageFont

from instagiffer.common import DOWNLOADS_DIR, FRAMES_CACHE_DIR, PROJECTS_DIR
from instagiffer.ffmpeg import FFmWrap

if sys.version_info < (3, 14):  # noqa: UP036
    import os
    import time

    def uuid7() -> uuid.UUID:
        timestamp_ms = int(time.time() * 1000)
        ts_bits = timestamp_ms & 0xFFFFFFFFFFFF
        rand_a = int.from_bytes(os.urandom(2)) & 0x0FFF
        rand_b = int.from_bytes(os.urandom(8)) & 0x3FFFFFFFFFFFFFFF
        int_val = (ts_bits << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
        return uuid.UUID(int=int_val)
else:
    uuid7 = uuid.uuid7


@dataclass
class IGOutput:
    width: int = 480
    height: int = 360
    fps: float = 10.0
    colors: int = 256
    optimize: bool = True
    loop: int = 0
    format: str = 'gif'


@dataclass
class SourceLayer:
    """Video or image source. trim, crop, speed etc. will live here later."""

    path: str = ''
    fps: float = 10.0
    start_time: float = 0.0
    duration: float = 5.0
    scale: float = 1.0

    @property
    def is_remote(self) -> bool:
        return self.path.startswith(('http://', 'https://'))

    def frames_cache_key(self) -> str:
        key = f'{self.path}|{self.fps}|{self.start_time}|{self.duration}|{self.scale}'
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def frames_dir(self) -> Path:
        return FRAMES_CACHE_DIR / self.frames_cache_key()

    def local_source_path(self) -> Path:
        """Local path to the source file. Remote sources are expected to be downloaded here first."""
        if self.is_remote:
            url_hash = hashlib.sha256(self.path.encode()).hexdigest()[:16]
            stem = self.path.rstrip('/').rsplit('/', 1)[-1] or 'source'
            return DOWNLOADS_DIR / url_hash / stem
        return Path(self.path)

    def frames_are_cached(self) -> bool:
        d = self.frames_dir()
        return d.is_dir() and any(d.glob('image*.png'))

    def get_frames(
        self,
        output: IGOutput,
        ffmpeg: FFmWrap | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ) -> list[Image.Image]:
        if not self.frames_are_cached():
            (ffmpeg or FFmWrap()).extract_frames(
                self.local_source_path(),
                self.frames_dir(),
                fps=self.fps,
                start_time=self.start_time,
                duration=self.duration,
                scale=self.scale,
                progress_callback=progress_callback,
            )
        size = (output.width, output.height)
        frames = []
        for p in sorted(self.frames_dir().glob('image*.png')):
            img = Image.open(p).convert('RGB')
            if img.size != size:
                img = img.resize(size, Image.Resampling.LANCZOS)
            frames.append(img)
        return frames


class HAlign(Enum):
    none = 'none'
    left = 'left'
    right = 'right'
    center = 'center'


class VAlign(Enum):
    none = 'none'
    top = 'top'
    bottom = 'bottom'
    center = 'center'


@dataclass
class TextLayer:
    """Overlay text. timing, animation etc. later."""

    text: str = ''
    font: str = ''
    size: int = 24
    color: str = '#ffffff'
    outline_color: str = '#000000'
    outline_size: int = 2
    position: tuple[int, int] = (0, 0)
    align_horizontal: HAlign = HAlign.center
    align_vertical: VAlign = VAlign.bottom
    margins: tuple[int, int, int, int] = (20, 20, 20, 20)

    def draw(self, frame: Image.Image) -> Image.Image:
        if not self.text:
            return frame

        frame = frame.copy()
        d = ImageDraw.Draw(frame)

        font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None
        if self.font:
            try:
                font = ImageFont.truetype(self.font, self.size)
            except OSError:
                pass
        if font is None:
            try:
                font = ImageFont.load_default(size=self.size)
            except TypeError:
                font = ImageFont.load_default()

        stroke = self.outline_size if self.outline_color else 0
        bbox = d.textbbox((0, 0), self.text, font=font, stroke_width=stroke)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        w, h = frame.size
        ml, mt, mr, mb = self.margins

        if self.align_horizontal == HAlign.left:
            x = ml
        elif self.align_horizontal == HAlign.right:
            x = w - tw - mr
        elif self.align_horizontal == HAlign.center:
            x = (w - tw) // 2
        else:
            x = self.position[0]

        if self.align_vertical == VAlign.top:
            y = mt
        elif self.align_vertical == VAlign.bottom:
            y = h - th - mb
        elif self.align_vertical == VAlign.center:
            y = (h - th) // 2
        else:
            y = self.position[1]

        d.text(
            (x, y), self.text, font=font, fill=self.color,
            stroke_width=stroke, stroke_fill=self.outline_color or None,
        )
        return frame


type Layer = SourceLayer | TextLayer


class Encoder(Protocol):
    def save(self, frames: list[Image.Image], output: IGOutput, path: Path) -> Path: ...


class PilGifEncoder:
    def save(self, frames: list[Image.Image], output: IGOutput, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        duration_ms = int(1000 / output.fps)
        quantized = [f.quantize(colors=output.colors, method=Image.Quantize.MEDIANCUT) for f in frames]
        quantized[0].save(
            path,
            format='GIF',
            save_all=True,
            append_images=quantized[1:],
            loop=output.loop,
            duration=duration_ms,
            optimize=output.optimize,
        )
        return path


class FfmpegMp4Encoder:
    def __init__(self, ffmpeg: FFmWrap | None = None) -> None:
        self._ff = ffmpeg or FFmWrap()

    def save(self, frames: list[Image.Image], output: IGOutput, path: Path) -> Path:
        return self._ff.encode_mp4(frames, output.width, output.height, output.fps, path)


def _layer_to_dict(layer: Layer) -> dict:
    d = asdict(layer)
    if isinstance(layer, TextLayer):
        d['align_horizontal'] = layer.align_horizontal.value
        d['align_vertical'] = layer.align_vertical.value
        d['type'] = 'text'
    else:
        d['type'] = 'source'
    return d


def _layer_from_dict(d: dict) -> Layer:
    d = d.copy()
    layer_type = d.pop('type')
    if layer_type == 'source':
        return SourceLayer(**d)
    if layer_type == 'text':
        d['align_horizontal'] = HAlign(d['align_horizontal'])
        d['align_vertical'] = VAlign(d['align_vertical'])
        d['position'] = tuple(d['position'])
        d['margins'] = tuple(d['margins'])
        return TextLayer(**d)
    raise ValueError(f'Unknown layer type: {layer_type!r}')


class IGProject:
    def __init__(self, project_id: str):
        if not isinstance(project_id, str):
            raise RuntimeError(f'Need string for {self.__class__.__name__} id!')
        self.project_id = project_id
        self.layers: list[Layer] = []
        self.output: IGOutput = IGOutput()

    @property
    def project_dir(self) -> Path:
        return PROJECTS_DIR / self.project_id

    @classmethod
    def new(cls) -> IGProject:
        """Create new empty project."""
        return cls(project_id=str(uuid7()))

    @classmethod
    def load(cls, project_id: str) -> IGProject:
        """Load project from stored data in instagiffer data dir."""
        project = cls(project_id=project_id)
        project_file = project.project_dir / 'project.json'
        if not project_file.is_file():
            raise FileNotFoundError(f'Project not found: {project_file}')
        with open(project_file, encoding='utf-8') as f:
            data = json.load(f)
        project.output = IGOutput(**data['output'])
        project.layers = [_layer_from_dict(layer) for layer in data['layers']]
        return project

    def save(self):
        """Save project to stored data in instagiffer data dir."""
        self.project_dir.mkdir(parents=True, exist_ok=True)
        data = {
            'project_id': self.project_id,
            'output': asdict(self.output),
            'layers': [_layer_to_dict(layer) for layer in self.layers],
        }
        with open(self.project_dir / 'project.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def add_source(self, path: str, **kwargs) -> SourceLayer:
        layer = SourceLayer(path=path, **kwargs)
        self.layers.append(layer)
        return layer

    def add_text(self, text: str, **kwargs) -> TextLayer:
        layer = TextLayer(text=text, **kwargs)
        self.layers.append(layer)
        return layer

    def composite_frames(
        self,
        ffmpeg: FFmWrap | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ) -> list[Image.Image]:
        """Return composited PIL frames without writing any file.
        * first source layer provides the base
        * multi-source compositing comes later
        """
        frames: list[Image.Image] = []
        for layer in self.layers:
            if isinstance(layer, SourceLayer):
                frames = layer.get_frames(self.output, ffmpeg=ffmpeg, progress_callback=progress_callback)
                break
        for layer in self.layers:
            if isinstance(layer, TextLayer):
                frames = [layer.draw(f) for f in frames]
        return frames

    def render(
        self,
        output_path: Path | str,
        encoder: Encoder | None = None,
        ffmpeg: FFmWrap | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ) -> Path:
        frames = self.composite_frames(ffmpeg=ffmpeg, progress_callback=progress_callback)
        return (encoder or PilGifEncoder()).save(frames, self.output, Path(output_path))

    def __repr__(self) -> str:
        return f'IGProject(id={self.project_id!r}, layers={len(self.layers)}, output={self.output!r})'


if __name__ == '__main__':
    from instagiffer.common import PROJECT_ROOT

    src: Path = PROJECT_ROOT / 'test' / 'data' / '288c39d6521eb8f1.mp4'
    out: Path = PROJECT_ROOT / 'test' / 'data' / 'out.gif'

    p: IGProject = IGProject.new()
    p.output = IGOutput(width=480, height=270, fps=10.0)
    p.add_source(str(src), fps=10.0, start_time=0.0, duration=3.0)
    p.add_text('Hello World', color='#ffff00', size=32)
    p.save()

    result = p.render(out, progress_callback=lambda pct: print(f'\r{pct:.0%}', end='', flush=True))
    print(f'\nRendered: {result}')
