#!/bin/bash
#
# MtG Goldfish Simulator — one-click installer for macOS.
#
# Double-click this file in Finder. It installs the small "uv" tool (which
# fetches the right Python and every dependency for you) and downloads
# everything the simulator needs. You only need to run this once.
#
# The very first time, macOS may say the file is "from an unidentified
# developer". If so: right-click this file, choose "Open", then "Open" again.
#
set -e

# Always work from the project folder, wherever this script was launched from.
cd "$(dirname "$0")"

# uv installs itself into one of these; make sure they are on PATH.
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

echo "=================================================="
echo "  Installing the MtG Goldfish Simulator"
echo "=================================================="
echo ""

# ---------------------------------------------------------------- step 1: uv
if command -v uv >/dev/null 2>&1; then
  echo "==> uv is already installed ($(uv --version)). Skipping."
else
  echo "==> Installing uv (this fetches Python + dependencies for you)…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if ! command -v uv >/dev/null 2>&1; then
  echo ""
  echo "❌ Could not find 'uv' after installing it."
  echo "   Please close this window, open a new Terminal, and run this installer again."
  echo ""
  read -n 1 -s -r -p "Press any key to close this window."
  exit 1
fi

# --------------------------------------------- step 2: Python + dependencies
echo ""
echo "==> Downloading Python and all dependencies…"
echo "    (The first time this can take a minute or two — please be patient.)"
echo ""
uv sync

# ---------------------------------------------- step 3: menu entry (an .app)
# A tiny app bundle so you can launch the simulator from Launchpad / Spotlight
# (Cmd-Space → "MtG Goldfish") without hunting for this folder. It just starts
# the server and opens your browser; the server quits itself when you close the
# last tab.
echo ""
echo "==> Creating a menu entry (Launchpad / Spotlight)…"
PROJECT_DIR="$(pwd)"
APP_DIR="$HOME/Applications/MtG Goldfish Simulator.app"
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/Contents/MacOS"
cat > "$APP_DIR/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>MtG Goldfish Simulator</string>
  <key>CFBundleDisplayName</key><string>MtG Goldfish Simulator</string>
  <key>CFBundleIdentifier</key><string>com.mtggoldfish.simulator</string>
  <key>CFBundleExecutable</key><string>launcher</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>LSUIElement</key><true/>
</dict></plist>
PLIST
cat > "$APP_DIR/Contents/MacOS/launcher" <<LAUNCHER
#!/bin/bash
exec "$PROJECT_DIR/launch-macos.command"
LAUNCHER
chmod +x "$APP_DIR/Contents/MacOS/launcher"
# Refresh Launchpad/Spotlight so the new app is found immediately.
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP_DIR" 2>/dev/null || true

echo ""
echo "=================================================="
echo "  ✅  All done!"
echo "=================================================="
echo ""
echo "  Launch it from Launchpad or Spotlight (Cmd-Space):"
echo "      MtG Goldfish Simulator"
echo "  …or double-click:  launch-macos.command"
echo ""
read -n 1 -s -r -p "Press any key to close this window."
echo ""
