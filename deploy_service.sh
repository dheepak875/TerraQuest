#!/bin/bash
# Deploy updated dashboard and service configuration to TerraQuest Pi

echo "================================================"
echo "TerraQuest Dashboard Deployment"
echo "================================================"

echo ""
echo "[1/3] Deploying app.py..."
scp dashboard/app.py terraq@TerraQuest-2.local:~/TerraQuest/dashboard/app.py

echo ""
echo "[2/3] Deploying service file..."
scp terraquest.service terraq@TerraQuest-2.local:~/TerraQuest/terraquest.service

echo ""
echo "================================================"
echo "Deployment Complete!"
echo "================================================"
echo ""
echo "Now run these commands on the Pi (SSH terminal):"
echo ""
echo "  # Copy service file to systemd"
echo "  sudo cp ~/TerraQuest/terraquest.service /etc/systemd/system/terraquest.service"
echo ""
echo "  # Reload systemd and restart service"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl restart terraquest.service"
echo ""
echo "  # Check service status"
echo "  sudo systemctl status terraquest.service"
echo ""
echo "  # View logs (optional)"
echo "  sudo journalctl -u terraquest.service -f"
echo ""
