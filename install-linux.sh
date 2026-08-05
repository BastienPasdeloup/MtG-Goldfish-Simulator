#!/bin/bash
#
# MtG Goldfish Simulator — one-click installer for Linux.
#
# Run this once to set everything up. Either:
#   • double-click it in your file manager and choose "Run in Terminal", or
#   • open a terminal in this folder and run:  ./install-linux.sh
#
# It installs the small "uv" tool (which fetches the right Python and every
# dependency for you) and downloads everything the simulator needs.
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
  echo "   Please close this terminal, open a new one, and run this installer again."
  echo ""
  read -n 1 -s -r -p "Press any key to close."
  exit 1
fi

# --------------------------------------------- step 2: Python + dependencies
echo ""
echo "==> Downloading Python and all dependencies…"
echo "    (The first time this can take a minute or two — please be patient.)"
echo ""
uv sync

# ------------------------------------------- step 3: menu entry (.desktop)
# A launcher in your applications menu so you can start the simulator without
# hunting for this folder. It starts the server + opens your browser; the server
# quits itself when you close the last tab.
echo ""
echo "==> Creating an applications-menu entry…"
PROJECT_DIR="$(pwd)"
APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"
cat > "$APPS_DIR/mtg-goldfish-simulator.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=MtG Goldfish Simulator
Comment=Solitaire MTG deck-testing simulator
Exec="$PROJECT_DIR/launch-linux.sh"
Path=$PROJECT_DIR
Terminal=true
Categories=Game;
DESKTOP
chmod +x "$APPS_DIR/mtg-goldfish-simulator.desktop"
update-desktop-database "$APPS_DIR" 2>/dev/null || true

echo ""
echo "=================================================="
echo "  ✅  All done!"
echo "=================================================="
echo ""
echo "  Launch it from your applications menu:  MtG Goldfish Simulator"
echo "  …or run:  ./launch-linux.sh"
echo ""
read -n 1 -s -r -p "Press any key to close."
echo ""
