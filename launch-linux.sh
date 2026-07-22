#!/bin/bash
#
# MtG Goldfish Simulator — one-click launcher for Linux.
#
# Either double-click it and choose "Run in Terminal", or open a terminal in
# this folder and run:  ./launch-linux.sh
#
# The simulator opens in your web browser automatically. Keep this terminal
# open while you use the app; close it (or press Ctrl+C) to stop the simulator.
#
# If you have not installed it yet, run ./install-linux.sh first.
#
set -e

# Always work from the project folder, wherever this script was launched from.
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

if ! command -v uv >/dev/null 2>&1; then
  echo "❌ uv is not installed yet."
  echo "   Please run ./install-linux.sh first, then try again."
  echo ""
  read -n 1 -s -r -p "Press any key to close."
  exit 1
fi

URL="http://127.0.0.1:8000"

echo "=================================================="
echo "  Starting the MtG Goldfish Simulator"
echo "=================================================="
echo ""
echo "  Your browser will open at $URL shortly."
echo "  Keep this terminal open while you use the app."
echo "  To stop the simulator: close this window or press Ctrl+C."
echo ""

# Open the browser as soon as the server is actually responding (it may take a
# while the first time while dependencies finish downloading).
(
  for _ in $(seq 1 180); do
    sleep 1
    if curl -s -o /dev/null "$URL"; then
      (xdg-open "$URL" >/dev/null 2>&1 || true)
      break
    fi
  done
) &

uv run mtg-goldfish
