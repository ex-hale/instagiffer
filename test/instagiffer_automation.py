"""
Instagiffer Automation API — cross-platform GUI automation.

Usage:
    with InstagifferAutomator.launch() as app:
        app.load_video("https://youtube.com/watch?v=...")
        app.create_gif()

InstagifferAutomator is an alias for the current platform's implementation:
  MacInstagifferAutomator     — macOS, uses AppleScript / System Events
  WindowsInstagifferAutomator — Windows, uses pywinauto
"""

import configparser
import os
import re
import subprocess
import sys
import time
from abc import ABC, abstractmethod

_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_DIR)
from instagiffer import GetAppSupportDir, GetLogPath

_TEST_DATA_DIR = os.path.join(_PROJECT_DIR, "test", "test_data")

# Log path for frozen builds; GetLogPath() returns the dev-source path when run unfrozen.
_FROZEN_LOG_PATH = os.path.join(GetAppSupportDir(), "logs", "instagiffer-event.log")

# Mac virtual key codes (also used as keys in _WIN_KEYCODES on Windows)
_KEY_RETURN = 36
_KEY_TAB = 48
_KEY_SPACE = 49
_KEY_ESC = 53
_KEY_DOWN = 125
_KEY_UP = 126


# -- Exceptions --


class AutomationError(Exception):
    pass


class AutomationTimeoutError(AutomationError):
    def __init__(self, operation, timeout):
        super().__init__(f"{operation} timed out after {timeout}s")


# -- Base class --


class _AutomatorBase(ABC):
    """Platform-independent automation: subprocess lifecycle, log-file assertions, and high-level actions."""

    def __init__(self, process=None, app_title="Instagiffer", launch_cmd=None, working_dir=None, log_path=None, startup_timeout=8.0, poll_interval=0.1):
        self.process = process
        self.app_title = app_title
        self.launch_cmd = launch_cmd or self._default_launch_cmd()
        self.working_dir = working_dir or _PROJECT_DIR
        self.log_path = log_path or GetLogPath()
        self.startup_timeout = startup_timeout
        self.poll_interval = poll_interval

    def _default_launch_cmd(self):
        return [sys.executable, "main.py", "--debug"]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.quit()

    # -- Subprocess --

    def terminate(self, timeout=5):
        if self.process is None or self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=2)

    def _apply_config_overrides(self, overrides):
        """Copy the default config, apply overrides, and write to test_data/test.conf."""
        conf = configparser.ConfigParser()
        conf.read(os.path.join(self.working_dir, "instagiffer.conf"))
        for section, values in overrides.items():
            for key, value in values.items():
                conf.set(section, key, str(value))
        os.makedirs(_TEST_DATA_DIR, exist_ok=True)
        test_conf_path = os.path.join(_TEST_DATA_DIR, "test.conf")
        with open(test_conf_path, "w") as f:
            conf.write(f)
        self.launch_cmd = list(self.launch_cmd) + ["--config", test_conf_path]

    @staticmethod
    def run_cli(video, output, timeout=120):
        """Run Instagiffer in CLI batch mode. Returns the CompletedProcess."""
        return subprocess.run(
            [sys.executable, "main.py", video, "-o", output],
            cwd=_PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    # -- Launch --

    @classmethod
    def _setup_frozen(cls, app_path, kwargs):
        """Configure kwargs for a frozen app bundle. Override per platform."""
        kwargs.setdefault("launch_cmd", [app_path])
        kwargs.setdefault("log_path", _FROZEN_LOG_PATH)

    def _post_launch(self):
        """Hook called after wait_for_window(). Override for platform-specific startup."""

    @classmethod
    def launch(cls, app_path=None, config_overrides=None, **kwargs):
        """Launch Instagiffer, wait for the main window, and return the automator.

        Pass app_path to test a frozen build instead of the dev source,
        e.g. app_path="/Applications/Instagiffer.app" or "dist/Instagiffer/Instagiffer.exe".
        Pass config_overrides to modify settings, e.g. {"color": {"numColors": "128"}}.
        """
        if app_path:
            cls._setup_frozen(app_path, kwargs)
        instance = cls(**kwargs)
        if config_overrides:
            instance._apply_config_overrides(config_overrides)
        instance.process = subprocess.Popen(instance.launch_cmd, cwd=instance.working_dir)
        instance.wait_for_window()
        instance._post_launch()
        return instance

    # -- Window management (abstract) --

    @abstractmethod
    def activate(self): ...

    @abstractmethod
    def window_exists(self, title=None): ...

    def wait_for_window(self, title=None, timeout=None):
        title = title or self.app_title
        timeout = timeout or self.startup_timeout
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.window_exists(title):
                return True
            time.sleep(self.poll_interval)
        raise AutomationTimeoutError(f"wait_for_window('{title}')", timeout)

    @abstractmethod
    def get_window_names(self): ...

    @abstractmethod
    def get_window_size(self, title=None): ...

    # -- Input (abstract) --

    @abstractmethod
    def send_keystroke(self, key, modifiers=None): ...

    @abstractmethod
    def send_key_code(self, code, modifiers=None): ...

    @abstractmethod
    def paste_text(self, value): ...

    @abstractmethod
    def click_menu(self, *menu_path): ...

    def quit(self, timeout=5):
        """Quit via File > Exit menu and wait for the process to exit."""
        try:
            self.click_menu("File", "Exit")
        except Exception:
            pass
        if self.process:
            try:
                self.process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.terminate()

    # -- Log observation --

    def read_event_log(self):
        if not os.path.exists(self.log_path):
            return ""
        with open(self.log_path, encoding="utf-8") as f:
            return f.read()

    def _log_line_count(self):
        log = self.read_event_log()
        return len(log.splitlines()) if log else 0

    def get_status(self, after_line=0):
        """Return the most recent SetStatus message from the event log."""
        log = self.read_event_log()
        last = ""
        for i, line in enumerate(log.splitlines()):
            if i >= after_line and "SetStatus:" in line:
                last = line.split("SetStatus:", 1)[1].strip().strip("'")
        return last

    def wait_for_status(self, substring, timeout=30, after_line=0):
        """Poll the status bar (via log) until it contains the given substring."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if substring in self.get_status(after_line=after_line):
                return self.get_status(after_line=after_line)
            time.sleep(self.poll_interval)
        raise AutomationTimeoutError(f"wait_for_status('{substring}')", timeout)

    def get_log_lines(self, pattern, after_line=0):
        """Return all log lines matching a regex pattern (searched after after_line)."""
        log = self.read_event_log()
        return [line for i, line in enumerate(log.splitlines()) if i >= after_line and re.search(pattern, line)]

    def assert_log_contains(self, pattern, after_line=0):
        """Assert at least one log line matches the regex pattern."""
        matches = self.get_log_lines(pattern, after_line=after_line)
        assert matches, f"No log line matching /{pattern}/ (after line {after_line})"
        return matches

    def assert_log_not_contains(self, pattern, after_line=0):
        """Assert no log lines match the regex pattern."""
        matches = self.get_log_lines(pattern, after_line=after_line)
        assert not matches, f"Unexpected log line matching /{pattern}/: {matches[0]}"

    def wait_for_log(self, pattern, timeout=30, after_line=0):
        """Poll the log until a line matching the regex pattern appears."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            matches = self.get_log_lines(pattern, after_line=after_line)
            if matches:
                return matches[-1]
            time.sleep(self.poll_interval)
        raise AutomationTimeoutError(f"wait_for_log('{pattern}')", timeout)

    # -- High-level actions --

    def load_video(self, path_or_url, timeout=30):
        self.activate()
        mark = self._log_line_count()
        self.paste_text(path_or_url)
        self.send_key_code(_KEY_RETURN)
        return self.wait_for_status("Video loaded", timeout=timeout, after_line=mark)

    def create_gif(self, timeout=120):
        self.activate()
        mark = self._log_line_count()
        self.send_keystroke("g", ["command down"])
        return self.wait_for_status("GIF saved", timeout=timeout, after_line=mark)

    def close_preview(self, timeout=10):
        """Close the GIF preview dialog by waiting for it and pressing Return."""
        self.wait_for_window("GIF Preview", timeout=timeout)
        self.activate()
        self.send_key_code(_KEY_RETURN)

    def open_effects(self):
        """Open the Filters dialog via Cmd+E (Ctrl+E on Windows)."""
        self.activate()
        self.send_keystroke("e", ["command down"])
        self.wait_for_window("Filters")

    def enable_all_effects(self):
        """Enable every effect checkbox in the Filters dialog via Tab+Space navigation.

        Tab order (T=Tab, S=Space; chkSharpen focused on open):
          T,T→Color Fade; S,T,T→Sepia; S,T,T→Burnt Corners; S,T,T→Nashville
          S,T,T→Colorize; S,T,T,T→Blur; S,T,T→Border; S,T,T,T→B&W; S→Return
        """
        self.open_effects()
        self.activate()
        S, T = _KEY_SPACE, _KEY_TAB
        # fmt: off
        for key in [T,T, S,T,T, S,T,T, S,T,T, S,T,T, S,T,T,T, S,T,T, S,T,T,T, S]:
            self.send_key_code(key)
        # fmt: on
        self.send_key_code(_KEY_RETURN)

    def open_caption(self):
        """Open the Caption Configuration dialog via Cmd+T (Ctrl+T on Windows)."""
        self.activate()
        self.send_keystroke("t", ["command down"])
        self.wait_for_window("Caption Configuration")

    def add_caption(self, text):
        """Open the Caption dialog, type caption text, and save via Cmd+Return."""
        self.open_caption()
        self.activate()
        self.send_keystroke(text)
        self.send_key_code(_KEY_RETURN, ["command down"])

    def set_manual_crop(self, width=-10, height=-10, x=5, y=5):
        """Adjust the Manual Crop dialog spinboxes (Width→Height→X→Y) via arrow keys, then confirm."""
        self.activate()
        self.send_keystroke("k", ["command down"])
        self.wait_for_window("Crop")
        self.activate()
        for i, val in enumerate((width, height, x, y)):
            for _ in range(abs(val)):
                self.send_key_code(_KEY_UP if val > 0 else _KEY_DOWN)
            self.send_key_code(_KEY_TAB if i < 3 else _KEY_RETURN)

    def generate_bug_report(self):
        """Click Help > Generate Bug Report and assert no error dialog appeared."""
        self.click_menu("Help", "Generate Bug Report")
        # Failure mode is a "Bug Report is empty" info dialog
        deadline = time.time() + 2
        while time.time() < deadline:
            assert not any("Bug Report" in n for n in self.get_window_names()), "Bug Report error dialog appeared"
            time.sleep(self.poll_interval)


# -- macOS: AppleScript / System Events --


class AppleScriptError(AutomationError):
    def __init__(self, stderr):
        super().__init__(f"AppleScript error: {stderr}")


def applescript(script, timeout=10):
    """Run an AppleScript snippet via osascript, return stdout."""
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout, check=False)
    if r.returncode != 0:
        raise AppleScriptError(r.stderr.strip())
    return r.stdout.strip()


class MacInstagifferAutomator(_AutomatorBase):
    """Drive Instagiffer's GUI via macOS System Events."""

    def __init__(self, process_name="Python", **kwargs):
        super().__init__(**kwargs)
        self.process_name = process_name

    def _tell(self, body, timeout=10):
        if self.process and self.process.pid:
            target = f"(first process whose unix id is {self.process.pid})"
        else:
            target = f'process "{self.process_name}"'
        script = f'tell application "System Events"\ntell {target}\n{body}\nend tell\nend tell'
        return applescript(script, timeout=timeout)

    @classmethod
    def _setup_frozen(cls, app_path, kwargs):
        binary = os.path.join(app_path, "Contents", "MacOS", "Instagiffer")
        kwargs.setdefault("process_name", "Instagiffer")
        kwargs.setdefault("launch_cmd", [binary])
        kwargs.setdefault("log_path", _FROZEN_LOG_PATH)

    def _post_launch(self):
        self.activate()

    def activate(self):
        self._tell("set frontmost to true")

    def window_exists(self, title=None):
        title = title or self.app_title
        try:
            out = self._tell(f'repeat with w in every window\nif name of w contains "{title}" then return "yes"\nend repeat\nreturn "no"', timeout=3)
            return out == "yes"
        except (AppleScriptError, subprocess.TimeoutExpired):
            return False

    def get_window_names(self):
        out = self._tell("return name of every window")
        return [w.strip() for w in out.split(",") if w.strip()]

    def get_window_size(self, title=None):
        title = title or self.app_title
        out = self._tell(
            f'repeat with w in every window\nif name of w contains "{title}" then\nset s to size of w\nreturn (item 1 of s as text) & "," & (item 2 of s as text)\nend if\nend repeat\nerror "No window containing \'{title}\'"'
        )
        w, h = out.split(",")
        return int(w), int(h)

    def send_keystroke(self, key, modifiers=None):
        mod = (" using {" + ", ".join(modifiers) + "}") if modifiers else ""
        self._tell(f'keystroke "{key}"{mod}')

    def send_key_code(self, code, modifiers=None):
        mod = (" using {" + ", ".join(modifiers) + "}") if modifiers else ""
        self._tell(f"key code {code}{mod}")

    def paste_text(self, value):
        """Set clipboard and paste into the focused field."""
        subprocess.run(["pbcopy"], input=value, text=True, check=True)
        self.send_keystroke("a", ["command down"])
        self.send_keystroke("v", ["command down"])

    def click_menu(self, *menu_path):
        """Click a menu item by path, e.g. click_menu("File", "Exit")."""
        target = f'menu bar item "{menu_path[0]}" of menu bar 1'
        script = f'tell {target}\nperform action "AXPress"\ndelay 0.1\n'
        parent = f'menu "{menu_path[0]}"'
        for level in menu_path[1:-1]:
            script += f'tell {parent}\ntell menu item "{level}"\nperform action "AXPress"\ndelay 0.1\n'
            parent = f'menu "{level}"'
        script += f'tell {parent}\ntell menu item "{menu_path[-1]}"\nperform action "AXPress"\n'
        script += "end tell\n" * (len(menu_path) * 2 - 1)
        self._tell(script)


# -- Windows: pywinauto --

# Map Mac key codes → pywinauto send_keys sequences
_WIN_KEYCODES = {
    _KEY_RETURN: "{ENTER}",
    _KEY_TAB: "{TAB}",
    _KEY_SPACE: "{VK_SPACE}",  # literal " " sends KEYEVENTF_UNICODE → Tk keysym='??', binding never fires
    _KEY_ESC: "{ESC}",
    _KEY_DOWN: "{DOWN}",
    _KEY_UP: "{UP}",
}

# Map Mac modifier names → pywinauto send_keys prefixes
_WIN_MODIFIERS = {
    "command down": "^",  # Command → Ctrl
    "shift down": "+",
    "option down": "%",  # Option → Alt
}

# send_keys special characters that must be escaped with {}
_SEND_KEYS_SPECIAL = set("^+%~{}()")


class WindowsInstagifferAutomator(_AutomatorBase):
    """Drive Instagiffer's GUI via pywinauto on Windows."""

    @property
    def _desktop(self):
        from pywinauto import Desktop

        return Desktop(backend="win32")

    def _post_launch(self):
        self.wait_for_log("Instagiffer main window has been created", timeout=10)  # wait for full __init__
        self._force_foreground()  # minimize+restore bypasses Windows focus-stealing block
        self._wait_for_window_size(min_width=400, timeout=5)  # Tk re-draws asynchronously after restore

    def _main_window(self):
        """Return the main application window, excluding transient dialogs like 'GIF Preview'."""
        for win in self._desktop.windows():
            title = win.window_text()
            if title.startswith(self.app_title) and "GIF Preview" not in title:
                return win
        raise AutomationError(f"Main window starting with '{self.app_title}' not found; windows={self.get_window_names()}")

    # -- Window management --

    def _topmost_app_window(self):
        """Return the topmost visible window belonging to our app process.

        subprocess.Popen.pid is unreliable under Git Bash (intermediate wrapper), so we find
        the real PID via the main window title, then walk Desktop.windows() in Z-order.
        Application.top_window() is not used because it omits Tk Toplevel dialogs.
        """
        import win32gui
        import win32process

        all_desktop = self._desktop.windows()

        actual_pid = None
        for win in all_desktop:
            try:
                if win.window_text().startswith(self.app_title):
                    _, actual_pid = win32process.GetWindowThreadProcessId(win.handle)
                    break
            except Exception:
                pass

        if actual_pid is None:
            return None

        app_hwnds = set()

        def _enum_cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    _, wpid = win32process.GetWindowThreadProcessId(hwnd)
                    if wpid == actual_pid:
                        app_hwnds.add(hwnd)
                except Exception:
                    pass

        win32gui.EnumWindows(_enum_cb, None)

        for win in all_desktop:
            try:
                if not win.is_visible() or not win.window_text():
                    continue
                if win.handle not in app_hwnds:
                    continue
                rect = win.rectangle()
                if rect.width() >= 100 and rect.height() >= 50:
                    return win
            except Exception:
                continue
        return None

    def _force_foreground(self):
        """Minimize+restore to bring the window to foreground (bypasses Windows focus-stealing block)."""
        try:
            win = self._topmost_app_window()
            if win is None:
                return
            if not win.is_minimized():
                win.minimize()
            win.restore()
        except Exception as e:
            print(f"[automation] _force_foreground: {e}")

    def _wait_for_window_size(self, min_width=400, timeout=5):
        """Poll until the main window is at least min_width px wide (Tk re-draws asynchronously after restore)."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                w, _ = self.get_window_size()
                if w >= min_width:
                    return
            except Exception:
                pass
            time.sleep(self.poll_interval)
        print(f"[automation] _wait_for_window_size: window never reached {min_width}px wide")

    def activate(self):
        """Focus the topmost visible app window (dialog or main).

        Uses Desktop.windows() not Application.top_window(), which omits Tk Toplevel dialogs.
        """
        try:
            win = self._topmost_app_window()
            if win is None:
                return
            if win.is_minimized():
                win.restore()
            win.set_focus()
        except Exception as e:
            print(f"[automation] activate: {e}")

    def open_effects(self):
        """Open the Filters dialog, then explicitly set focus so Tk settles on chkSharpen.

        On Windows, Win32 and Tk's internal focus can briefly be out of sync after a Toplevel
        appears; set_focus() + 300ms sleep lets Tk restore focus before we send keystrokes.
        """
        super().open_effects()
        wins = [w for w in self._desktop.windows() if "Filters" in w.window_text()]
        if not wins:
            raise AutomationError("Filters window not found after open_effects()")
        wins[0].set_focus()
        time.sleep(0.3)  # let Tk restore internal widget focus to chkSharpen

    def window_exists(self, title=None):
        title = title or self.app_title
        try:
            return bool(self._desktop.windows(title_re=f".*{title}.*"))
        except Exception:
            return False

    def get_window_names(self):
        return [w.window_text() for w in self._desktop.windows() if w.window_text()]

    def get_window_size(self, title=None):
        title = title or self.app_title
        for w in self._desktop.windows():
            if title in w.window_text():
                r = w.rectangle()
                return r.width(), r.height()
        raise AutomationError(f"Window containing '{title}' not found")

    # -- Input --

    def send_keystroke(self, key, modifiers=None):
        from pywinauto.keyboard import send_keys

        prefix = "".join(_WIN_MODIFIERS.get(m, "") for m in (modifiers or []))
        if prefix:
            send_keys(f"{prefix}{key}")
        else:
            # Typing plain text — escape send_keys special characters
            escaped = "".join(f"{{{c}}}" if c in _SEND_KEYS_SPECIAL else c for c in key)
            send_keys(escaped, with_spaces=True)

    def send_key_code(self, code, modifiers=None):
        from pywinauto.keyboard import send_keys

        key = _WIN_KEYCODES[code]
        prefix = "".join(_WIN_MODIFIERS.get(m, "") for m in (modifiers or []))
        send_keys(f"{prefix}{key}", with_spaces=True)

    def paste_text(self, value):
        import pyperclip
        from pywinauto.keyboard import send_keys

        self.activate()
        pyperclip.copy(value)
        send_keys("^a^v")

    def close_preview(self, timeout=10):
        """Close the GIF preview dialog by sending Enter directly to its window handle."""
        self.wait_for_window("GIF Preview", timeout=timeout)
        try:
            dlg_list = [w for w in self._desktop.windows() if "GIF Preview" in w.window_text()]
            if not dlg_list:
                raise AutomationError("GIF Preview window not found via Desktop")
            dlg_list[0].set_focus()
            dlg_list[0].type_keys("{ENTER}")
        except AutomationError:
            raise
        except Exception as e:
            print(f"[automation] close_preview: type_keys failed ({e}), falling back to global send_keys")
            from pywinauto.keyboard import send_keys

            send_keys("{ENTER}", with_spaces=True)
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self.window_exists("GIF Preview"):
                time.sleep(0.5)  # buffer for Tk to settle and re-raise main window
                return
            time.sleep(self.poll_interval)
        print("[automation] close_preview: timed out waiting for GIF Preview to close")

    def click_menu(self, *menu_path):
        """Navigate a menu via keyboard (Tk menus are owner-drawn; menu_select() cannot read them).

        Alt + first char opens the top-level menu (all menus use underline=0), then the first
        char of each item selects it.
        """
        from pywinauto.keyboard import send_keys

        try:
            self._main_window().set_focus()
        except Exception as e:
            print(f"[automation] click_menu: set_focus failed: {e}")
        time.sleep(0.1)
        send_keys(f"%{menu_path[0][0].lower()}")
        time.sleep(0.15)
        for item in menu_path[1:]:
            send_keys(item[0].lower(), with_spaces=True)
            time.sleep(0.1)

    def generate_bug_report(self, timeout=8):
        """Click Help > Generate Bug Report, assert no error dialog, then close the text editor."""
        from pywinauto.keyboard import send_keys

        before_handles = {w.handle for w in self._desktop.windows()}
        super().generate_bug_report()

        log_stem = os.path.splitext(os.path.basename(self.log_path))[0]
        deadline = time.time() + timeout
        editor_win = None
        while time.time() < deadline and not editor_win:
            for w in self._desktop.windows():
                try:
                    t = w.window_text()
                    if w.handle not in before_handles and w.is_visible() and (log_stem in t or "Notepad" in t):
                        editor_win = w
                        break
                except Exception:
                    pass
            time.sleep(self.poll_interval)

        if editor_win:
            try:
                editor_win.set_focus()
                send_keys("%{F4}")
            except Exception as e:
                print(f"[automation] generate_bug_report: failed to close editor: {e}")
        else:
            print("[automation] generate_bug_report: no editor window found to close")


InstagifferAutomator = WindowsInstagifferAutomator if sys.platform == "win32" else MacInstagifferAutomator
