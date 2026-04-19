"""Thin wrapper for FFmpeg video info and frame extraction."""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
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

    def get_video_info(self, video_path: Path) -> VideoInfo:
        """
        Return :class:`VideoInfo` for *video_path*.

        Handles non-square pixels (SAR/DAR correction) and phone-video
        side-rotation (90°/270°: swap width and height).
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
        try:
            fps = float(stream.get('avg_frame_rate', '').rstrip('/1'))
        except ValueError:
            fps = float(Fraction(stream.get('avg_frame_rate', '')))

        return VideoInfo(
            width=stream.get('width', 0),
            height=stream.get('height', 0),
            duration_sec=float(stream.get('duration', 0)),
            fps=fps,
            codec=stream.get('codec_name', ''),
        )

    def extract_frames(
        self,
        video_path: Path,
        output_dir: Path,
        fps: float,
        start_time: float = 0.0,
        duration: float = 5.0,
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
            start_time:        Seek position in seconds before extraction (Default: 0.0).
            duration:          How many seconds to extract (Default: 5 seconds).
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

        # -stats: emit progress lines to stderr
        cmd: list[str] = [str(self.ffmpeg), '-v', 'quiet', '-stats', '-progress', 'pipe:1']

        # -ss before -i: fast keyframe seek (accurate enough for GIF use)
        if start_time > 0:
            cmd += ['-ss', f'{start_time:.3f}']
        cmd += ['-t', f'{duration:.3f}']
        cmd += ['-i', str(video_path)]
        # -sn: skip subtitle streams
        cmd += ['-r', str(fps), '-sn']
        cmd += [str(output_dir / FRAME_PATTERN)]

        log.debug('extract_frames cmd: %s', ' '.join(cmd))

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert process.stdout is not None

        total_frames = fps * duration
        if progress_callback:
            for line in process.stdout:
                if not line.startswith('frame='):
                    continue
                this_frame = int(line[6:].rstrip())
                progress_callback(this_frame / total_frames)

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
        """If we're not using default paths, check for given or system paths"""
        if ffmpeg_path is None and self.ffmpeg.is_file() and self.ffprobe.is_file():
            log.debug(f'Using deps ffmpeg: {self.ffmpeg}')
            log.debug(f'Using deps ffprobe: {self.ffprobe}')
            return

        if ffmpeg_path is not None:
            this_path = Path(ffmpeg_path)
            if this_path.is_dir():
                ff_test = this_path / FFMPEG_EXE
                if ff_test.is_file():
                    self.ffmpeg = ff_test
                    log.debug(f'Using ffmpeg from given dir: {self.ffmpeg}')
                ff_test = this_path / FFPROBE_EXE
                if ff_test.is_file():
                    self.ffprobe = ff_test
                    log.debug(f'Using ffprobe from given dir: {self.ffprobe}')
            elif this_path.is_file():
                self.ffmpeg = this_path
                log.debug(f'Using ffmpeg from given path: {self.ffmpeg}')
                ff_test = this_path.parent / FFPROBE_EXE
                if ff_test.is_file():
                    self.ffprobe = ff_test
                    log.debug(f'Using ffprobe from next to given path: {self.ffprobe}')
            else:
                logging.error(f'Could not make sense of given {ffmpeg_path = }, checking system ...')

        else:
            this_path = shutil.which(FFMPEG_EXE)
            if not this_path:
                raise FFmpegNotFoundError(_NOT_FOUND_MSG.format(FFMPEG))
            self.ffmpeg = Path(this_path)
            log.debug(f'Using ffmpeg found in environment: {self.ffmpeg}')

            this_path = shutil.which(FFPROBE_EXE)
            if not this_path:
                logging.warning(_NOT_FOUND_MSG.format(FFPROBE), '\nUsing backup parser.')
            else:
                self.ffprobe = Path(this_path)
                log.debug(f'Using ffprobe found in environment: {self.ffprobe}')


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
