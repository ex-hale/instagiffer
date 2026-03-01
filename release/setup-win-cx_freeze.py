"""Build Windows executable for Instagiffer using cx_Freeze. See Makefile win_* targets."""

__author__ = "Justin Todd"
__email__ = "instagiffer@gmail.com"
__copyright__ = "Copyright 2013-2026, Exhale Software Inc."
application_title = "Instagiffer"
main_python_file = "instagiffer.py"

import os
import sys
from cx_Freeze import setup, Executable

#
# Get version from environment
#

if "INSTAGIFFER_VERSION" in os.environ:
    INSTAGIFFER_VERSION = os.environ["INSTAGIFFER_VERSION"]
else:
    sys.exit(1)

if "INSTAGIFFER_PRERELEASE" in os.environ:
    INSTAGIFFER_PRERELEASE = os.environ["INSTAGIFFER_PRERELEASE"]
    INSTAGIFFER_VERSION += INSTAGIFFER_PRERELEASE.replace("pre-", ".")

base = None

# Empty log files
logFiles = ["instagiffer.exe.log", "instagiffer-event.log"]
for log in logFiles:
    open(log, "w+").close()

DATA_FILES = []

if sys.platform == "darwin":
    DATA_FILES = [
        "deps/mac/",
        "fonts/",
        "instagiffer.conf",
        "instagiffer.icns",
    ]
elif sys.platform == "win32":
    base = "Win32GUI"

    DATA_FILES = [
        "release/uninstall.ico",
        "instagiffer.ico",
        "instagiffer.conf",
        "deps/win/",
    ]


includes = []
excludes = ["doctest", "pdb", "unittest", "difflib"]  # ssl (Needed for imgur uploading)
packages = ["PIL", "PIL.ImageDraw", "PIL.ImageGrab"]
options = {
    "build_exe": {
        "excludes": excludes,
        "includes": includes,
        "packages": packages,
        "include_files": DATA_FILES + logFiles,
        "optimize": True,
        "silent": True,
    }
}

setup(
    name=application_title,
    version=INSTAGIFFER_VERSION,
    description="Instagiffer - Animated GIF creator",
    url="http://www.instagiffer.com",
    author=__author__,
    options=options,
    executables=[Executable(main_python_file, base=base, icon="instagiffer.ico")],
)


# Mac post-compilation activities
if sys.platform == "darwin":
    # Make instagiffer executable
    os.chmod("build/Instagiffer.app/Contents/MacOS/instagiffer", 0o755)
