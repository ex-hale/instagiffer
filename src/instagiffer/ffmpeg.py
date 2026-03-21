"""Thin wrapper for FFmpeg video info and frame extraction."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

# Output frame filename pattern - 1-indexed, zero-padded to 4 digits
FRAME_PATTERN = 'image%04d.png'
FRAME_GLOB = 'image*.png'


class FFmpegError(Exception):
    """Raised when ffmpeg encounters an error."""


class FFmpegNotFoundError(FFmpegError):
    """Raised when the ffmpeg executable cannot be located."""


@dataclass
class VideoInfo:
    """Metadata parsed from a video file via ``ffmpeg -i``."""

    width: int
    height: int
    duration_sec: float
    fps: float
    codec: str = ''

    @property
    def duration_ms(self) -> int:
        return int(self.duration_sec * 1000)

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height if self.height else 0.0


class FFmpegWrapper:
    """
    Thin wrapper around the ``ffmpeg`` executable.

    Usage::

        ffmpeg = FFmpegWrapper()                       # auto-locate in PATH
        ffmpeg = FFmpegWrapper(Path('/usr/bin/ffmpeg'))  # explicit path

        info = ffmpeg.get_video_info(Path('clip.mp4'))
        frames = ffmpeg.extract_frames(
            Path('clip.mp4'),
            output_dir=Path('/tmp/frames'),
            fps=15,
            start_time=2.5,
            duration=5.0,
            progress_callback=lambda p: print(f'{p:.0%}'),
        )
    """

    def __init__(self, ffmpeg_path: Path | None = None) -> None:
        if ffmpeg_path is not None:
            self.ffmpeg = Path(ffmpeg_path)
            if not self.ffmpeg.exists():
                raise FFmpegNotFoundError(f'ffmpeg not found at: {self.ffmpeg}')
        else:
            found = shutil.which('ffmpeg')
            if found is None:
                raise FFmpegNotFoundError(
                    'ffmpeg not found in PATH. Install ffmpeg and make sure it is on your PATH.'
                )
            self.ffmpeg = Path(found)

        log.debug('Using ffmpeg: %s', self.ffmpeg)

    def get_video_info(self, video_path: Path) -> VideoInfo:
        """
        Return :class:`VideoInfo` for *video_path*.

        Handles non-square pixels (SAR/DAR correction) and phone-video
        side-rotation (90°/270° → swap width and height).
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f'Video not found: {video_path}')

        # ffmpeg writes stream info to stderr even when it "fails" (exit 1 is normal)
        result = subprocess.run(
            [str(self.ffmpeg), '-i', str(video_path)],
            capture_output=True,
            text=True,
        )
        output = result.stderr

        width, height = _parse_resolution(output)
        duration_sec = _parse_duration(output)
        fps = _parse_fps(output)
        codec = _parse_codec(output)

        return VideoInfo(
            width=width, height=height, duration_sec=duration_sec, fps=fps, codec=codec
        )

    def extract_frames(
        self,
        video_path: Path,
        output_dir: Path,
        fps: float,
        start_time: float = 0.0,
        duration: float | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ) -> list[Path]:
        """
        Extract frames from *video_path* into *output_dir* as PNG files.

        The frames are named ``image0001.png``, ``image0002.png``, … and
        returned as a sorted list of :class:`~pathlib.Path` objects.

        Args:
            video_path:        Source video file.
            output_dir:        Destination directory (created if needed).
            fps:               Frames per second to extract.
            start_time:        Seek position in seconds before extraction.
            duration:          How many seconds to extract (``None`` = full clip).
            progress_callback: Optional callable receiving a float 0.0-1.0.

        Raises:
            FileNotFoundError: If *video_path* does not exist.
            FFmpegError:       If ffmpeg exits non-zero or no frames are produced.
        """
        video_path = Path(video_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if not video_path.exists():
            raise FileNotFoundError(f'Video not found: {video_path}')

        # Build command.
        # -ss before -i  →  fast keyframe seek (accurate enough for GIF use)
        # -stats          →  emit progress lines to stderr
        # -sn             →  skip subtitle streams
        cmd: list[str] = [str(self.ffmpeg), '-v', 'quiet', '-stats']

        if start_time > 0:
            cmd += ['-ss', f'{start_time:.3f}']
        if duration is not None:
            cmd += ['-t', f'{duration:.3f}']

        cmd += ['-i', str(video_path)]
        cmd += ['-r', str(fps), '-sn']
        cmd += [str(output_dir / FRAME_PATTERN)]

        log.debug('extract_frames cmd: %s', ' '.join(cmd))

        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True)
        assert process.stderr is not None

        for line in process.stderr:
            log.debug('ffmpeg: %s', line.rstrip())
            if progress_callback and duration:
                match = re.search(r'time=(\d+:\d+:\d+\.\d+)', line)
                if match:
                    elapsed = _duration_str_to_sec(match.group(1))
                    progress_callback(min(elapsed / duration, 1.0))

        process.wait()

        if process.returncode != 0:
            raise FFmpegError(
                f'ffmpeg exited with code {process.returncode}. Command: {" ".join(cmd)}'
            )

        frames = sorted(output_dir.glob(FRAME_GLOB))
        if not frames:
            raise FFmpegError(
                f'No frames were extracted from "{video_path.name}". '
                'Is it a supported video format?'
            )

        log.info('Extracted %d frames from "%s"', len(frames), video_path.name)

        if progress_callback:
            progress_callback(1.0)

        return frames


def _parse_resolution(ffmpeg_output: str) -> tuple[int, int]:
    """Parse width x height from ffmpeg stderr, correcting for SAR/DAR and rotation."""
    match = re.search(r'Stream.*Video.*\s(\d+)x(\d+)', ffmpeg_output)
    if not match:
        raise FFmpegError('Could not determine video resolution.')

    width, height = int(match.group(1)), int(match.group(2))

    # Non-square pixels: recompute width from display aspect ratio
    sar_match = re.search(r'SAR (\d+):(\d+) DAR (\d+):(\d+)', ffmpeg_output)
    if sar_match:
        sar_x, sar_y = int(sar_match.group(1)), int(sar_match.group(2))
        dar_x, dar_y = int(sar_match.group(3)), int(sar_match.group(4))
        r_sar = sar_x / sar_y
        r_dar = dar_x / dar_y
        if r_sar != 1.0 and r_dar != r_sar:
            log.debug('Non-square pixels (SAR %.2f, DAR %.2f) — adjusting width', r_sar, r_dar)
            width = round(height * r_dar)

    # Phone videos filmed sideways
    if re.search(r'rotate\s*:\s*(?:90|270|-90|-270)', ffmpeg_output):
        log.debug('Side rotation detected — swapping width and height')
        width, height = height, width

    return width, height


def _parse_duration(ffmpeg_output: str) -> float:
    """Return video duration in seconds from ffmpeg stderr."""
    match = re.search(r'Duration:\s*(\d+:\d+:\d+\.\d+)', ffmpeg_output)
    if not match:
        raise FFmpegError('Could not determine video duration.')
    return _duration_str_to_sec(match.group(1))


def _parse_fps(ffmpeg_output: str) -> float:
    """
    Return frame rate from ffmpeg stderr.

    Prefers ``X fps`` (display rate) over ``X tbr`` (timebase rate).
    Falls back to 25 fps with a warning.
    """
    match = re.search(r'(\d+(?:\.\d+)?)\s+fps', ffmpeg_output)
    if not match:
        match = re.search(r'(\d+(?:\.\d+)?)\s+tbr', ffmpeg_output)
    if not match:
        log.warning('Could not determine video FPS — defaulting to 25')
        return 25.0
    return float(match.group(1))


def _parse_codec(ffmpeg_output: str) -> str:
    """Return the video codec name (e.g. 'h264') or empty string."""
    match = re.search(r'Video:\s+(\w+)', ffmpeg_output)
    return match.group(1) if match else ''


def _duration_str_to_sec(s: str) -> float:
    """Convert ``'HH:MM:SS.ff'`` to a float number of seconds."""
    parts = s.split(':')
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


if __name__ == '__main__':
    import pytest

    from tests.unit import test_ffmpeg
    pytest.main([test_ffmpeg.__file__, '-v'])
