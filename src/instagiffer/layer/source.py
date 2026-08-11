"""
The Instagiffer SouceLayer is has a video file as source for the resulting PIL Images.
"""

import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PIL import Image

from instagiffer.common import DOWNLOADS_DIR, FRAMES_CACHE_DIR
from instagiffer.ffmpeg import FRAME_GLOB
from instagiffer.render import RenderContext

TYPE = 'source'


class Fit(Enum):
    """Image fitting options enum: `crop` or `contain`."""

    crop = 'crop'
    """Scale to fill, crop excess — never distorts, may lose edges."""
    contain = 'contain'
    """Scale to fit, pad with black bars — never crops, may add bars."""


@dataclass
class SourceLayer:
    """Video or image source. trim, crop, speed etc. will live here later."""

    path: str = ''
    fps: float = 10.0
    start_time: float = 0.0
    duration: float = 5.0
    scale: float = 1.0
    fit: Fit = Fit.crop
    """Image fitting options enum: `crop` or `contain`."""

    def draw(self, render_context: RenderContext) -> list[Image.Image]:
        if not self.frames_are_cached():
            render_context.ffmpeg.extract_frames(
                self.local_source_path(),
                self.frames_dir(),
                fps=self.fps,
                start_time=self.start_time,
                duration=self.duration,
                scale=self.scale,
                progress_callback=render_context.progress_callback,
            )
        size = (render_context.output.width, render_context.output.height)
        images = []
        paths = sorted(self.frames_dir().glob(FRAME_GLOB))
        for i, frame in enumerate(render_context.frames):
            img = Image.open(paths[frame.source_frame or i]).convert('RGB')
            if img.size != size:
                img = fit_frame(img, size, self.fit)
            images.append(img)
        return images

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
        return d.is_dir() and any(d.glob(FRAME_GLOB))


def fit_frame(img: Image.Image, size: tuple[int, int], fit: Fit) -> Image.Image:
    tw, th = size
    sw, sh = img.size
    if fit == Fit.crop:
        scale = max(tw / sw, th / sh)
        img = img.resize((round(sw * scale), round(sh * scale)), Image.Resampling.LANCZOS)
        left = (img.width - tw) // 2
        top = (img.height - th) // 2
        return img.crop((left, top, left + tw, top + th))
    # Fit.contain: scale to fit, pad remainder with black
    scale = min(tw / sw, th / sh)
    img = img.resize((round(sw * scale), round(sh * scale)), Image.Resampling.LANCZOS)
    result = Image.new('RGB', size, (0, 0, 0))
    result.paste(img, ((tw - img.width) // 2, (th - img.height) // 2))
    return result


def from_dict(d: dict) -> SourceLayer:
    d['fit'] = Fit(d['fit'])
    return SourceLayer(**d)
