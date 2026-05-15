#!/usr/bin/env python3
"""
calibrate.py — run this ONCE on your Mac with Granola open
────────────────────────────────────────────────────────────
Prints Granola's full accessibility tree (buttons, titles, descriptions)
so you can confirm the auto-click in mac_notifier.py will hit the right target.

Usage:
  python3 calibrate.py

Make sure:
  1. Granola is open and showing the recording interface
  2. System Preferences → Privacy & Security → Accessibility
     has Terminal (or your Python) ticked
"""

import subprocess

SCRIPT = """
set output to "=== Granola Accessibility Inspector ===" & linefeed

tell application "System Events"
    tell process "Granola"

        -- Windows
        set output to output & linefeed & "── Windows ──────────────────────────" & linefeed
        repeat with w in windows
            set output to output & "  Window: " & name of w & linefeed
            repeat with btn in (every button of w)
                set t to ""
                try
                    set t to title of btn
                end try
                set d to ""
                try
                    set d to description of btn
                end try
                set output to output & "    Button  title=" & t & "  desc=" & d & linefeed
            end repeat
        end repeat

        -- Menu bar extra (status item)
        set output to output & linefeed & "── Menu bar items ───────────────────" & linefeed
        try
            repeat with mb in menu bar items of menu bar 2
                set output to output & "  StatusItem: " & title of mb & linefeed
            end repeat
        end try

    end tell
end tell

return output
"""

result = subprocess.run(["osascript", "-e", SCRIPT],
                        capture_output=True, text=True, timeout=15)

if result.returncode != 0:
    print("ERROR:", result.stderr.strip())
    print()
    print("→ Make sure Granola is open and Accessibility permission is granted.")
    print("  System Settings → Privacy & Security → Accessibility → enable Terminal")
else:
    print(result.stdout.strip())
    print()
    print("─────────────────────────────────────────────────────────")
    print("If you see a Record button above, mac_notifier.py should  ")
    print("auto-click it. If the title is different (e.g. 'Start'),  ")
    print("update the string in _try_click_record_via_accessibility()")
    print("in mac_notifier.py to match.")
