#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# setup.sh — run once on your VPS after cloning the repo
# Usage:  bash setup.sh
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

echo ""
echo "╔══════════════════════════════════════╗"
echo "║      Grammerly VPS Setup Script      ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── 1. System packages ────────────────────────────────────────────
echo "[1/4] Installing system dependencies..."
sudo apt-get update -q
sudo apt-get install -y python3 python3-pip python3-venv git

# ── 2. Virtual environment ────────────────────────────────────────
echo "[2/4] Creating Python virtual environment..."
python3 -m venv venv

# ── 3. Python packages ────────────────────────────────────────────
echo "[3/4] Installing Python packages..."
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt

# ── 4. Permissions ───────────────────────────────────────────────
echo "[4/4] Setting script permissions..."
chmod +x start.sh install-service.sh

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Confirm bot/.env has your credentials (BOT_TOKEN, DATABASE_URL, RAPIDAPI_KEY, etc.)"
echo "  2. Test the bot manually first:           ./start.sh"
echo "  3. Install as a system service:           sudo bash install-service.sh"
echo ""
