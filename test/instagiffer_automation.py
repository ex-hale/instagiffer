"""
Instagiffer Automation API — macOS GUI automation via AppleScript (System Events).

Usage:
    with InstagifferAutomator.launch() as app:
        app.load_video("https://youtube.com/watch?v=...")
        app.create_gif()
"""

import configparser
import os
import re
import subprocess
import tempfile
import time

_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TEST_DATA_DIR = os.path.join(_PROJECT_DIR, "test", "test_data")


class AutomationError(Exception):
    pass


class AppleScriptError(AutomationError):
    def __init__(self, stderr):
        super().__init__(f"AppleScript error: {stderr}")


class AutomationTimeoutError(AutomationError):
    def __init__(self, operation, timeout):
        super().__init__(f"{operation} timed out after {timeout}s")


class AppNotRunningError(AutomationError):
    pass


def applescript(script, timeout=10):
    """Run an AppleScript snippet via osascript, return stdout."""
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout, check=False)
    if r.returncode != 0:
        raise AppleScriptError(r.stderr.strip())
    return r.stdout.strip()


class InstagifferAutomator:
    """Drive Instagiffer's GUI via macOS System Events."""

    def __init__(self, process=None, process_name="Python", app_title="Instagiffer", launch_cmd=None, working_dir=None, startup_timeout=3.0, poll_interval=0.1):
        self.process = process
        self.process_name = process_name
        self.app_title = app_title
        self.launch_cmd = launch_cmd or ["python3", "main.py"]
        self.working_dir = working_dir or _PROJECT_DIR
        self.startup_timeout = startup_timeout
        self.poll_interval = poll_interval

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.quit()

    def _tell(self, body, timeout=10):
        if self.process and self.process.pid:
            target = f"(first process whose unix id is {self.process.pid})"
        else:
            target = f'process "{self.process_name}"'
        script = f'tell application "System Events"\ntell {target}\n{body}\nend tell\nend tell'
        return applescript(script, timeout=timeout)

    # -- Lifecycle --

    @classmethod
    def launch(cls, config_overrides=None, **kwargs):
        """Launch Instagiffer, wait for the main window, and activate it.

        Pass config_overrides to modify settings from the default config,
        e.g. {"color": {"numColors": "128"}}.
        """
        instance = cls(**kwargs)
        if config_overrides:
            instance._apply_config_overrides(config_overrides)
        instance.process = subprocess.Popen(instance.launch_cmd, cwd=instance.working_dir)
        instance.wait_for_window()
        instance.activate()
        return instance

    @staticmethod
    def run_cli(video, output, timeout=120):
        """Run Instagiffer in CLI batch mode. Returns the CompletedProcess."""
        import sys

        return subprocess.run(
            [sys.executable, "main.py", video, "-o", output],
            cwd=_PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

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

    def terminate(self, timeout=5):
        if self.process is None or self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=2)

    def quit_via_menu(self):
        self._tell(f'click menu item "Quit Python" of menu "{self.process_name}" of menu bar 1')

    def activate(self):
        """Bring the app window to the front."""
        self._tell("set frontmost to true")

    # -- Window queries --

    def window_exists(self, title=None):
        title = title or self.app_title
        try:
            out = self._tell(f'repeat with w in every window\nif name of w contains "{title}" then return "yes"\nend repeat\nreturn "no"', timeout=3)
            return out == "yes"
        except (AppleScriptError, subprocess.TimeoutExpired):
            return False

    def wait_for_window(self, title=None, timeout=None):
        title = title or self.app_title
        timeout = timeout or self.startup_timeout
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.window_exists(title):
                return True
            time.sleep(self.poll_interval)
        raise AutomationTimeoutError(f"wait_for_window('{title}')", timeout)

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

    # -- Dialog management --

    def close_all_dialogs(self, max_attempts=5):
        for _ in range(max_attempts):
            names = self.get_window_names()
            dialogs = [n for n in names if self.app_title not in n]
            if not dialogs:
                break
            self.send_key_code(53)  # Escape
            names = self.get_window_names()
            dialogs = [n for n in names if self.app_title not in n]
            if dialogs:
                try:
                    self._tell(f'click button 1 of window "{dialogs[0]}"')
                except AppleScriptError:
                    pass

    # -- Input --

    def send_keystroke(self, key, modifiers=None):
        mod = (" using {" + ", ".join(modifiers) + "}") if modifiers else ""
        self._tell(f'keystroke "{key}"{mod}')

    def send_key_code(self, code, modifiers=None):
        mod = (" using {" + ", ".join(modifiers) + "}") if modifiers else ""
        self._tell(f"key code {code}{mod}")

    def click_button(self, button_name):
        self._tell(f'click button "{button_name}" of window 1')

    def click_menu(self, *menu_path):
        """Click a menu item by path, e.g. click_menu("File", "Exit")."""
        # Build the navigation chain using AXPress actions, which is more
        # reliable than `click` with Tk 9 (especially after modal dialogs).
        target = f'menu bar item "{menu_path[0]}" of menu bar 1'
        script = f'tell {target}\nperform action "AXPress"\ndelay 0.1\n'
        parent = f'menu "{menu_path[0]}"'
        for level in menu_path[1:-1]:
            script += f'tell {parent}\ntell menu item "{level}"\nperform action "AXPress"\ndelay 0.1\n'
            parent = f'menu "{level}"'
        script += f'tell {parent}\ntell menu item "{menu_path[-1]}"\nperform action "AXPress"\n'
        # Close all the tell blocks
        script += "end tell\n" * (len(menu_path) * 2 - 1)
        self._tell(script)

    def paste_text(self, value):
        """Set clipboard and paste into the focused field (Tk doesn't expose text fields via accessibility)."""
        subprocess.run(["pbcopy"], input=value, text=True, check=True)
        self.send_keystroke("a", ["command down"])  # select all
        self.send_keystroke("v", ["command down"])  # paste

    # -- Observation --

    def get_ui_elements(self):
        out = self._tell(
            'set output to ""\nset elems to entire contents of window 1\nrepeat with e in elems\ntry\nset r to role of e\nset n to ""\ntry\nset n to name of e\nend try\nset output to output & r & "|" & n & linefeed\nend try\nend repeat\nreturn output'
        )
        elements = []
        for line in out.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split("|", 1)
            elements.append({"role": parts[0], "name": parts[1] if len(parts) > 1 else ""})
        return elements

    def screenshot(self, output_path=None):
        if output_path is None:
            output_path = os.path.join(tempfile.gettempdir(), "instagiffer_screenshot.png")
        wid = self._tell(f'repeat with w in every window\nif name of w contains "{self.app_title}" then\nreturn id of w\nend if\nend repeat\nerror "No window found"')
        subprocess.run(["screencapture", "-l", wid, output_path], check=True, timeout=10)
        return output_path

    def read_event_log(self):
        log_path = os.path.join(self.working_dir, "instagiffer-event.log")
        if not os.path.exists(log_path):
            return ""
        with open(log_path, encoding="utf-8") as f:
            return f.read()

    def _log_line_count(self):
        """Return the current number of lines in the event log."""
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
            status = self.get_status(after_line=after_line)
            if substring in status:
                return status
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

    # -- High-level convenience --

    def load_video(self, path_or_url, timeout=30):
        self.activate()
        mark = self._log_line_count()
        self.paste_text(path_or_url)
        self.send_key_code(36)  # Return
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
        self.send_key_code(36)  # Return (Close button has focus)

    def open_effects(self):
        """Open the Filters dialog via Cmd+E."""
        self.activate()
        self.send_keystroke("e", ["command down"])
        self.wait_for_window("Filters")

    def enable_all_effects(self):
        """Open the Filters dialog and enable every effect checkbox via Tab+Space.

        Tab order (matching visual layout, T=Tab, S=Space):
          [dialog opens, chkSharpen already has focus via focus_widget]
          chkSharpen (Enhance, already enabled — skip it)
          T -> spnSharpen, T -> chkDesaturate
          S,T -> spnDesaturate, T -> chkSepia
          S,T -> spnSepia, T -> chkEdgeFade
          S,T -> spnFadedEdge, T -> chkNashville
          S,T -> spnNashville, T -> chkColorTint
          S,T -> spnColorTint, T -> btnTintColor, T -> chkBlurred
          S,T -> spnBlur, T -> chkBorder
          S,T -> spnBorder, T -> btnBorderColor, T -> chkGrayScale
          S,T -> [disabled widgets skipped by Tk] -> btnOK
          Return to close
        """
        self.open_effects()
        self.activate()
        TAB = 48
        SPACE = 49
        # fmt: off
        sequence = [
            TAB, TAB,               # Enhance already focused+enabled, skip it + spinbox -> Color Fade
            SPACE, TAB, TAB,        # Enable Color Fade + skip spinbox -> Sepia
            SPACE, TAB, TAB,        # Enable Sepia + skip spinbox -> Burnt Corners
            SPACE, TAB, TAB,        # Enable Burnt Corners + skip spinbox -> Nashville
            SPACE, TAB, TAB,        # Enable Nashville + skip spinbox -> Colorize
            SPACE, TAB, TAB, TAB,   # Enable Colorize + skip spinbox + skip Color Picker -> Blur
            SPACE, TAB, TAB,        # Enable Blur + skip spinbox -> Border
            SPACE, TAB, TAB, TAB,   # Enable Border + skip spinbox + skip Color Picker -> B&W
            SPACE,                  # Enable Black & White
        ]
        # fmt: on
        for key in sequence:
            self.send_key_code(key)
        # Disabled widgets (Cinemagraph, Sound) are skipped by Tk's tab traversal.
        # Press Return to close (btnOK).
        self.send_key_code(36)  # Return

    def open_caption(self):
        """Open the Caption Configuration dialog via Cmd+T."""
        self.activate()
        self.send_keystroke("t", ["command down"])
        self.wait_for_window("Caption Configuration")

    def add_caption(self, text):
        """Open the Caption dialog, type caption text, and save via Cmd+Return."""
        self.open_caption()
        self.activate()
        self.send_keystroke(text)
        self.send_key_code(36, ["command down"])  # Cmd+Return to save

    def set_manual_crop(self, width=-10, height=-10, x=5, y=5):
        """Open the Manual Crop dialog, adjust crop via spinbox arrows, and close.

        Values are spinbox increments (positive = Up, negative = Down).
        Width and height are adjusted first to shrink the crop area, then
        x/y offsets are nudged to reposition it.

        Tab order (focus starts on spnWidth): spnWidth -> spnHeight -> spnX -> spnY -> btnOK
        """
        self.activate()
        self.send_keystroke("k", ["command down"])  # Cmd+K opens Manual Crop
        self.wait_for_window("Crop Settings")
        self.activate()
        TAB = 48
        UP = 126
        DOWN = 125
        # spnWidth already focused
        for _ in range(abs(width)):
            self.send_key_code(UP if width > 0 else DOWN)
        self.send_key_code(TAB)  # -> spnHeight
        for _ in range(abs(height)):
            self.send_key_code(UP if height > 0 else DOWN)
        self.send_key_code(TAB)  # -> spnX
        for _ in range(abs(x)):
            self.send_key_code(UP if x > 0 else DOWN)
        self.send_key_code(TAB)  # -> spnY
        for _ in range(abs(y)):
            self.send_key_code(UP if y > 0 else DOWN)
        # Return closes the dialog (bound to Done handler)
        self.send_key_code(36)  # Return

    def close_dialog(self):
        """Close the current modal dialog by pressing Return."""
        self.activate()
        self.send_key_code(36)  # Return

    def quit(self, timeout=5):
        """Quit via File > Exit menu and wait for the process to exit."""
        self.activate()
        self.click_menu("File", "Exit")
        if self.process:
            self.process.wait(timeout=timeout)
