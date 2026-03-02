"""
Instagiffer Test Suite

GUI tests use InstagifferAutomator and run on both macOS (AppleScript) and Windows (pywinauto).
CLI tests run on all platforms.

Usage:
    python -m pytest test/ -v
    python -m pytest test/ -v --app /Applications/Instagiffer.app   # macOS frozen app
    python -m pytest test/ -v --app dist/Instagiffer/Instagiffer.exe  # Windows frozen app
"""

import os
import sys
import time
import pytest
from instagiffer_automation import InstagifferAutomator

TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data")
TEST_VIDEOS = sorted(os.path.join(TEST_DIR, f) for f in os.listdir(TEST_DIR)) if os.path.isdir(TEST_DIR) else []


requires_gui = pytest.mark.skipif(
    sys.platform not in ("darwin", "win32"),
    reason="GUI automation requires macOS or Windows",
)
requires_test_video = pytest.mark.skipif(
    not os.path.isdir(TEST_DIR) or not os.listdir(TEST_DIR),
    reason="No test videos found — run: make test-videos",
)


# Helpers


def gif_path_from_status(status):
    """Extract the GIF file path from a status bar message."""
    assert "Path:" in status, f"Expected 'Path:' in status, got: {status}"
    return status.split("Path:", 1)[1].strip()


def assert_valid_gif(path):
    """Assert the file at path exists, was recently created, and has valid GIF magic bytes."""
    assert os.path.isfile(path), f"GIF not found at {path}"
    age = time.time() - os.path.getmtime(path)
    assert age < 10, f"GIF is {age:.0f}s old — stale file, not from this run"
    with open(path, "rb") as f:
        magic = f.read(6)
    assert magic == b"GIF89a", f"Not a valid GIF file (magic: {magic!r})"


# GUI tests


@requires_gui
@requires_test_video
def test_full_smoke(app_path):
    """Full smoke test: load video, create GIF with all options, verify output, generate bug report."""
    video = os.path.join(TEST_DIR, "test_video_1.mp4")

    with InstagifferAutomator.launch(app_path=app_path, config_overrides={"color": {"numColors": "128"}}) as app:
        # Verify app started successfully
        app.assert_log_contains(r"Instagiffer: \d+\.\d+\.\d+")

        # Load a video
        app.load_video(video)

        # Apply a manual crop (shrink by 10px each side, nudge offset 5px)
        app.set_manual_crop(width=-10, height=-10, x=5, y=5)

        # Enable every effect
        app.enable_all_effects()

        # Add a caption
        app.add_caption("Hello World")

        # Create GIF with all effects, caption, and crop applied
        status = app.create_gif()
        assert_valid_gif(gif_path_from_status(status))

        # Close the GIF preview dialog
        app.close_preview()

        # Help > Generate Bug Report should open the log file in a text editor (not an error dialog)
        assert os.path.isfile(app.log_path), f"Log file not found at {app.log_path}"
        app.generate_bug_report()


# CLI tests


@requires_test_video
@pytest.mark.parametrize("video", TEST_VIDEOS, ids=os.path.basename)
def disabled_test_cli_creates_gif(video):
    """CLI batch mode produces a valid GIF file from a local video."""
    name = os.path.splitext(os.path.basename(video))[0]
    output_gif = os.path.join(TEST_DIR, f"test_cli_creates_gif_{name}.gif")

    result = InstagifferAutomator.run_cli(video, output_gif)
    assert result.returncode == 0, f"CLI exited with {result.returncode}\nstderr: {result.stderr}"
    assert_valid_gif(output_gif)
