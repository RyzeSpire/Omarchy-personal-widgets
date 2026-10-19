#!/usr/bin/env python3
"""Open a fresh Codex resume picker in Foot on workspace 7."""
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

APP_ID = "ryze.codex-resume"


def hypr(*args):
    return subprocess.check_output(["hyprctl", *args], text=True, timeout=4)


def codex_executable():
    # Resolve the installed CLI directly, bypassing the personal workspace-9 wrapper.
    mise = shutil.which("mise")
    if mise:
        result = subprocess.run([mise, "which", "codex"], capture_output=True, text=True, timeout=8)
        candidate = result.stdout.strip()
        if result.returncode == 0 and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise ValueError("The mise-managed Codex CLI could not be found.")


def secondary_monitor(monitors):
    active = [m for m in monitors if not m.get("disabled") and m.get("mirrorOf", "none") in (None, "", "none")]
    if len(active) < 2:
        return None
    # Prefer the usual external display, then another non-laptop output.
    external = next((m for m in active if m.get("name") == "HDMI-A-1"), None)
    if external:
        return external["name"]
    internal = next((m for m in active if m.get("name", "").startswith(("eDP", "LVDS", "DSI"))), None)
    primary = internal or min(active, key=lambda m: m.get("id", 0))
    return next(m["name"] for m in active if m is not primary)


def place_window(selector):
    response = hypr("dispatch", 'hl.dsp.window.move({ workspace="7", follow=true, window=' + selector + ' })').strip()
    if response != "ok":
        raise ValueError("Codex opened, but could not be moved to workspace 7.")
    target = secondary_monitor(json.loads(hypr("-j", "monitors")))
    if target:
        workspaces = json.loads(hypr("-j", "workspaces"))
        workspace = next((w for w in workspaces if w.get("id") == 7), None)
        if workspace and workspace.get("monitor") != target:
            response = hypr("dispatch", 'hl.dsp.workspace.move({ workspace="7", monitor=' + json.dumps(target) + ' })').strip()
            if response != "ok":
                raise ValueError("Codex opened on workspace 7, but could not be moved to the secondary monitor.")
    response = hypr("dispatch", 'hl.dsp.focus({ window=' + selector + ' })').strip()
    if response != "ok":
        raise ValueError("Codex opened on workspace 7, but could not be focused.")


def launch():
    terminal = shutil.which("foot")
    if not terminal:
        raise ValueError("The Foot terminal is not installed.")
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", "/run/user/" + str(os.getuid())))
    fd = os.open(runtime / "omarchy-codex-resume.lock", os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        executable = codex_executable()
        existing = {w.get("address") for w in json.loads(hypr("-j", "clients"))}
        directory = Path.home() / "Work"
        if not directory.is_dir():
            directory = Path.home()
        process = subprocess.Popen(
            [terminal, "--app-id=" + APP_ID, "--title=Codex — Resume", "--working-directory=" + str(directory), executable, "resume", "--all"],
            cwd=directory, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            windows = json.loads(hypr("-j", "clients"))
            window = next((w for w in windows if w.get("mapped") and w.get("class") == APP_ID and w.get("address") not in existing), None)
            if window:
                address = window.get("address", "")
                if not re.fullmatch(r"0x[0-9a-fA-F]+", address):
                    raise ValueError("Could not identify the Codex terminal.")
                selector = json.dumps("address:" + address)
                place_window(selector)
                return
            if process.poll() is not None:
                raise ValueError("The Codex terminal exited before it could open.")
            time.sleep(.1)
        raise ValueError("Codex took too long to open. Please try again.")


if __name__ == "__main__":
    try:
        launch()
        print(json.dumps({"ok": True}))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        message = str(error) if isinstance(error, ValueError) else "Could not open Codex on workspace 7."
        print(json.dumps({"ok": False, "error": message}))
        raise SystemExit(1)
