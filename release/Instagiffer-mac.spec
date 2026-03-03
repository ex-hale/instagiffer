# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Instagiffer macOS .app bundle.

Usage:  pyinstaller release/Instagiffer-mac.spec
Output: dist/Instagiffer.app
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
# ./deps/mac/magick and instagiffer.conf work unchanged.
datas = [
    (p("instagiffer.conf"), "."),
    (p("instagiffer.icns"), "."),
    (p("deps/mac/ffmpeg"), "deps/mac"),
    (p("deps/mac/magick"), "deps/mac"),
    (p("deps/mac/yt-dlp"), "deps/mac"),
    (p("deps/mac/gifsicle"), "deps/mac"),
    (p("deps/mac/etc"), "deps/mac/etc"),
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

app = BUNDLE(
    coll,
    name="Instagiffer.app",
    icon=p("instagiffer.icns"),
    bundle_identifier="com.instagiffer.instagiffer",
    info_plist={
        "CFBundleShortVersionString": __version__,
        "CFBundleVersion": __version__,
        "CFBundleDevelopmentRegion": "English",
        "CFBundleDisplayName": "Instagiffer",
        "CFBundleName": "Instagiffer",
        "NSHumanReadableCopyright": __copyright__,
        "LSMinimumSystemVersion": "11.0",
        "LSMultipleInstancesProhibited": True,
        "LSApplicationCategoryType": "public.app-category.graphics-design",
        "LSEnvironment": {"LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"},
        "NSScreenCaptureUsageDescription": "Instagiffer needs screen recording permission to capture screen regions as GIFs.",
    },
)
