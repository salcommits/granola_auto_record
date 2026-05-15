#!/usr/bin/env python3
"""
mac_notifier.py — runs on YOUR MAC as a launchd background agent
──────────────────────────────────────────────────────────────────
Watches the shared queue written by the Hyperagent auto-granola-meeting-recorder.
When a meeting entry appears, opens Granola via its URL scheme and starts
a new recording. Shows a brief banner to confirm.

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
    os.environ.get("GRANOLA_QUEUE_FILE", "~/.granola_queue.json")
)
POLL_INTERVAL = 10
LOG_FILE      = os.path.expanduser("~/Library/Logs/granola_notifier.log")
# ──────────────────────────────────────────────────────────────────────────────

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


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


def banner(title: str, body: str) -> None:
    """Non-blocking macOS notification banner."""
    script = f'display notification "{body}" with title "{title}"'
    subprocess.Popen(["osascript", "-e", script])


def start_granola_recording(title: str) -> None:
    """
    Open Granola and start a new recording via its URL scheme.
    granola://new-document launches a new note and begins recording.
    """
    try:
        subprocess.Popen(["open", "granola://new-document"])
        banner("🎙 Granola", f"Recording started — {title}")
        log.info("started recording: '%s'", title)
    except Exception as exc:
        banner("🎙 Granola", f"Failed to start recording — {title}")
        log.error("failed to start recording for '%s': %s", title, exc)


def main() -> None:
    log.info("mac_notifier started — watching %s", QUEUE_FILE)

    while True:
        try:
            queue   = load_queue()
            changed = False

            for eid, entry in queue.items():
                if not entry.get("done", False):
                    start_granola_recording(entry.get("title", "Meeting"))
                    queue[eid]["done"] = True
                    changed = True

            if changed:
                save_queue(queue)

        except Exception as exc:
            log.error("watcher error: %s", exc, exc_info=True)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
