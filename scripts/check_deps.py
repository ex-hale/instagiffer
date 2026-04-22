from __future__ import annotations

import io
import urllib.request
from collections.abc import Callable
from pathlib import Path

from instagiffer.common import CHECK, DEPS_DIR, EX, IM_A_LINUX, IM_A_MAC, IM_A_WIN

_FF_EXES = 'ffmpeg', 'ffprobe'
_FFMPEG_BTBN = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/'
if IM_A_WIN:
    FF_EXES: tuple[str, ...] = tuple(f'{name}.exe' for name in _FF_EXES)
    FFMPEG_URL = f'{_FFMPEG_BTBN}ffmpeg-master-latest-win64-gpl.zip'
elif IM_A_LINUX:
    FF_EXES: tuple[str, ...] = _FF_EXES
    FFMPEG_URL = f'{_FFMPEG_BTBN}ffmpeg-master-latest-linux64-gpl.tar.xz'
elif IM_A_MAC:
    evermeet_repo = 'https://evermeet.cx/ffmpeg/getrelease/'
    FF_EXES: tuple[str, ...] = _FF_EXES
    FFMPEG_URL = f'{evermeet_repo}zip'
    FFPROBE_URL = f'{evermeet_repo}ffprobe/zip'

_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'}
_CHUNK_SIZE = 8192


def main() -> None:
    print(f'Checking dependencies: {DEPS_DIR.name} ...')
    all_good = True
    if not check_ffmpeg():
        all_good = False

    if all_good:
        print(f'{CHECK} all dependencies checked!')


def check_ffmpeg() -> bool:
    """Make sure ffmpeg and ffprobe are locally available.
    Sadly all the platforms have their specialties.
    """
    if not ffmpeg_missing():
        print(f'  {CHECK} Ffmpeg')
        return True

    if IM_A_MAC:
        _check_ffmpeg_mac()
    else:
        print('  Downloading ffmpeg ...')
        package_buffer = read_into_buffer(FFMPEG_URL)

        print('  Opening package ...')
        if IM_A_LINUX:
            _check_ffmpeg_linux(package_buffer)
        else:
            _check_ffmpeg_win(package_buffer)

    missing = ffmpeg_missing()
    if not missing:
        print(f'  {CHECK} Ffmpeg Done!')
        return True
    print(f'  {EX} FFmpeg files missing: {missing}')
    return False


def ffmpeg_missing() -> list[str]:
    """Get list of missing executable names if any."""
    return [x for x in FF_EXES if not (DEPS_DIR / x).is_file()]


def _check_ffmpeg_linux(io_object: io.BytesIO) -> None:
    """Open linux specific tar.xz-buffer and extract our executables from `bin`."""
    import tarfile

    with tarfile.open(fileobj=io_object, mode='r:xz') as tar_object:
        for member in tar_object.getmembers():
            if not member.isfile():
                continue
            if not any(member.name.endswith(name) for name in FF_EXES):
                continue
            this_path = Path(member.name)
            if this_path.parent.name != 'bin':
                continue
            member.name = this_path.name
            tar_object.extract(member, path=DEPS_DIR)


def _check_ffmpeg_win(io_object: io.BytesIO) -> None:
    """Open the Windows zip-buffer and extract executables from `bin`."""
    import zipfile

    with zipfile.ZipFile(io_object) as zip_object:
        for member in zip_object.filelist:
            if member.is_dir():
                continue
            if not any(member.filename.endswith(name) for name in FF_EXES):
                continue
            this_path = Path(member.filename)
            if this_path.parent.name != 'bin':
                continue
            member.filename = this_path.name
            zip_object.extract(member, DEPS_DIR)


def _check_ffmpeg_mac() -> None:
    """Download ffmpeg and ffprobe separately in these 1 file only zips.
    The mac binary repo offers them that way.
    """
    import zipfile

    for name, url in zip(FF_EXES, (FFMPEG_URL, FFPROBE_URL), strict=True):
        print(f'  Downloading {name} ...')
        buffer_bytes = read_into_buffer(url)
        with zipfile.ZipFile(buffer_bytes) as zip_object:
            zip_object.extractall(DEPS_DIR)


class DownloadCB:
    def __init__(self):
        import rich.progress

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
        progress_callback = DownloadCB().callback
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


def read_into_buffer(url: str, progress_callback: Callable | None = None) -> io.BytesIO:
    """Fetch contents of `url` and return them as io buffer object.

    Downloads the response in chunks of :data:`_CHUNK_SIZE` bytes, calling
    ``progress_callback(current, total)`` after each chunk. If ``total`` is
    unknown the server did not send a ``Content-Length`` header and ``total``
    will be ``-1``.

    :param url: The URL to fetch data from.
    :param progress_callback: Optional callable receiving (current: int, total: int) byte counts
        as the download progresses. Falls back to debug logging if not provided.
    :return: All of the response bytes in io.BytesIO object.
    :raises RuntimeError: If ``size`` is provided but is not an :class:`int`.
    :raises urllib.error.URLError: If the URL cannot be reached."""
    if progress_callback is None:
        progress_callback = DownloadCB().callback

    request = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(request) as response:
        current = 0
        total = int(response.headers.get('Content-Length', -1))
        bytes_buffer = io.BytesIO()
        while True:
            chunk = response.read(_CHUNK_SIZE)
            if not chunk:
                break
            bytes_buffer.write(chunk)
            current += len(chunk)
            progress_callback(current, total)
        bytes_buffer.seek(0)
        return bytes_buffer


if __name__ == '__main__':
    main()
