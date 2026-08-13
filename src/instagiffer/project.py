from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from PIL import Image

import instagiffer.layer
from instagiffer.common import PROJECTS_DIR
from instagiffer.compat import uuid7
from instagiffer.ffmpeg import FFmWrap
from instagiffer.layer import IGLayer, SourceLayer, TextLayer
from instagiffer.render import Frame, IGOutput, RenderContext

DEFAULT_DURATION = 3.0


class Encoder(Protocol):
    def save(self, render_context: RenderContext, path: Path) -> Path: ...


class NoSuchEncoder(Exception):
    pass


class PilGifEncoder:
    def save(self, render_context: RenderContext, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        duration_ms = int(1000 / render_context.output.fps)
        quantized = [
            image.quantize(colors=render_context.output.colors, method=Image.Quantize.MEDIANCUT)
            for image in render_context.get_images()
        ]
        quantized[0].save(
            path,
            format='GIF',
            save_all=True,
            append_images=quantized[1:],
            loop=render_context.output.loop,
            duration=duration_ms,
            optimize=render_context.output.optimize,
        )
        return path


class FfmpegMp4Encoder:
    def save(self, render_context: RenderContext, path: Path) -> Path:
        return render_context.ffmpeg.encode_mp4(
            frames=[f.image for f in render_context.frames],
            width=render_context.output.width,
            height=render_context.output.height,
            fps=render_context.output.fps,
            path=path,
        )


ENCODERS: dict[str, type[Encoder]] = {'gif': PilGifEncoder, 'mp4': FfmpegMp4Encoder}


class IGProject:
    def __init__(self, project_id: str, duration: int | float | None = None) -> None:
        if not isinstance(project_id, str):
            raise RuntimeError(f'Need string for {self.__class__.__name__} id!')
        self.name: str = ''
        """Display name of the project."""
        self.duration: int | float | None = None
        """Duration in seconds."""
        self.project_id: str = project_id
        """Internal identifier."""
        self.layers: list[IGLayer] = []
        """List of layers. First index `0` is bottom layer..."""
        self.output: IGOutput = IGOutput()
        """Output configuration with final dimensions and format settings."""
        self._ffmpeg: FFmWrap | None = None
        """FFmpeg wrapper instance to be reused."""
        self._render_context: RenderContext | None = None
        """Default render context to use the whole range of the project."""

    @property
    def project_dir(self) -> Path:
        """Path into this projects background data directory."""
        return PROJECTS_DIR / self.project_id

    @classmethod
    def new(cls, duration: int | float | None = None) -> IGProject:
        """Create new empty project."""
        if not duration:
            duration = DEFAULT_DURATION
        return cls(project_id=str(uuid7()), duration=duration)

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

    def add_source(self, path: str | Path, **kwargs) -> SourceLayer:
        string_path = path if isinstance(path, str) else str(path)
        layer = SourceLayer(string_path, **kwargs)
        self.layers.append(layer)
        return layer

    def add_text(self, text: str, **kwargs) -> TextLayer:
        layer = TextLayer(text=text, **kwargs)
        self.layers.append(layer)
        return layer

    def composite_frames(
        self,
        render_context: RenderContext | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ) -> list[Image.Image]:
        """
        Return composited PIL frames according to given or default render context.

        A default render context uses ALL frames of the project and its built-in
        ffmpeg wrapper and output objects.
        """
        if render_context is None:
            render_context = self.get_default_render_context(progress_callback)

        for layer in self.layers:
            images = layer.draw(render_context)
            render_context.update_images(images)
        return images

    def render(
        self,
        output_path: Path | str,
        render_context: RenderContext | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ) -> Path:
        try:
            encoder: Encoder = ENCODERS[self.output.format]
        except KeyError:
            raise NoSuchEncoder(f'No encoder "{self.output.format}"!') from KeyError

        if render_context is None:
            render_context = self.get_default_render_context(progress_callback)

        render_context.update_images(self.composite_frames(render_context))
        return encoder().save(render_context, Path(output_path))

    def __repr__(self) -> str:
        return (
            f'IGProject(id={self.project_id!r}, layers={len(self.layers)}, output={self.output!r})'
        )

    @property
    def ffmpeg(self) -> FFmWrap:
        if self._ffmpeg is not None:
            return self._ffmpeg

        self._ffmpeg = FFmWrap()
        return self._ffmpeg

    def get_default_render_context(
        self, progress_callback: Callable[[float], None] | None = None
    ) -> RenderContext:
        if self._render_context is not None:
            if progress_callback is not None:
                self._render_context.progress_callback = progress_callback
            return self._render_context

        frame_count = int(self.duration or DEFAULT_DURATION * self.output.fps)
        frame_length = 1.0 / self.output.fps
        frames = [
            Frame(n=i, length=frame_length, start=i * frame_length, end=(i + 1) * frame_length)
            for i in range(frame_count)
        ]
        self._render_context = RenderContext(frames=frames, output=self.output, ffmpeg=self.ffmpeg)
        if progress_callback is not None:
            self._render_context.progress_callback = progress_callback
        return self._render_context


if __name__ == '__main__':
    from instagiffer.common import PROJECT_ROOT

    test_data: Path = PROJECT_ROOT / 'test' / 'data'
    src: Path = test_data / '288c39d6521eb8f1.mp4'
    out: Path = test_data / 'temp' / 'out2'

    p: IGProject = IGProject.new()
    p.output = IGOutput(width=480, height=270, fps=10.0, format='mp4')
    p.add_source(src, fps=3.0, start_time=0.0, duration=3.0)
    p.add_text('Heeello, LindaaA!', color='#ff8080', size=42, font='comic', outline_size=6)
    p.save()

    result = p.render(out, progress_callback=lambda pct: print(f'\r{pct:.0%}', end='', flush=True))
    print(f'\nRendered: {result}')
