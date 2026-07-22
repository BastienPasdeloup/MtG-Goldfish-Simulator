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

echo ""
echo "=================================================="
echo "  ✅  All done!"
echo "=================================================="
echo ""
echo "  To start the simulator, run:  ./launch-linux.sh"
echo "  (or double-click launch-linux.sh and choose 'Run in Terminal')"
echo ""
read -n 1 -s -r -p "Press any key to close."
echo ""
