#!/bin/bash

# This script creates a backup of existing code on EC2 before deploying new code
# Usage: ./backup_ec2.sh <ec2-ip> <path-to-pem-key>

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <ec2-ip> <path-to-pem-key>"
    exit 1
fi

EC2_IP=$1
PEM_KEY=$2
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Creating backup of existing code on EC2 instance $EC2_IP..."

# SSH into EC2 and create backup
ssh -i "$PEM_KEY" ubuntu@"$EC2_IP" "bash -s" << EOF
    # Check if event-echo directory exists
    if [ -d "/home/ubuntu/event-echo" ]; then
        echo "Found existing event-echo directory, creating backup..."
        cd /home/ubuntu
        tar -czf event-echo_backup_${TIMESTAMP}.tar.gz event-echo/
        mkdir -p backups
        mv event-echo_backup_${TIMESTAMP}.tar.gz backups/
        echo "Backup created at: /home/ubuntu/backups/event-echo_backup_${TIMESTAMP}.tar.gz"
    else
        echo "No existing event-echo directory found."
    fi

    # List any running processes
    echo "Current running processes:"
    ps aux | grep -i "python\|flask\|gunicorn"
EOF

echo "Backup process complete. Please check the output above for existing processes."