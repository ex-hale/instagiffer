"""Build Windows executable for Instagiffer using cx_Freeze. See Makefile win_* targets."""

import os
import sys
from cx_Freeze import setup, Executable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from instagiffer import __version__

__author__ = "Justin Todd"
__email__ = "instagiffer@gmail.com"
__copyright__ = "Copyright 2013-2026, Exhale Software Inc."
application_title = "Instagiffer"
main_python_file = "instagiffer.py"

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
    version=__version__,
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
