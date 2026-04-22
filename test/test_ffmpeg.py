from pathlib import Path

import pytest

from instagiffer import ffmpeg

THIS_DIR = Path(__file__).parent
TEST_DATA = THIS_DIR / 'data'


def test_info():
    test_videos = list(TEST_DATA.glob('*.mp4'))
    assert test_videos != []

    ffm_wrap = ffmpeg.FFmWrap()
    assert ffm_wrap.ffmpeg.is_file()
    assert ffm_wrap.ffprobe.is_file()

    info = ffm_wrap.get_video_info(test_videos[0])
    assert round(info.aspect_ratio, 2) == 1.33
    assert info.fps >= 15
    assert info.height >= 10
    assert info.width >= 10
    assert info.duration_sec >= 1
    assert info.duration_ms >= 1000

    ffm_wrap.ffprobe = Path()
    info_fallback = ffm_wrap.get_video_info(test_videos[0])
    for k, v in info_fallback:
        assert getattr(info, k) == v


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
