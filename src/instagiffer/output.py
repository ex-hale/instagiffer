from dataclasses import dataclass


@dataclass
class IGOutput:
    width: int = 480
    height: int = 360
    fps: float = 10.0
    colors: int = 256
    optimize: bool = True
    loop: int = 0
    format: str = 'gif'
