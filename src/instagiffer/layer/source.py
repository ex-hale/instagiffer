import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PIL import Image

from instagiffer.common import DOWNLOADS_DIR, FRAMES_CACHE_DIR
from instagiffer.ffmpeg import FFmWrap
from instagiffer.output import IGOutput

TYPE = 'source'


class Fit(Enum):
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
                img = fit_frame(img, size, self.fit)
            frames.append(img)
        return frames


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
