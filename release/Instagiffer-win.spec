# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Instagiffer Windows .exe build.

Usage:  pyinstaller release/Instagiffer-win.spec
Output: dist/Instagiffer/Instagiffer.exe
"""

import os
import sys

# Project root is one level up from the spec file
ROOT = os.path.join(SPECPATH, "..")

sys.path.insert(0, ROOT)
from instagiffer import __version__, __copyright__

p = lambda *parts: os.path.join(ROOT, *parts)

# Bundle deps/win/ plus app assets. main() does os.chdir(sys._MEIPASS) on startup
# so relative paths in instagiffer.conf (e.g. .\deps\win\magick.exe) resolve correctly.
datas = [
    (p("instagiffer.conf"), "."),
    (p("instagiffer.ico"), "."),
    (p("release/uninstall.ico"), "."),
    (p("deps/win"), "deps/win"),
]

a = Analysis(
    [p("main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=["win32api", "win32event", "winerror", "win32con"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["doctest", "pdb", "unittest", "difflib"],
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure, a.zipped_data)

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
    icon=p("instagiffer.ico"),
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
