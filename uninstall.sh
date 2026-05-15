#!/usr/bin/env bash
set -euo pipefail

LABEL="com.granola.notifier"
SCRIPT_DEST="$HOME/.local/bin/granola_mac_notifier.py"
PLIST_DEST="$HOME/Library/LaunchAgents/${LABEL}.plist"

GREEN='\033[0;32m'; NC='\033[0m'
info() { echo -e "${GREEN}✔${NC}  $*"; }

echo ""
echo "  🎙  Granola Reminder — Uninstaller"
echo ""

launchctl unload "$PLIST_DEST" 2>/dev/null && info "LaunchAgent unloaded" || true
[[ -f "$PLIST_DEST"  ]] && rm "$PLIST_DEST"  && info "Removed plist"
[[ -f "$SCRIPT_DEST" ]] && rm "$SCRIPT_DEST" && info "Removed notifier script"

echo ""
info "Uninstalled. (Logs and queue file kept — delete manually if wanted.)"
echo ""
