from dataclasses import dataclass
from enum import Enum

from PIL import Image, ImageDraw, ImageFont

from instagiffer.render import RenderContext

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

    def draw(self, render_context: RenderContext) -> list[Image.Image]:
        blank = render_context.output.get_blank()
        if not self.text:
            return [f.image or blank for f in render_context.frames]

        images: list[Image.Image] = []
        for frame in render_context.frames:
            image = blank if frame.image is None else frame.image.copy()
            image_draw = ImageDraw.Draw(image)
            stroke = self.outline_size if self.outline_color else 0
            font = self._get_font()
            x, y = self._get_x_y(font, stroke, image, image_draw)
            image_draw.text(
                (x, y),
                self.text,
                font=font,
                fill=self.color,
                stroke_width=stroke,
                stroke_fill=self.outline_color or None,
            )
            images.append(image)
        return images

    def _get_font(self) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
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
        return font

    def _get_x_y(
        self,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        stroke: int,
        image: Image.Image,
        image_draw: ImageDraw.ImageDraw,
    ) -> tuple[int, int]:
        bbox = image_draw.textbbox((0, 0), self.text, font=font, stroke_width=stroke)
        tw, th = int(bbox[2] - bbox[0]), int(bbox[3] - bbox[1])
        w, h = image.size
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
        return x, y


def from_dict(d: dict) -> TextLayer:
    d['align_horizontal'] = HAlign(d['align_horizontal'])
    d['align_vertical'] = VAlign(d['align_vertical'])
    d['position'] = tuple(d['position'])
    d['margins'] = tuple(d['margins'])
    return TextLayer(**d)


def to_dict(layer: TextLayer):
    pass
