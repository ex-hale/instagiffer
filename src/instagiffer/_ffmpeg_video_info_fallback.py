import re
import subprocess
from pathlib import Path

from instagiffer.ffmpeg import FFmpegError, VideoInfo, _duration_str_to_sec, log


def get_video_info(ffmpeg_path: str | Path, video_path: str | Path):
    # ffmpeg writes stream info to stderr even when it "fails" (exit 1 is normal)
    result = subprocess.run(
        [ffmpeg_path, '-i', video_path],
        capture_output=True,
        text=True,
    )
    output = result.stderr

    width, height = _parse_resolution(output)
    duration_sec = _parse_duration(output)
    fps = _parse_fps(output)
    codec = _parse_codec(output)
    return VideoInfo(width, height, duration_sec, fps, codec)


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
