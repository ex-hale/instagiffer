# Instagiffer

![Logo](doc/graphics/app_icon.png "Instagiffer Logo")

Whether you pronounce it GIF, or GIF, Instagiffer is the perfect tool for creating the best reaction moments to any situation. Sometimes, only a GIF will do in a conversation, and can say so much by saying so little. If you find yourself struggling to find the perfect GIF, look no more—just make your own. It's easy. Promise.

Instagiffer was designed during an era where websites would limit upload file sizes to 1MB, therefore, my primary goal was to generate highly-optimized GIFs that still look great. It started out as a CLI script which I used for my personal GIF creations and it grew organically from there—the user experience was never my primary focus, and because of this, the UI is a bit quirky. Help me improve it!

## Architecture

Instagiffer is a monolithic Python script. The UI is built with Tkinter. GIF generation is performed using FFmpeg (frame extraction from videos) and ImageMagick (effects, cropping, text, and GIF compression). Videos are downloaded from YouTube using yt-dlp. Optionally, gifsicle is used for further GIF optimization.

### Project Structure

```
instagiffer.py          # Main application (~9300 lines)
main.py                 # Entry point
instagiffer.conf        # Configuration file (INI format)
pyproject.toml          # Project metadata and tool config
Makefile                # Build, test, and release automation
release/                # Platform-specific build scripts
  setup-mac-py2app.py   #   macOS app bundle (py2app)
  setup-win-cx_freeze.py#   Windows executable (cx_Freeze)
  installer.iss         #   Windows installer (Inno Setup)
test/                   # Tests
  test_instagiffer.py   #   pytest suite
  instagiffer_automation.py # GUI automation tests
deps/                   # Bundled platform binaries
  mac/                  #   macOS: ffmpeg, yt-dlp, gifsicle
  win/                  #   Windows: ffmpeg, convert, yt-dlp, gifsicle
```

### Key Classes

| Class | Purpose |
|-------|---------|
| `InstaConfig` | Config file management (configparser INI format) |
| `AnimatedGif` | Core GIF engine (ffmpeg frame extraction, ImageMagick effects/compression) |
| `GifPlayerWidget` | Tkinter GIF preview widget |
| `GifApp` | Main GUI application |
| `InstaCommandLine` | CLI argument parser |
| `ImagemagickFont` | Font enumeration via ImageMagick |

## Setting Up Your Development Environment

### Requirements

- Python 3.10+ (developed on 3.14)
- External tools: ffmpeg, ImageMagick (`magick`), yt-dlp, gifsicle

### macOS

Install dependencies via [Homebrew](https://brew.sh):

```bash
brew install python@3.14 python-tk@3.14 imagemagick gifsicle ffmpeg yt-dlp
pip install pillow
```

Clone and set up the project:

```bash
git clone https://github.com/ex-hale/instagiffer.git
cd instagiffer
make setup    # Creates .venv and installs dev dependencies
make run      # Launches the app
```

### Windows

Prerequisites:
- [Python 3.10+](https://www.python.org/downloads/)
- [Inno Setup](https://jrsoftware.org/isdl.php) (for building the installer)
- Pillow: `pip install pillow`

Update the bundled binaries in `deps/win/`:
- [FFmpeg static build](https://www.gyan.dev/ffmpeg/builds/)
- [ImageMagick portable](https://imagemagick.org/script/download.php#windows)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp/releases)
- [gifsicle](https://eternallybored.org/misc/gifsicle/)

## Development

The Makefile provides all common development tasks:

```bash
make setup      # Create venv and install dependencies
make run        # Run the application
make test       # Run pytest suite (downloads test videos on first run)
make lint       # Run pylint
make format     # Run black formatter (line length: 200)
make clean      # Remove build artifacts, venv, test data
```

Configuration is in `pyproject.toml`. Black is configured with a 200-character line length.

## Building a Release

Before releasing, double-check:
- Version numbers updated in `instagiffer.py`?
- Help links work?
- Tested on a vanilla Mac/Windows VM?

### macOS

```bash
make mac_deps     # Download/install bundled dependencies
make mac_app      # Build .app bundle with py2app
make mac_dmg      # Build DMG installer
make mac_pkg      # Build .pkg installer
make mac_release  # Build both DMG and .pkg
```

### Windows

```bash
make win_exe        # Build executable with cx_Freeze
make win_installer  # Build Inno Setup installer
make win_portable   # Build portable zip
make win_release    # Build installer + portable zip
```

## Testing

### Test URLs
- https://www.youtube.com/watch?v=EPP7WLuZVUk

### Regression Test Checklist

- Online downloads
  - YouTube (especially popular music videos)
  - VEVO
  - DailyMotion, Metacafe
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
![Instagiffer Color Swatch](doc/graphics/color.png?raw=true "Instagiffer Color Swatch")

Main Color: `#395976`

### Font

"Bookman Old Style"

## License

BSD 4-Clause. See [main.py](main.py) for the full license text.
