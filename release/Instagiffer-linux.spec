# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Instagiffer Linux .app bundle.

Usage:  pyinstaller release/Instagiffer-linux.spec
Output: dist/Instagiffer/
"""

import os
import sys

# Project root is one level up from the spec file
ROOT = os.path.join(SPECPATH, "..")

sys.path.insert(0, ROOT)
from instagiffer import __version__, __copyright__

block_cipher = None

p = lambda *parts: os.path.join(ROOT, *parts)

# All data files land in _internal/ (PyInstaller's default data root).
# The app's main() does os.chdir(sys._MEIPASS) so relative paths like
# ./deps/linux/magick and instagiffer.conf work unchanged.
datas = [
    (p("instagiffer.conf"), "."),
    (p("deps/linux/ffmpeg"), "deps/linux"),
    (p("deps/linux/magick"), "deps/linux"),
    (p("deps/linux/yt-dlp"), "deps/linux"),
    # (p("deps/linux/gifsicle"), "deps/linux"),
    # (p("deps/linux/etc"), "deps/linux/etc"),
]

a = Analysis(
    [p("main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["doctest", "pdb", "unittest", "difflib"],
    noarchive=False,
    optimize=2,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Instagiffer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Instagiffer",
)
