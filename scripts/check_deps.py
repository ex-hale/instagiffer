from __future__ import annotations

import io
import platform
import stat
import tarfile
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from instagiffer.common import CHECK, DEPS_DIR, EX, IM_A_LINUX, IM_A_MAC, IM_A_WIN, OS_NAME

_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'
}
_CHUNK_SIZE = 8192


def main() -> None:
    print(f'Checking dependencies: {DEPS_DIR.name} ...')
    if all(dep.check() for dep in (FFmpeg, Qt, Deno)):
        print(f'{CHECK} all dependencies checked!')


@dataclass
class _Dependency:
    name = ''
    base_url: str = ''
    file_names: tuple[str, ...] = ()

    @classmethod
    def _check(cls) -> bool:
        """Make sure ffmpeg and ffprobe are locally available.
        Sadly all the platforms have their specialties.
        """
        return False

    @classmethod
    def check(cls) -> bool:
        print(f'  Checking {cls.name} ...', end='')
        if not cls.missing_files():
            print(f'\b\b\b{CHECK}  ')
            return True

        check_name = f'_check_{OS_NAME}'
        if hasattr(cls, check_name):
            getattr(cls, check_name)()
        else:
            cls._check()

        missing = cls.missing_files()
        if not missing:
            print(f'  {CHECK} {cls.name} Done!')
            return True
        print(f'  {EX} {cls.name} files missing: {missing}')
        return False

    @classmethod
    def missing_files(cls) -> list[str]:
        return [f for f in cls.files() if not (DEPS_DIR / f).is_file()]

    @classmethod
    def files(cls) -> tuple[str, ...]:
        if IM_A_WIN:
            return tuple(f'{f}.exe' for f in cls.file_names)
        return cls.file_names

    @classmethod
    def make_files_executable(cls) -> None:
        for f in cls.files():
            this = DEPS_DIR / f
            this.chmod(this.stat().st_mode | stat.S_IEXEC)


class FFmpeg(_Dependency):
    name = 'FFmpeg'
    if IM_A_MAC:
        base_url = 'https://evermeet.cx/ffmpeg/getrelease/'
    else:
        base_url = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/'
    file_names = 'ffmpeg', 'ffprobe'

    @classmethod
    def _check_mac(cls) -> None:
        """Download ffmpeg and ffprobe separately in these 1 file only zips.
        The mac x64 binary repo offers them that way.
        FIXME: this currently only works for x86_64 macs!!!
        evermeet will not provide binaries for arm:
        https://evermeet.cx/ffmpeg/apple-silicon-arm
        We're currently downloading the intel binaries!
        Which might break with a `bad CPU type in executable` error!
        """
        ff_urls = f'{cls.base_url}zip', f'{cls.base_url}ffprobe/zip'
        for name, url in zip(cls.files(), ff_urls, strict=True):
            print(f'\n  Downloading {name} ...\n  {url}')
            buffer_bytes = read_into_buffer(url)
            with zipfile.ZipFile(buffer_bytes) as zip_object:
                zip_object.extractall(DEPS_DIR)
        cls.make_files_executable()

    @classmethod
    def _check_linux(cls) -> None:
        """Open linux specific tar.xz-buffer and extract our executables from `bin`."""
        url = f'{cls.base_url}ffmpeg-master-latest-linux64-gpl.tar.xz'
        print(f'\n  Downloading {cls.name} ...\n  {url}')
        package_buffer = read_into_buffer(url)
        print('  Opening package ...')
        with tarfile.open(fileobj=package_buffer, mode='r:xz') as tar_object:
            for member in tar_object.getmembers():
                if not member.isfile():
                    continue
                if not any(member.name.endswith(name) for name in cls.files()):
                    continue
                this_path = Path(member.name)
                if this_path.parent.name != 'bin':
                    continue
                member.name = this_path.name
                tar_object.extract(member, path=DEPS_DIR)
        cls.make_files_executable()

    @classmethod
    def _check_win(cls) -> None:
        """Open the Windows zip-buffer and extract executables from `bin`."""
        url = f'{cls.base_url}ffmpeg-master-latest-win64-gpl.zip'
        print(f'\n  Downloading {cls.name} ...\n  {url}')
        package_buffer = read_into_buffer(url)
        print('  Opening package ...')
        with zipfile.ZipFile(package_buffer) as zip_object:
            for member in zip_object.filelist:
                if member.is_dir():
                    continue
                if not any(member.filename.endswith(name) for name in cls.files()):
                    continue
                this_path = Path(member.filename)
                if this_path.parent.name != 'bin':
                    continue
                member.filename = this_path.name
                zip_object.extract(member, DEPS_DIR)


class Qt(_Dependency):
    name = 'Qt'
    file_names = (name,)

    @classmethod
    def _check(cls) -> bool:
        cls.file_names = ()
        if not IM_A_LINUX:
            return True
        import ctypes

        try:
            ctypes.CDLL('libxcb-cursor.so.0')
        except OSError:
            print(
                f'\b\b\b{EX} \nMissing "libxcb-cursor0"!\n'
                '  please try installing it and try again:\n'
                '  sudo apt install libxcb-cursor0'
            )
            return False
        return True


class Deno(_Dependency):
    name = 'deno'
    base_url = 'https://github.com/denoland/deno/releases/latest/download/'
    _arch = 'x86_64' if platform.processor() != 'arm64' else 'aarch64'
    file_names = (name,)

    @classmethod
    def _check(cls) -> bool:
        suffix_map = {
            'linux': 'unknown-linux-gnu',
            'win': 'pc-windows-msvc',
            'mac': 'apple-darwin',
        }

        url = f'{cls.base_url}deno-{cls._arch}-{suffix_map[OS_NAME]}.zip'
        print(f'\n  Downloading {cls.name} ...\n   {url}')
        buffer_bytes = read_into_buffer(url)
        with zipfile.ZipFile(buffer_bytes) as zip_object:
            zip_object.extractall(DEPS_DIR)

        return True


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
