import sys
from collections.abc import Callable
from dataclasses import dataclass

from PIL import Image

from instagiffer.ffmpeg import FFmWrap


@dataclass
class IGOutput:
    width: int = 480
    height: int = 360
    fps: int | float = 10.0
    colors: int = 256
    optimize: bool = True
    loop: int = 0
    format: str = 'gif'
    length: int | float = 3.0

    def get_blank(self) -> Image.Image:
        return Image.new('RGB', (self.width, self.height), (0, 0, 0))


@dataclass
class IGLayer:
    name: str = ''
    """User settable display name of the Layer."""
    type: str = ''
    """Type name of the Layer."""

    def __post_init__(self) -> None:
        self.name = self.__class__.__name__
        self.type = sys.modules[self.__class__.__module__].TYPE

    def draw(self, render_context: RenderContext) -> list[Image.Image]: ...


@dataclass
class Frame:
    n: int
    """Frame number. Starts at 0."""
    length: float
    """Frame duration in seconds."""
    start: float
    """Frame start time in seconds."""
    end: float
    """Frame end time in seconds."""
    image: Image.Image | None = None
    """Frame contents."""
    source_frame: int | None = None
    """Source frame index to sample (handles hold frames, slow-mo etc)"""


@dataclass
class RenderContext:
    frames: list[Frame]
    output: IGOutput
    ffmpeg: FFmWrap
    progress_callback: Callable[[float], None] | None = None

    def update_images(self, images: list[Image.Image]) -> None:
        assert len(images) == len(self.frames), (
            'Number of images to update has to match number of frames!'
        )
        for frame, image in zip(self.frames, images, strict=True):
            frame.image = image

    def get_images(self) -> list[Image.Image]:
        assert not any(f.image is None for f in self.frames)
        return [f.image for f in self.frames if f.image is not None]
