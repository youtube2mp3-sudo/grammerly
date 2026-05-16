#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# install-service.sh — installs Grammerly as a systemd service
# Run with:  sudo bash install-service.sh
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
RUN_AS="${SUDO_USER:-$(logname 2>/dev/null || whoami)}"
SERVICE_NAME="grammerly"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo ""
echo "Installing Grammerly as a systemd service..."
echo "  Repo path  : $REPO_DIR"
echo "  Running as : $RUN_AS"
echo "  Service    : $SERVICE_FILE"
echo ""

# Write the unit file — paths are resolved automatically at install time
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Grammerly Discord Bot
Documentation=https://github.com/youtube2mp3-sudo/grammerly
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_AS
WorkingDirectory=$REPO_DIR
ExecStart=$REPO_DIR/venv/bin/python3 $REPO_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=grammerly

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo "Service installed and started!"
echo ""
echo "Useful commands:"
echo "  Live logs   :  journalctl -u $SERVICE_NAME -f"
echo "  Status      :  systemctl status $SERVICE_NAME"
echo "  Restart     :  sudo systemctl restart $SERVICE_NAME"
echo "  Stop        :  sudo systemctl stop $SERVICE_NAME"
echo "  Disable     :  sudo systemctl disable $SERVICE_NAME"
echo ""
