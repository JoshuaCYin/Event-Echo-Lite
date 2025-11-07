#!/bin/bash

# This script cleans up existing Event Echo installation on EC2
# Usage: ./cleanup_ec2.sh <ec2-ip> <path-to-pem-key>

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <ec2-ip> <path-to-pem-key>"
    exit 1
fi

EC2_IP=$1
PEM_KEY=$2

echo "WARNING: This will remove all existing Event Echo files and configurations on $EC2_IP"
read -p "Are you sure you want to proceed? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Cleanup cancelled."
    exit 1
fi

# SSH into EC2 and clean up
ssh -i "$PEM_KEY" ubuntu@"$EC2_IP" "bash -s" << 'EOF'
    echo "Stopping services..."
    # Stop supervisor service if it exists
    if [ -f "/etc/supervisor/conf.d/event-echo.conf" ]; then
        sudo supervisorctl stop event-echo
        sudo rm /etc/supervisor/conf.d/event-echo.conf
        sudo supervisorctl reread
        sudo supervisorctl update
    fi

    # Remove nginx config if it exists
    if [ -f "/etc/nginx/sites-enabled/event-echo" ]; then
        sudo rm /etc/nginx/sites-enabled/event-echo
        sudo rm -f /etc/nginx/sites-available/event-echo
        sudo service nginx restart
    fi

    echo "Removing application files..."
    # Remove application directory
    rm -rf /home/ubuntu/event-echo

    # Remove log files
    sudo rm -rf /var/log/event-echo

    echo "Cleanup complete!"
EOF

echo "EC2 instance has been cleaned. You can now deploy fresh code."