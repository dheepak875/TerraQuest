#!/bin/bash
set -e

# Default Hotspot Password if not specified
HOTSPOT_PASS="letsgoww"

echo "Checking for NetworkManager..."
if ! command -v nmcli &> /dev/null; then
    echo "Error: NetworkManager (nmcli) is not installed or active."
    echo "If you are on Raspberry Pi OS 'Bullseye', run 'sudo raspi-config' -> Advanced Options -> Network Config -> NetworkManager."
    echo "If you are on 'Bookworm', it should be there. Ensure it's active."
    exit 1
fi

echo ">>> Configuring Home WiFi: Silence of the LANS"
# Remove if exists to ensure clean state
nmcli con delete "Silence of the LANS" 2>/dev/null || true

# Add connection
nmcli con add type wifi ifname wlan0 con-name "Silence of the LANS" ssid "Silence of the LANS"
nmcli con modify "Silence of the LANS" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "beatz555"
# High Priority
nmcli con modify "Silence of the LANS" connection.autoconnect yes
nmcli con modify "Silence of the LANS" connection.autoconnect-priority 100

echo ">>> Configuring Backup Hotspot: TerraQuest-Link"
nmcli con delete "TerraQuest-Link" 2>/dev/null || true

# Add AP connection
nmcli con add type wifi ifname wlan0 con-name "TerraQuest-Link" ssid "TerraQuest-Link" mode ap
nmcli con modify "TerraQuest-Link" ipv4.method shared
nmcli con modify "TerraQuest-Link" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$HOTSPOT_PASS"
# Low Priority
nmcli con modify "TerraQuest-Link" connection.autoconnect yes
nmcli con modify "TerraQuest-Link" connection.autoconnect-priority 10

echo ">>> Configuration Complete!"
echo "Current Connections:"
nmcli con show
