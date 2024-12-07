#!/bin/bash

## Security measures

GATEKEEPER_IP=$1
PROXY_IP=$2

echo "Gatekeeper IP: $GATEKEEPER_IP"
echo "Proxy IP: $PROXY_IP"

###########################################################
# Disable and remove unused services
###########################################################
echo "Starting Trusted Host service cleanup..."
# List of unused or optional services to disable
unused_services=(
    "ModemManager.service"
    "multipathd.service"
    "serial-getty@ttyS0.service"
    "udisks2.service"
    "acpid.service"
    "chrony.service"
    "cron.service"
    "getty@tty1.service"
    "rsyslog.service"
    "snap.amazon-ssm-agent.amazon-ssm-agent.service"
    "snapd.service"
    "unattended-upgrades.service"
)

echo "Disabling and stopping unused or optional services..."
for service in "${unused_services[@]}"; do
    if systemctl list-unit-files | grep -q "$service"; then
        echo "Disabling and stopping $service..."
        sudo systemctl stop "$service" 2>/dev/null || echo "Failed to stop $service."
        sudo systemctl disable "$service" 2>/dev/null || echo "Failed to disable $service."
    else
        echo "$service is not installed or active. Skipping."
    fi
done

echo "Unused services have been disabled."

###########################################################
# Configure IPTables
###########################################################
echo "Starting IPTables Configuration..."

# Allow temporary unrestricted traffic (not to lock myself out)
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -P FORWARD ACCEPT
sudo iptables -P INPUT ACCEPT
sudo iptables -P OUTPUT ACCEPT

# Allow loopback traffic
sudo iptables -A INPUT -i lo -j ACCEPT
sudo iptables -A OUTPUT -o lo -j ACCEPT
echo "Allowed loopback traffic."

# Allow established and related connections
sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
echo "Allowed established and related connections."

# Apply restrictive rules for Gatekeeper and Proxy
sudo iptables -A INPUT -p tcp --dport 22 -s "$GATEKEEPER_IP" -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 80 -s "$GATEKEEPER_IP" -j ACCEPT
sudo iptables -A FORWARD -p tcp --dport 80 -d "$PROXY_IP" -j ACCEPT
sudo iptables -A OUTPUT -d "$PROXY_IP" -j ACCEPT
echo "Applied restrictive rules for Gatekeeper and Proxy."

# Set default policies to DROP (Restrict all other traffic)
sudo iptables -P INPUT DROP
sudo iptables -P FORWARD DROP

echo "Security Setup complete. Bootstrapping before blocking OUT traffic.."
## Bootstrapping before dropping OUTPUT connections

# Setup
## Setup environment
sudo apt update
sudo apt install -y python3-venv python3-pip
python3 -m venv .venv
source ~/.venv/bin/activate
pip install fastapi uvicorn boto3 requests pydantic aiohttp

## Block OUT traffic
echo "Blocking OUT traffic.."
sudo iptables -P OUTPUT DROP

# Save rules
sudo iptables-save > iptables.log
echo "IPTables rules updated and saved successfully."
echo "Security Setup complete. Launching Trusted Host.."

# Launch Trusted Host
sudo .venv/bin/uvicorn main:app --host 0.0.0.0 --port 80