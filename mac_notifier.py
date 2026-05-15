#!/usr/bin/env python3
"""
mac_notifier.py — runs on YOUR MAC as a launchd background agent
──────────────────────────────────────────────────────────────────
Watches the shared queue written by hyperagent_scanner.py.
When a meeting appears, opens Granola and auto-clicks Record.
Shows a brief banner to confirm — no dialogs, nothing to dismiss.

install.sh sets this up to run automatically at login.
"""

import json
import time
import subprocess
import logging
import sys
import os

# ── Config ─────────────────────────────────────────────────────────────────────
QUEUE_FILE    = os.path.expanduser(
    os.environ.get("GRANOLA_QUEUE_FILE",
                   "~/AirLoop/granola_reminder/.notification_queue.json")
)
POLL_INTERVAL = 10
GRANOLA_APP   = "Granola"
LOG_FILE      = os.path.expanduser("~/Library/Logs/granola_notifier.log")
# ──────────────────────────────────────────────────────────────────────────────

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_queue() -> dict:
    try:
        with open(QUEUE_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        log.warning("Queue file malformed — skipping cycle")
        return {}


def save_queue(queue: dict) -> None:
    tmp = QUEUE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(queue, f, indent=2)
    os.replace(tmp, QUEUE_FILE)


def is_granola_running() -> bool:
    return subprocess.run(["pgrep", "-x", GRANOLA_APP], capture_output=True).returncode == 0


def open_granola(wait: int = 3) -> None:
    if not is_granola_running():
        log.info("launching Granola…")
        subprocess.Popen(["open", "-a", GRANOLA_APP])
        time.sleep(wait)
    else:
        subprocess.Popen(["open", "-a", GRANOLA_APP])  # bring to front
        time.sleep(1)


def banner(title: str, body: str) -> None:
    """Non-blocking macOS notification banner."""
    script = f'display notification "{body}" with title "{title}"'
    subprocess.Popen(["osascript", "-e", script])


# ── Recording automation (three approaches, first success wins) ────────────────

def try_accessibility_click() -> bool:
    """Walk every button in every Granola window, click anything named 'Record'."""
    script = """
    tell application "System Events"
        tell process "Granola"
            repeat with w in windows
                repeat with btn in (every button of w)
                    set t to ""
                    try
                        set t to title of btn
                    end try
                    set d to ""
                    try
                        set d to description of btn
                    end try
                    if (t contains "ecord") or (d contains "ecord") then
                        click btn
                        return "ok:" & t
                    end if
                end repeat
            end repeat
        end tell
    end tell
    return "not_found"
    """
    try:
        r = subprocess.run(["osascript", "-e", script],
                           capture_output=True, text=True, timeout=8)
        out = r.stdout.strip()
        if out.startswith("ok:"):
            log.info("accessibility click → %s", out)
            return True
    except Exception as exc:
        log.debug("accessibility attempt: %s", exc)
    return False


def try_menubar_click() -> bool:
    """Open Granola's menu-bar popover, look for Record inside."""
    script = """
    tell application "System Events"
        tell process "Granola"
            try
                click menu bar item 1 of menu bar 2
                delay 0.8
            end try
            repeat with w in windows
                repeat with btn in (every button of w)
                    set t to ""
                    try
                        set t to title of btn
                    end try
                    if t contains "ecord" then
                        click btn
                        return "ok:" & t
                    end if
                end repeat
            end repeat
        end tell
    end tell
    return "not_found"
    """
    try:
        r = subprocess.run(["osascript", "-e", script],
                           capture_output=True, text=True, timeout=10)
        out = r.stdout.strip()
        if out.startswith("ok:"):
            log.info("menubar click → %s", out)
            return True
    except Exception as exc:
        log.debug("menubar attempt: %s", exc)
    return False


def try_keyboard_shortcut() -> bool:
    """Send ⌘R — Granola's most likely recording shortcut."""
    script = """
    tell application "System Events"
        tell process "Granola"
            keystroke "r" using {command down}
        end tell
    end tell
    """
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
        log.info("sent ⌘R to Granola")
        return True
    except Exception as exc:
        log.debug("keystroke attempt: %s", exc)
    return False


def autostart_recording(title: str) -> None:
    open_granola(wait=3)

    success = (
        try_accessibility_click() or
        try_menubar_click()        or
        try_keyboard_shortcut()
    )

    if success:
        banner("🎙 Granola", f"Recording started — {title}")
        log.info("recording started: '%s'", title)
    else:
        banner("🎙 Granola", f"Couldn't auto-click Record — tap it manually\n{title}")
        log.warning("all automation attempts failed for '%s' — run calibrate.py", title)


# ── Main loop ──────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("mac_notifier started — watching %s", QUEUE_FILE)

    while True:
        try:
            queue   = load_queue()
            changed = False

            for eid, entry in queue.items():
                if not entry.get("done", False):
                    autostart_recording(entry.get("title", "Meeting"))
                    queue[eid]["done"] = True
                    changed = True

            if changed:
                save_queue(queue)

        except Exception as exc:
            log.error("watcher error: %s", exc, exc_info=True)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
