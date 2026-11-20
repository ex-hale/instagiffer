"""Build a static ffmpeg binary for macOS (Apple Silicon) into deps/mac/."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "deps" / "build"
OUT_DIR = BUILD_DIR / "ffmpeg-out"
DEST = ROOT / "deps" / "mac" / "ffmpeg"

FFMPEG_VERSION = "7.1"
TARBALL = f"ffmpeg-{FFMPEG_VERSION}.tar.xz"
URL = f"https://ffmpeg.org/releases/{TARBALL}"
SRC = BUILD_DIR / f"ffmpeg-{FFMPEG_VERSION}"

CONFIGURE_FLAGS = [
    "./configure",
    f"--prefix={OUT_DIR.resolve()}",
    "--enable-static",
    "--disable-shared",
    "--disable-doc",
    "--disable-ffplay",
    "--disable-ffprobe",
    "--enable-gpl",
    "--enable-version3",
    "--enable-libx264",
]


def run(cmd, cwd=None):
    print(f"+ {' '.join(map(str, cmd))}", flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def main():
    if DEST.exists():
        print(f"ffmpeg already present at {DEST}")
        return

    # 1. Ensure build deps are installed (x264, nasm, etc.)
    #    Assumes `brew bundle` has already run, or run it here:
    if shutil.which("brew") is None:
        sys.exit("Error: Homebrew is required (install x264, nasm via Brewfile)")

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    DEST.parent.mkdir(parents=True, exist_ok=True)

    # 2. Download & extract
    tarball = BUILD_DIR / TARBALL
    if not tarball.exists():
        print(f"Downloading {URL} ...")
        run(["curl", "-fSL", "-o", str(tarball), URL])
    if not SRC.exists():
        run(["tar", "-xf", str(tarball), "-C", str(BUILD_DIR)])
        tarball.unlink()

    # 3. Configure, build, install
    run(CONFIGURE_FLAGS, cwd=SRC)
    ncpu = subprocess.check_output(["sysctl", "-n", "hw.ncpu"]).decode().strip()
    run(["make", f"-j{ncpu}"], cwd=SRC)
    run(["make", "install"], cwd=SRC)

    # 4. Copy the static binary
    shutil.copy2(OUT_DIR / "bin" / "ffmpeg", DEST)
    os.chmod(DEST, 0o755)
    print(f"ffmpeg ready at {DEST}")


if __name__ == "__main__":
    main()