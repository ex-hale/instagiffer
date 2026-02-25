"""
Instagiffer Test Suite

Code quality tests run on all platforms.
GUI regression tests use AppleScript (System Events) and require macOS + Accessibility permissions.

Usage: python3 -m pytest test_instagiffer.py -v
"""

# pylint: disable=redefined-outer-name,unused-argument

import subprocess
import sys
import time
import os
import pytest  # pylint: disable=import-error

requires_macos = pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only (AppleScript)")

# ---------------------------------------------------------------------------
# AppleScript helpers
# ---------------------------------------------------------------------------

PROCESS_NAME = "Python"  # Tkinter apps appear as "Python" to System Events
APP_TITLE = "Instagiffer"
LAUNCH_CMD = ["python3", "main.py"]
STARTUP_TIMEOUT = 10
EVENT_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instagiffer-event.log")


def applescript(script):
    """Run an AppleScript snippet and return stdout. Raises on osascript failure."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"AppleScript error: {result.stderr.strip()}")
    return result.stdout.strip()


def window_exists(title=APP_TITLE):
    """Check if a window whose name contains `title` exists."""
    try:
        out = applescript(f"""
            tell application "System Events"
                tell process "{PROCESS_NAME}"
                    repeat with w in every window
                        if name of w contains "{title}" then return "yes"
                    end repeat
                end tell
            end tell
            return "no"
            """)
        return out == "yes"
    except RuntimeError:
        return False


def wait_for_window(title=APP_TITLE, timeout=STARTUP_TIMEOUT):
    """Block until a window with the given title appears, or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if window_exists(title):
            return True
        time.sleep(0.5)
    return False


def get_window_names():
    """Return list of all window names for our process."""
    out = applescript(f"""
        tell application "System Events"
            tell process "{PROCESS_NAME}"
                return name of every window
            end tell
        end tell
        """)
    return [w.strip() for w in out.split(",") if w.strip()]


def get_window_size(title=APP_TITLE):
    """Return (width, height) of the first window whose name contains `title`."""
    out = applescript(f"""
        tell application "System Events"
            tell process "{PROCESS_NAME}"
                repeat with w in every window
                    if name of w contains "{title}" then
                        set s to size of w
                        return (item 1 of s as text) & "," & (item 2 of s as text)
                    end if
                end repeat
            end tell
        end tell
        error "No window containing '{title}'"
        """)
    w, h = out.split(",")
    return int(w), int(h)




def close_all_dialogs():
    """Close any extra windows/dialogs, leaving only the main window."""
    for _ in range(5):
        names = get_window_names()
        dialogs = [n for n in names if APP_TITLE not in n]
        if not dialogs:
            break
        # Try Escape key first
        applescript(f"""
            tell application "System Events"
                tell process "{PROCESS_NAME}"
                    key code 53
                end tell
            end tell
            """)
        time.sleep(0.3)
        # If Escape didn't work, try clicking the close button
        names = get_window_names()
        dialogs = [n for n in names if APP_TITLE not in n]
        if dialogs:
            try:
                applescript(f"""
                    tell application "System Events"
                        tell process "{PROCESS_NAME}"
                            click button 1 of window "{dialogs[0]}"
                        end tell
                    end tell
                    """)
            except RuntimeError:
                pass
            time.sleep(0.3)


def send_keystroke(key, modifiers=None):
    """Send a keystroke to the app. modifiers: list of 'command down', 'shift down', etc."""
    mod_str = ""
    if modifiers:
        mod_str = " using {" + ", ".join(modifiers) + "}"
    applescript(f"""
        tell application "System Events"
            tell process "{PROCESS_NAME}"
                keystroke "{key}"{mod_str}
            end tell
        end tell
        """)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def app():
    """Launch Instagiffer, wait for it to appear, yield, then kill it."""
    cwd = os.path.dirname(os.path.abspath(__file__))
    proc = subprocess.Popen(LAUNCH_CMD, cwd=cwd)  # pylint: disable=consider-using-with

    if not wait_for_window():
        proc.kill()
        pytest.fail(f"App window '{APP_TITLE}' did not appear within {STARTUP_TIMEOUT}s")

    # Give it a moment to fully render
    time.sleep(1)

    # Close any startup dialogs (e.g. Configure Logo)
    close_all_dialogs()

    yield proc

    # Teardown: kill if still running
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


# ---------------------------------------------------------------------------
# macOS GUI tests
# ---------------------------------------------------------------------------


@requires_macos
def test_01_mac_app_launches(app):
    """App process starts and main window appears."""
    assert app.poll() is None, "App process should still be running"
    assert window_exists(APP_TITLE), f"Window '{APP_TITLE}' should exist"


@requires_macos
def test_02_mac_event_log(app):
    """Event log is created and contains the startup message."""
    assert os.path.exists(EVENT_LOG), f"Event log not found: {EVENT_LOG}"
    log_content = open(EVENT_LOG, encoding="utf-8").read()  # pylint: disable=consider-using-with
    assert "Starting Instagiffer version" in log_content, f"Startup message not found in event log:\n{log_content[:500]}"


@requires_macos
def test_03_mac_window_has_size(app):
    """Main window has non-zero dimensions."""
    w, h = get_window_size(APP_TITLE)
    assert w > 100, f"Window width {w} is too small"
    assert h > 100, f"Window height {h} is too small"


@requires_macos
def test_04_mac_single_main_window(app):
    """Only the main Instagiffer window should be open (no stray dialogs)."""
    names = get_window_names()
    assert len(names) == 1, f"Expected 1 window, got {len(names)}: {names}"
    assert APP_TITLE in names[0]


@requires_macos
def test_05_mac_close_app(app):
    """Quit the app and verify clean exit."""
    try:
        applescript(f"""
            tell application "System Events"
                tell process "{PROCESS_NAME}"
                    click menu item "Quit Python" of menu "{PROCESS_NAME}" of menu bar 1
                end tell
            end tell
            """)
    except RuntimeError:
        # Fallback: send SIGTERM
        app.terminate()

    try:
        app.wait(timeout=5)
    except subprocess.TimeoutExpired:
        app.kill()
        app.wait(timeout=2)

    assert app.poll() is not None, "App process should have exited"
