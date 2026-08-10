from dataclasses import dataclass
from enum import Enum

from PIL import Image, ImageDraw, ImageFont

TYPE = 'text'


class HAlign(Enum):
    """Horizontal Alignments."""

    none = 'none'
    left = 'left'
    right = 'right'
    center = 'center'


class VAlign(Enum):
    """Vertical Alignments."""

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
            (x, y),
            self.text,
            font=font,
            fill=self.color,
            stroke_width=stroke,
            stroke_fill=self.outline_color or None,
        )
        return frame


def from_dict(d: dict) -> TextLayer:
    d['align_horizontal'] = HAlign(d['align_horizontal'])
    d['align_vertical'] = VAlign(d['align_vertical'])
    d['position'] = tuple(d['position'])
    d['margins'] = tuple(d['margins'])
    return TextLayer(**d)
