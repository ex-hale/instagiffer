"""Thin wrapper for FFmpeg video info and frame extraction."""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from instagiffer.common import DEPS_DIR, IM_A_WIN

log = logging.getLogger(__name__)

# Output frame filename pattern - 1-indexed, zero-padded to 4 digits
FRAME_PATTERN = 'image%04d.png'
FRAME_GLOB = 'image*.png'
_EXT = '' if not IM_A_WIN else '.exe'
FFMPEG = 'ffmpeg'
FFPROBE = 'ffprobe'
FFMPEG_EXE = f'{FFMPEG}{_EXT}'
FFPROBE_EXE = f'{FFPROBE}{_EXT}'
EXECUTABLES = FFMPEG_EXE, FFPROBE_EXE
_NOT_FOUND_MSG = (
    '{} not found in environment PATH!\n'
    'Use `uv run poe deps` to get the executables locally or\n'
    'Install it system wide and make sure it is on your environment PATH.'
)


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

    def __iter__(self):
        for attr in ('width', 'height', 'aspect_ratio', 'duration_sec', 'duration_ms', 'fps', 'codec'):
            yield attr, getattr(self, attr)


class FFmwrapp:
    """
    Thin wrapper around the `ffmpeg` executable.

    Usage::

        ffmpeg = FFmwrapp()                         # auto-locate in PATH
        ffmpeg = FFmwrapp(Path('/usr/bin/ffmpeg'))  # explicit path

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
        self.ffmpeg: Path = DEPS_DIR / FFMPEG_EXE
        self.ffprobe: Path = DEPS_DIR / FFPROBE_EXE
        self._check_paths(ffmpeg_path)
        log.debug('Using ffmpeg: %s', self.ffmpeg)

    def get_video_info(self, video_path: Path) -> VideoInfo:
        """
        Return :class:`VideoInfo` for *video_path*.

        Handles non-square pixels (SAR/DAR correction) and phone-video
        side-rotation (90°/270° → swap width and height).
        """
        video_path = Path(video_path)
        if not video_path.is_file():
            raise FileNotFoundError(f'Video not found: {video_path}')

        if not self.ffprobe.is_file():
            from instagiffer._ffmpeg_video_info_fallback import get_video_info

            return get_video_info(self.ffmpeg, video_path)

        result = subprocess.run(
            [self.ffprobe, '-v', 'quiet', '-print_format', 'json', '-show_streams', video_path],
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        if not data or 'streams' not in data or not data['streams']:
            raise FFmpegError(f'Could not extract video info from {video_path}')

        stream = data['streams'][0]
        return VideoInfo(
            width=stream.get('width', 0),
            height=stream.get('height', 0),
            duration_sec=float(stream.get('duration', 0)),
            fps=float(stream.get('avg_frame_rate', '').rstrip('/1')),
            codec=stream.get('codec_name', '')
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
        if not video_path.is_file():
            raise FileNotFoundError(f'Video not found: {video_path}')

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

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
            raise FFmpegError(f'ffmpeg exited with code {process.returncode}. Command: {" ".join(cmd)}')

        frames = sorted(output_dir.glob(FRAME_GLOB))
        if not frames:
            raise FFmpegError(f'No frames were extracted from "{video_path.name}". Is it a supported video format?')

        log.info('Extracted %d frames from "%s"', len(frames), video_path.name)

        if progress_callback:
            progress_callback(1.0)

        return frames

    def _check_paths(self, ffmpeg_path: Path | None = None):
        """If were not using default paths, check for given or system paths"""
        if ffmpeg_path is None and self.ffmpeg.is_file() and self.ffprobe.is_file():
            return

        if ffmpeg_path is not None:
            this_path = Path(ffmpeg_path)
            if this_path.is_dir():
                ff_test = this_path / FFMPEG_EXE
                if ff_test.is_file():
                    self.ffmpeg = ff_test
                ff_test = this_path / FFPROBE_EXE
                if ff_test.is_file():
                    self.ffprobe = ff_test
            elif this_path.is_file():
                self.ffmpeg = this_path
                ff_test = this_path.parent / FFPROBE_EXE
                if ff_test.is_file():
                    self.ffprobe = ff_test
            else:
                logging.error(f'Could not make sense of given {ffmpeg_path = }, checking system ...')

        else:
            this_path = shutil.which(FFMPEG_EXE)
            if not this_path:
                raise FFmpegNotFoundError(_NOT_FOUND_MSG.format(FFMPEG))
            this_path = shutil.which(FFPROBE_EXE)
            if not this_path:
                logging.warning(_NOT_FOUND_MSG.format(FFPROBE), '\nUsing backup parser.')


def _duration_str_to_sec(s: str) -> float:
    """Convert ``'HH:MM:SS.ff'`` to a float number of seconds."""
    parts = s.split(':')
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


class FFmpegError(Exception):
    """Raised when ffmpeg encounters an error."""


class FFmpegNotFoundError(FFmpegError):
    """Raised when the ffmpeg executable cannot be located."""


if __name__ == '__main__':
    import pytest

    from test import test_ffmpeg

    pytest.main([test_ffmpeg.__file__, '-v'])
