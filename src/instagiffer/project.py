from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from PIL import Image

import instagiffer.layer
from instagiffer.common import DEFAULTS_DIR, PROJECTS_DIR, USER_DEFAULTS_DIR
from instagiffer.compat import uuid7
from instagiffer.ffmpeg import FFmWrap
from instagiffer.layer import IGLayer, SourceLayer, TextLayer
from instagiffer.render import Frame, IGOutput, RenderContext

_TEMPLATE = '_template'
TEMPLATE_PATTERN = '{}.json'
PROJECT_FILE_NAME = TEMPLATE_PATTERN.format('project')
PROJECT_ID = 'project_id'


class Encoder(Protocol):
    def save(self, render_context: RenderContext, path: str | Path) -> Path: ...


class NoSuchEncoder(Exception):
    pass


class PilGifEncoder:
    def save(self, render_context: RenderContext, path: str | Path) -> Path:
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
    def save(self, render_context: RenderContext, path: str | Path) -> Path:
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
    def new(cls) -> IGProject:
        """Create new empty project."""
        return cls(project_id=str(uuid7()))

    @classmethod
    def load(cls, identifier: str | Path) -> IGProject:
        """Load project from path or stored data in instagiffer data dir."""
        if isinstance(identifier, str) and (PROJECTS_DIR / identifier).is_dir():
            project = cls(project_id=identifier)
            project_file = project.project_dir / PROJECT_FILE_NAME
        else:
            project = cls.new()
            project_file = Path(identifier)

        if not project_file.is_file():
            raise FileNotFoundError(f'Project not found: {project_file}')

        return project.load_data(json.loads(project_file.read_bytes()))

    def load_data(self, data: dict) -> IGProject:
        self.output = IGOutput(**data['output'])
        self.layers = instagiffer.layer.from_dicts(data['layers'])
        return self

    def save(self):
        """Save project to stored data in instagiffer data dir."""
        self.project_dir.mkdir(parents=True, exist_ok=True)
        data = {
            'output': asdict(self.output),
            'layers': instagiffer.layer.to_dicts(self.layers),
        }
        with open(self.project_dir / PROJECT_FILE_NAME, 'w', encoding='utf-8') as f:
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
            encoder: type[Encoder] = ENCODERS[self.output.format]
        except KeyError:
            raise NoSuchEncoder(f'No encoder "{self.output.format}"!') from KeyError

        if render_context is None:
            render_context = self.get_default_render_context(progress_callback)

        render_context.update_images(self.composite_frames(render_context))
        return encoder().save(render_context, output_path)

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


def get_default() -> IGProject:
    """Get default project object from built-in or user defined defaults.

    For EACH of the output and layer parts in a project:
    Always look for USER defaults first, then for builtin defaults.
    If a "_template" key is present, try loading from that template.
    """
    project_file = USER_DEFAULTS_DIR / PROJECT_FILE_NAME
    if not project_file.is_file():
        project_file = DEFAULTS_DIR / PROJECT_FILE_NAME
    if project_file.is_file():
        data = json.loads(project_file.read_bytes())
    if PROJECT_ID not in data:
        data[PROJECT_ID] = str(uuid7())

    data['output'] = _check_default_component(data.get('output'), 'output')
    data['layers'] = _check_default_component(data.get('layers'), 'layers')
    if not isinstance(data['layers'], list):
        data['layers'] = []
    for i, layer_data in enumerate(data['layers']):
        data['layers'][i] = _check_default_component(layer_data)

    project = IGProject.new()
    project.load_data(data)
    return project


def _check_default_component(container: dict | None, name: str | None = None) -> dict:
    """Resolve found `_template` trying absolute path first, then
    relative to `USER_DEFAULTS_DIR`, or `DEFAULTS_DIR`.
    """
    # Early exit if the component is already done.
    if container is not None and _TEMPLATE not in container and container:
        return container

    if container is None:
        container = {}

    template_name: str = ''
    if _TEMPLATE in container:
        template_name = container.pop(_TEMPLATE)
    if not template_name and name is not None:
        template_name = TEMPLATE_PATTERN.format(name)

    template_path = Path(template_name)
    if not template_path.is_file():
        template_path = USER_DEFAULTS_DIR / template_name
    if not template_path.is_file():
        template_path = DEFAULTS_DIR / template_name

    if template_path.is_file():
        container.update(json.loads(template_path.read_bytes()))

    return container


if __name__ == '__main__':
    from instagiffer.common import PROJECT_DIR

    test_data: Path = PROJECT_DIR / 'test' / 'data'
    src: Path = test_data / '288c39d6521eb8f1.mp4'
    out: Path = test_data / 'temp' / 'out2'

    p: IGProject = IGProject.new()
    p.output = IGOutput(width=480, height=270, fps=10.0, format='mp4')
    p.add_source(src, fps=3.0, start_time=0.0, duration=3.0)
    p.add_text('Hello, Linda!', color='#ff8080', size=42, font='comic', outline_size=6)
    p.save()

    result = p.render(out, progress_callback=lambda pct: print(f'\r{pct:.0%}', end='', flush=True))
    print(f'\nRendered: {result}')
