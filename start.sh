#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# start.sh — activate the venv and launch the bot
# Usage:  ./start.sh
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

# Change to the repo root regardless of where the script is called from
cd "$(dirname "$0")"

# Make sure the venv exists
if [ ! -f "venv/bin/activate" ]; then
  echo "ERROR: Virtual environment not found. Run:  bash setup.sh"
  exit 1
fi

source venv/bin/activate
exec python3 main.py
