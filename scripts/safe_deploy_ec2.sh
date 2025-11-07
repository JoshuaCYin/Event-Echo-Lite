#!/bin/bash

# This script safely deploys Event Echo backend to EC2, preserving existing configurations
# Usage: ./safe_deploy_ec2.sh <ec2-ip> <path-to-pem-key>

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <ec2-ip> <path-to-pem-key>"
    exit 1
fi

EC2_IP=$1
PEM_KEY=$2
APP_DIR="/home/ubuntu/event-echo"

echo "Checking existing setup on EC2 instance $EC2_IP..."

# First, check existing setup and processes
ssh -i "$PEM_KEY" ubuntu@"$EC2_IP" "bash -s" << 'EOF'
    echo "=== Current Environment Check ==="
    
    # Check Python version
    echo "Python version:"
    python3 --version
    
    # Check for existing virtual environment
    if [ -d "/home/ubuntu/event-echo/venv" ]; then
        echo "Found existing virtual environment"
    fi
    
    # Check for supervisor configurations
    if [ -f "/etc/supervisor/conf.d/event-echo.conf" ]; then
        echo "Found existing supervisor config"
        sudo supervisorctl status
    fi
    
    # Check for nginx configurations
    if [ -f "/etc/nginx/sites-enabled/event-echo" ]; then
        echo "Found existing nginx config"
        sudo nginx -t
    fi
    
    # Check for existing .env file
    if [ -f "/home/ubuntu/event-echo/.env" ]; then
        echo "Found existing .env file"
        echo "Current environment variables (keys only):"
        grep -v '^#' /home/ubuntu/event-echo/.env | cut -d'=' -f1
    fi
    
    echo "=== Process Check ==="
    ps aux | grep -i "python\|flask\|gunicorn"
EOF

# Ask for confirmation before proceeding
read -p "Would you like to proceed with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Deployment cancelled."
    exit 1
fi

# Copy backend files to EC2, preserving existing .env
echo "Copying backend files..."
scp -i "$PEM_KEY" -r ../backend ../requirements.txt ubuntu@"$EC2_IP":$APP_DIR/

# Update configuration and restart services
ssh -i "$PEM_KEY" ubuntu@"$EC2_IP" "bash -s" << 'EOF'
    cd /home/ubuntu/event-echo

    # Activate existing virtual environment or create new one
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate

    # Install/update requirements
    pip install -r requirements.txt

    # Only create .env if it doesn't exist
    if [ ! -f ".env" ]; then
        echo "Creating new .env file..."
        cat > .env << 'END'
JWT_SECRET=my_random_secret_key
DATABASE_URL=postgresql://postgres:wildcats!EventEcho@eventecho-db.c1g0am6a8mrk.us-east-2.rds.amazonaws.com/eventecho
END
    fi

    # Restart services if they exist
    if [ -f "/etc/supervisor/conf.d/event-echo.conf" ]; then
        echo "Restarting supervisor service..."
        sudo supervisorctl restart event-echo
    fi

    if [ -f "/etc/nginx/sites-enabled/event-echo" ]; then
        echo "Restarting nginx..."
        sudo service nginx restart
    fi

    # Show status
    echo "=== Final Status Check ==="
    if [ -f "/etc/supervisor/conf.d/event-echo.conf" ]; then
        sudo supervisorctl status event-echo
    fi
    if [ -f "/etc/nginx/sites-enabled/event-echo" ]; then
        sudo service nginx status
    fi
EOF

echo "Safe deployment complete! Please check the output above for any issues."
echo "You can check the application logs at:"
echo "  - Application logs: /var/log/event-echo/out.log and err.log"
echo "  - Nginx logs: /var/log/nginx/error.log and access.log"