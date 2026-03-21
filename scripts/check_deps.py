from __future__ import annotations

import io
import os
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path

IM_A_MAC: bool = sys.platform == 'darwin'
IM_A_PC: bool = sys.platform == 'win32'
IM_A_LINUX: bool = sys.platform == 'linux'
_ROOT = Path(__file__).parent.parent
_DEPS_PATH = _ROOT / 'deps'


_EXES = 'ffmpeg', 'ffprobe'
if IM_A_PC:
    EXES: tuple[str, ...] = tuple(f'{name}.exe' for name in _EXES)
    FFMPEG_URL = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip'
    DEPS_DIR = _DEPS_PATH / 'win'
elif IM_A_LINUX:
    EXES: tuple[str, ...] = _EXES
    FFMPEG_URL = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz'
    DEPS_DIR = _DEPS_PATH / 'linux'
elif IM_A_MAC:
    EXES: tuple[str, ...] = _EXES
    FFMPEG_URL = 'https://evermeet.cx/ffmpeg/getrelease/zip'
    DEPS_DIR = _DEPS_PATH / 'mac'


_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'}
_CHUNK_SIZE = 8192

DEPS_DIR = DEPS_DIR.parent / 'linux'
EXES: tuple[str, ...] = _EXES

def main():
    if all((DEPS_DIR / name).is_file() for name in EXES):
        print('All ffmpeg dependencies fullified!')
        return

    import tarfile

    url = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz'
    stored = DEPS_DIR / os.path.basename(url)
    if stored.is_file():
        with open(stored, 'rb') as file_object:
            package_bytes = file_object.read()
    else:
        print('  Downloading ffmpeg ...')
        package_bytes = read_raw(url)

    print('  Opening package ...')
    with tarfile.open(fileobj=io.BytesIO(package_bytes), mode='r:xz') as tar_object:
        for member in tar_object.getmembers():
            if not member.isfile():
                continue
            if not any(member.name.endswith(name) for name in EXES):
                continue
            this_path = Path(member.name)
            if this_path.parent.name != 'bin':
                continue
            member.name = this_path.name
            tar_object.extract(member, path=DEPS_DIR)

    print('Ffmpeg Done!')

class DownloadCB:
    def __init__(self, name: str):
        import rich.progress

        self._name = name
        self._progress = rich.progress.Progress(
            '[progress.description]{task.description}',
            rich.progress.BarColumn(),
            rich.progress.DownloadColumn(),
            rich.progress.TransferSpeedColumn(),
            rich.progress.TimeRemainingColumn(),
        )
        self._task = None
        self._progress.start()

    def callback(self, current: int, total: int):
        if self._task is None:
            self._task = self._progress.add_task(' ', total=total if total != -1 else None)
        self._progress.update(self._task, completed=current)
        if total != -1 and current >= total:
            self._progress.stop()


def read_raw(url: str, progress_callback: Callable | None = None, size: int | None = None) -> bytes:
    """Fetch the contents of a URL and return them as raw bytes.

    Downloads the response in chunks of :data:`_CHUNK_SIZE` bytes, calling
    ``progress_callback(current, total)`` after each chunk. If ``total`` is
    unknown the server did not send a ``Content-Length`` header and ``total``
    will be ``-1``.

    :param url: The URL to fetch.
    :param progress_callback: Optional callable receiving (current: int, total: int) byte counts
        as the download progresses. Falls back to debug logging if not provided.
    :param size: If given, read only this many bytes from the response instead
        of consuming the full body. Must be an :class:`int`.
    :return: The raw response body as bytes.
    :raises RuntimeError: If ``size`` is provided but is not an :class:`int`.
    :raises urllib.error.URLError: If the URL cannot be reached.
    """
    if progress_callback is None:
        progress_callback = DownloadCB(os.path.basename(url)).callback
    request = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(request) as response:
        total = int(response.headers.get('Content-Length', -1))
        if size is not None:
            if not isinstance(size, int):
                raise RuntimeError('Value `size` needs to be Integer!')
            return response.read(size)

        chunks = []
        current = 0
        while True:
            chunk = response.read(_CHUNK_SIZE)
            if not chunk:
                break
            chunks.append(chunk)
            current += len(chunk)
            progress_callback(current, total)

        return b''.join(chunks)


if __name__ == '__main__':
    main()
