import os
import sys
from pathlib import Path

CHECK = b'\xe2\x9c\x94'.decode()
EX = b'\xe2\x9c\x96'.decode()

IM_A_LINUX: bool = sys.platform == 'linux'
IM_A_WIN: bool = sys.platform == 'win32'
IM_A_MAC: bool = sys.platform == 'darwin'

LIB_PATH = Path(__file__).parent
SOURCE_PATH = LIB_PATH.parent
PROJECT_ROOT = SOURCE_PATH.parent
DEPS_ROOT = PROJECT_ROOT / 'deps'
ASSETS_PATH = PROJECT_ROOT / 'assets'

if IM_A_LINUX:
    DEPS_DIR = DEPS_ROOT / 'linux'
    _APP_DATA_ROOT = Path.home() / '.local' / 'share'
    _CACHE_ROOT = Path.home() / '.cache'
elif IM_A_MAC:
    DEPS_DIR = DEPS_ROOT / 'mac'
    _APP_DATA_ROOT = Path.home() / '.local' / 'share'
    _CACHE_ROOT = Path.home() / '.cache'
elif IM_A_WIN:
    DEPS_DIR = DEPS_ROOT / 'win'
    _APP_DATA_ROOT = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    _CACHE_ROOT = _APP_DATA_ROOT
else:
    raise RuntimeError(f'Unsupported system "{sys.platform}"?!?!')

APP_DATA_DIR = _APP_DATA_ROOT / 'instagiffer'
PROJECTS_DIR = APP_DATA_DIR / 'projects'
DOWNLOADS_DIR = APP_DATA_DIR / 'downloads'
FRAMES_CACHE_DIR = _CACHE_ROOT / 'instagiffer' / 'frames_cache'
