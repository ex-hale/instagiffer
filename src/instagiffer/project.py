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
import instagiffer.layer
from instagiffer.compat import uuid7
from instagiffer.ffmpeg import FFmWrap
from instagiffer.layer import Layer, SourceLayer, TextLayer
from instagiffer.output import IGOutput


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
        project.layers = instagiffer.layer.from_dicts(data['layers'])
        return project

    def save(self):
        """Save project to stored data in instagiffer data dir."""
        self.project_dir.mkdir(parents=True, exist_ok=True)
        data = {
            'project_id': self.project_id,
            'output': asdict(self.output),
            'layers': instagiffer.layer.to_dicts(self.layers),
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
