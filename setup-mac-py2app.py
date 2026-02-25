"""Build Instagiffer.app bundle for macOS using py2app. See Makefile mac_* targets."""

import glob
import os
import sys
from setuptools import setup

#
# Get version from environment
#

if "INSTAGIFFER_VERSION" in os.environ:
    INSTAGIFFER_VERSION = os.environ["INSTAGIFFER_VERSION"]
else:
    sys.exit(1)
if "INSTAGIFFER_PRERELEASE" in os.environ and "-pre" in os.environ["INSTAGIFFER_PRERELEASE"]:
    INSTAGIFFER_PRERELEASE = os.environ["INSTAGIFFER_PRERELEASE"]
    INSTAGIFFER_PRERELEASE = INSTAGIFFER_PRERELEASE.replace("-pre", ".")
else:
    INSTAGIFFER_PRERELEASE = ""


__author__ = "Exhale Software Inc."
__copyright__ = "Copyright (c) 2013-2026, Exhale Software Inc."
__version__ = INSTAGIFFER_VERSION + INSTAGIFFER_PRERELEASE

APP = ["main.py"]

DATA_FILES = [
    ("deps/mac", ["./deps/mac/yt-dlp", "./deps/mac/ffmpeg"]),
    ("deps/mac/im", glob.glob("./deps/mac/im/*")),
    "instagiffer.conf",
    "instagiffer.icns",
]

# Note: py2app can't create a standalone using built-in python

OPTIONS = {
    "iconfile": "instagiffer.icns",
    # 'argv_emulation': True,
    "optimize": 2,
    "packages": ["PIL"],
    "plist": {
        "CFBundleShortVersionString": __version__,
        "CFBundleVersion": __version__,
        "CFBundleDevelopmentRegion": "English",
        "CFBundleDisplayName": "Instagiffer",
        "CFBundleName": "Instagiffer",
        "NSHumanReadableCopyright": __copyright__,
        "CFBundleIdentifier": "com.instagiffer.instagiffer",
        "LSMinimumSystemVersion": "10.8.0",
        "LSMultipleInstancesProhibited": True,
        # 'CFBundlePackageType':          'APPL',
        # 'CFBundleSignature':            'HAPS',
        "LSApplicationCategoryType": "public.app-category.graphics-design",
        "LSEnvironment": {"LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"},
    },
}

setup(
    name="Instagiffer",
    url="http://instagiffer.com",
    version=__version__,
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)

# Make files executable
approot = "./dist/Instagiffer.app/Contents/Resources/"
for f in ["deps/mac/ffmpeg", "deps/mac/yt-dlp", "deps/mac/im/bin/convert"]:
    os.chmod(approot + f, 0o755)
