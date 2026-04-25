#!/bin/bash
# launch_at_boot.sh
# Formally stop the existing service to ensure clean resource release
sudo systemctl stop terraquest.service
sleep 2
# Launch the dashboard directly
cd /home/terraq/TerraQuest/dashboard
/usr/bin/python3 app.py > /home/terraq/TerraQuest/dashboard_boot.log 2>&1
