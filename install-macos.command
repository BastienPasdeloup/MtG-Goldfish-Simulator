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

echo ""
echo "=================================================="
echo "  ✅  All done!"
echo "=================================================="
echo ""
echo "  To start the simulator, double-click:"
echo "      launch-macos.command"
echo ""
read -n 1 -s -r -p "Press any key to close this window."
echo ""
