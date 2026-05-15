#!/usr/bin/env python3
"""
hyperagent_scanner.py — runs INSIDE Hyperagent's container
────────────────────────────────────────────────────────────
Polls your Google Calendar iCal feed. When a meeting is starting,
writes an entry to a shared queue file. The Mac-side agent
(mac_notifier.py) reads that file and auto-starts Granola recording.

SETUP (one-time, in Hyperagent):
  pip install icalendar requests

  export ICAL_URL='https://calendar.google.com/calendar/ical/...'
  python3 hyperagent_scanner.py

Get your iCal URL:
  calendar.google.com → Settings → [your calendar]
  → "Secret address in iCal format"
"""

import json
import time
import hashlib
import logging
import sys
import os
from datetime import datetime, timezone, timedelta

import requests
from icalendar import Calendar

# ── Config ─────────────────────────────────────────────────────────────────────
ICAL_URL      = os.environ.get("ICAL_URL", "")
LOOKAHEAD_MIN = 2      # queue events this many minutes before they start
POLL_INTERVAL = 30     # seconds between calendar fetches
QUEUE_FILE    = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    ".notification_queue.json",
)
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def fetch_starting_soon(ical_url: str, lookahead_min: int) -> list[dict]:
    """Return events whose start time is within the next `lookahead_min` minutes."""
    try:
        resp = requests.get(ical_url, timeout=15)
        resp.raise_for_status()
    except Exception as exc:
        log.warning("iCal fetch failed: %s", exc)
        return []

    cal = Calendar.from_ical(resp.content)
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(minutes=lookahead_min)

    events = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        dtstart = component.get("DTSTART")
        if dtstart is None:
            continue
        start = dtstart.dt
        if isinstance(start, datetime):
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
        else:
            start = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)

        if now <= start <= window_end:
            events.append({
                "title":    str(component.get("SUMMARY", "Untitled meeting")),
                "start":    start.isoformat(),
                "start_ts": start.timestamp(),
            })
    return events


def event_id(event: dict) -> str:
    return hashlib.sha1(f"{event['title']}::{event['start']}".encode()).hexdigest()[:12]


def load_queue() -> dict:
    try:
        with open(QUEUE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_queue(queue: dict) -> None:
    tmp = QUEUE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(queue, f, indent=2)
    os.replace(tmp, QUEUE_FILE)


def main() -> None:
    if not ICAL_URL:
        print("\n  ERROR: ICAL_URL not set.")
        print("  export ICAL_URL='https://calendar.google.com/calendar/ical/...'")
        sys.exit(1)

    log.info("scanner started — polling every %ds, lookahead %d min", POLL_INTERVAL, LOOKAHEAD_MIN)

    while True:
        try:
            events  = fetch_starting_soon(ICAL_URL, LOOKAHEAD_MIN)
            queue   = load_queue()
            now_ts  = time.time()
            changed = False

            for event in events:
                eid = event_id(event)
                if eid not in queue:
                    queue[eid] = {
                        **event,
                        "queued_at": now_ts,
                        "done":      False,
                    }
                    log.info("queued: %s at %s", event["title"], event["start"])
                    changed = True

            # Prune entries older than 2 hours
            queue = {k: v for k, v in queue.items()
                     if now_ts - v.get("queued_at", 0) < 7200}

            if changed:
                save_queue(queue)

        except Exception as exc:
            log.error("poll error: %s", exc, exc_info=True)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
