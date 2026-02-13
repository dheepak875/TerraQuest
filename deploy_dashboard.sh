#!/bin/bash
# Quick deployment script for dashboard updates

echo "Deploying dashboard/app.py to TerraQuest-2..."
scp dashboard/app.py terraq@TerraQuest-2.local:~/TerraQuest/dashboard/app.py

echo ""
echo "Now restart the service on the Pi with:"
echo "  ssh terraq@TerraQuest-2.local"
echo "  sudo systemctl restart terraquest.service"
