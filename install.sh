#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  auto-granola-meeting-recorder — Mac-side installer
#
#  Works two ways:
#    1. curl install (recommended):
#       curl -fsSL https://raw.githubusercontent.com/YOUR_USER/auto-granola-meeting-recorder/main/install.sh | bash
#
#    2. Local install (clone the repo first):
#       chmod +x install.sh && ./install.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

GITHUB_RAW="https://raw.githubusercontent.com/YOUR_USER/auto-granola-meeting-recorder/main"
LABEL="com.granola.notifier"
SCRIPT_DEST="$HOME/.local/bin/granola_mac_notifier.py"
PLIST_DEST="$HOME/Library/LaunchAgents/${LABEL}.plist"
QUEUE_FILE="$HOME/.granola_queue.json"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${GREEN}✔${NC}  $*"; }
warn()    { echo -e "${YELLOW}⚠${NC}  $*"; }
failure() { echo -e "${RED}✘  $*${NC}"; exit 1; }

echo ""
echo "  🎙  auto-granola-meeting-recorder"
echo "  ───────────────────────────────────"
echo ""

# ── Checks ────────────────────────────────────────────────────────────────────
[[ "$(uname)" == "Darwin" ]] || failure "macOS only."

PYTHON=$(command -v python3 2>/dev/null || true)
[[ -n "$PYTHON" ]] || failure "python3 not found. Install it from python.org or run: brew install python3"
info "Python: $PYTHON"

if [[ ! -d "/Applications/Granola.app" ]]; then
    warn "Granola.app not found in /Applications — install Granola first."
    warn "https://www.granola.ai"
    exit 1
fi
info "Granola.app found"

# ── Download mac_notifier.py ──────────────────────────────────────────────────
mkdir -p "$(dirname "$SCRIPT_DEST")"

# If running via curl, download from GitHub. If local, copy from next to install.sh.
LOCAL_NOTIFIER="$(cd "$(dirname "${BASH_SOURCE[0]:-}")" 2>/dev/null && pwd)/mac_notifier.py"

if [[ -f "$LOCAL_NOTIFIER" ]]; then
    cp "$LOCAL_NOTIFIER" "$SCRIPT_DEST"
    info "Copied mac_notifier.py from local repo"
else
    curl -fsSL "$GITHUB_RAW/mac_notifier.py" -o "$SCRIPT_DEST" \
        || failure "Could not download mac_notifier.py from GitHub"
    info "Downloaded mac_notifier.py"
fi

chmod +x "$SCRIPT_DEST"

# ── Write launchd plist ───────────────────────────────────────────────────────
mkdir -p "$(dirname "$PLIST_DEST")"

cat > "$PLIST_DEST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON}</string>
        <string>${SCRIPT_DEST}</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
        <key>GRANOLA_QUEUE_FILE</key>
        <string>${QUEUE_FILE}</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ProcessType</key>
    <string>Interactive</string>

    <key>StandardOutPath</key>
    <string>${HOME}/Library/Logs/granola_notifier.log</string>
    <key>StandardErrorPath</key>
    <string>${HOME}/Library/Logs/granola_notifier.log</string>
</dict>
</plist>
PLIST

info "LaunchAgent configured"

# ── Load the agent ────────────────────────────────────────────────────────────
launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"
info "Mac notifier running in the background"

# ── Grant Accessibility permission nudge ──────────────────────────────────────
echo ""
echo "  ─────────────────────────────────────────────────────────────"
echo "  ⚠️   One permission required (one-time)"
echo ""
echo "  System Settings → Privacy & Security → Accessibility"
echo "  → enable Terminal (or whichever app you ran this from)"
echo ""
echo "  This lets the notifier auto-click Record in Granola."
echo "  ─────────────────────────────────────────────────────────────"
echo ""
info "Setup complete. Granola will start recording automatically. 🎙"
echo ""
