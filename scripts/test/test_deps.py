import io
import os
import shutil
import sys
from importlib import reload
from pathlib import Path

import pytest

THIS_DIR = Path(__file__).parent
TEST_DATA = THIS_DIR / 'data'
SCRIPTS_DIR = THIS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(SCRIPTS_DIR))
import check_deps  # noqa: E402


def test_linux():
    name = 'linux'
    backup_platform = sys.platform
    sys.platform = name
    reload(check_deps)
    sys.platform = backup_platform

    assert check_deps.IM_A_LINUX
    assert not check_deps.IM_A_MAC
    assert not check_deps.IM_A_WIN

    def read_buffer_mock(url, *args):
        with open(TEST_DATA / 'linux_ffmpeg.tar.xz', 'rb') as file_object:
            return io.BytesIO(file_object.read())

    check_deps.read_into_buffer = read_buffer_mock  # ty:ignore[invalid-assignment]

    _package_check(name)


def test_windows():
    name = 'win32'
    _reload_with(name)

    assert not check_deps.IM_A_LINUX
    assert not check_deps.IM_A_MAC
    assert check_deps.IM_A_WIN

    def read_buffer_mock(url, *args):
        with open(TEST_DATA / 'win_ffmpeg.zip', 'rb') as file_object:
            return io.BytesIO(file_object.read())

    check_deps.read_into_buffer = read_buffer_mock  # ty:ignore[invalid-assignment]

    _package_check(name)


def test_mac():
    name = 'darwin'
    _reload_with(name)

    assert not check_deps.IM_A_LINUX
    assert check_deps.IM_A_MAC
    assert not check_deps.IM_A_WIN

    def read_buffer_mock(url: str, *args):
        if '/ffprobe/' in url:
            file_name = 'mac_ffprobe.zip'
        else:
            file_name = 'mac_ffmpeg.zip'
        with open(TEST_DATA / file_name, 'rb') as file_object:
            return io.BytesIO(file_object.read())

    check_deps.read_into_buffer = read_buffer_mock  # ty:ignore[invalid-assignment]

    _package_check(name)


def _reload_with(name: str):
    backup_platform = sys.platform
    sys.platform = name  # ty:ignore[invalid-assignment]
    reload(check_deps)
    sys.platform = backup_platform


def _package_check(name: str):
    backup_deps = check_deps._DEPS_PATH / f'_{name}_backup'
    if backup_deps.is_dir():
        shutil.rmtree(backup_deps)
    if check_deps.DEPS_DIR.is_dir():
        check_deps.DEPS_DIR.rename(backup_deps)

    assert not check_deps.DEPS_DIR.is_dir()

    check_deps.main()

    assert check_deps.DEPS_DIR.is_dir()
    missing = check_deps.ffmpeg_mising()
    assert not missing
    for name in check_deps.FF_EXES:
        assert not os.path.getsize(check_deps.DEPS_DIR / name)

    shutil.rmtree(check_deps.DEPS_DIR)
    if backup_deps.is_dir():
        backup_deps.rename(check_deps.DEPS_DIR)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
