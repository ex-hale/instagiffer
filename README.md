# Instagiffer

![Logo](assets/app_icon.png "Instagiffer Logo")

Whether you pronounce it GIF, or GIF, Instagiffer is the perfect tool for creating the best reaction moments to any situation. Sometimes, only a GIF will do in a conversation, and can say so much by saying so little. If you find yourself struggling to find the perfect GIF, look no more. Just make your own. It's easy. Promise.

Instagiffer was designed during an era where websites would limit upload file sizes to 1MB, therefore, my primary goal was to generate highly-optimized GIFs that still looked great. It started out as a CLI script which I used for my personal GIF creations and it grew organically from there. The user experience was never my primary focus, so the UI is a bit quirky. Help me improve it!

## Architecture

Instagiffer is a single-file Python application (`instagiffer.py`) built with a Tkinter GUI. It orchestrates several external tools to turn videos into optimized GIFs: FFmpeg extracts frames from video files, ImageMagick handles effects, cropping, text overlays, and GIF compression, and gifsicle provides optional further optimization. Videos can be loaded from local files or downloaded from YouTube and other sites via yt-dlp. All configuration is stored in an INI file (`instagiffer.conf`) managed by Python's configparser.

## Setting Up Your Development Environment

### macOS

Requires [Homebrew](https://brew.sh).

```bash
git clone https://github.com/ex-hale/instagiffer.git
cd instagiffer
make deps    # Installs Homebrew packages, creates .venv, builds platform dependencies
make run     # Launches the app
```

### Windows

Prerequisites (one-time setup on a fresh machine). In any PowerShell prompt:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install-devtools.ps1
```

This uses [winget](https://learn.microsoft.com/en-us/windows/package-manager/winget/) (built into
Windows 11) to install Python 3.13, Git for Windows, GNU Make, and Inno Setup 6. Then open a new
Git Bash window:

```bash
git clone https://github.com/ex-hale/instagiffer.git
cd instagiffer
make deps    # Downloads ffmpeg, yt-dlp, gifsicle, and ImageMagick into deps/win/
make run     # Launches the app
```

> **Tip:** If you see a PowerShell execution policy error when activating the venv, run
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once to make it permanent.

## Development

The Makefile provides all common development tasks:

```bash
make init       # Create venv and install dependencies
make run        # Run the application
make test       # Run pytest suite (downloads test videos on first run)
make lint       # Run pylint
make format     # Run black formatter (line length: 200)
make clean      # Remove build artifacts, venv, test data
make dist       # Build distributable (DMG on macOS, installer on Windows)
```

Configuration is in `pyproject.toml`. Black is configured with a 200-character line length.

## Building a Release

Before releasing, double-check:
- Version numbers updated in `instagiffer.py`?
- Help links work?
- Tested on a vanilla Mac/Windows VM?

```bash
make dist    # Build distributable (DMG on macOS, installer on Windows)
```

Output goes to `dist/`. All dependencies are fetched automatically.

> **Note:** The macOS app is not notarized, so users will need to right-click and select
> "Open" on first launch to bypass the Gatekeeper warning.

## Testing

### Test URLs
- https://www.youtube.com/watch?v=EPP7WLuZVUk

### Regression Test Checklist

These are being migrated into the automated test suite (`make test`). Until then, run through manually before a release.

- Online downloads
  - YouTube (especially popular music videos)
  - TikTok, Instagram Reels, Reddit
- Videos where h > w, w == h, w > h
- Invalid video formats
- Cellphone videos shot in portrait and landscape
- Corrupted video
- Any videos that revealed a bug previously
- Image sequence
- Image sequence with bad image in the middle
- Image sequence of 1
- Unicode paths
- Cinemagraphs
- Settings at extremes
- Specify time out of range
- GIF overwrite on and off
- Different YouTube qualities
- Screen capture
- Check for memory leaks
- Super-long GIF
- Help > Generate Bug Report
- Make a 5 second GIF using screen capture. If you have a second monitor, capture something there.
- Frames > Export Frames (pick a folder and ensure the frames are correctly exported)
- Frames > Delete Frames. Delete all even frames
- Frames > Import Frames - use the frames you just exported (you can multi-select)
- Create a GIF of people having a dialog with text captions. Do this using a YouTube video.
- Create a GIF 10 seconds or longer, and under 1MB
- Input invalid data
- Unpopular video formats or sites
- Button-smash the GUI (hit Escape to interrupt events)
- Load invalid or corrupted movie files
- Edit `instagiffer.conf` and muck around with config parameters (requires restart)

## Look and Feel

### Color
Main Color: `#395976`

### Font

"Bookman Old Style"

## License

BSD 4-Clause. See [main.py](main.py) for the full license text.
