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
elif IM_A_MAC:
    DEPS_DIR = DEPS_ROOT / 'mac'
elif IM_A_WIN:
    DEPS_DIR = DEPS_ROOT / 'win'
else:
    raise RuntimeError(f'Unsupported system "{sys.platform}"?!?!')
