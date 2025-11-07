#!/bin/bash

# This script sets up the Event Echo backend on an EC2 instance
# Run this script on your local machine
# Usage: ./setup_ec2.sh <ec2-ip> <path-to-pem-key>

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <ec2-ip> <path-to-pem-key>"
    exit 1
fi

EC2_IP=$1
PEM_KEY=$2
APP_DIR="/home/ubuntu/event-echo"
BACKEND_DIR="$APP_DIR/backend"

echo "Setting up Event Echo backend on EC2 instance $EC2_IP..."

# Create deployment directory structure on EC2
ssh -i "$PEM_KEY" ubuntu@"$EC2_IP" "mkdir -p $APP_DIR"

# Copy backend files to EC2
echo "Copying backend files..."
scp -i "$PEM_KEY" -r ../backend ../requirements.txt ubuntu@"$EC2_IP":$APP_DIR/

# SSH into EC2 and set up the environment
ssh -i "$PEM_KEY" ubuntu@"$EC2_IP" "bash -s" << 'EOF'
    APP_DIR="/home/ubuntu/event-echo"
    cd $APP_DIR

    # Update system and install Python
    sudo apt-get update
    sudo apt-get install -y python3-pip python3-venv supervisor nginx

    # Create and activate virtual environment
    python3 -m venv venv
    source venv/bin/activate

    # Install requirements
    pip install -r requirements.txt

    # Create .env file (you'll need to fill in the values)
    cat > .env << 'END'
JWT_SECRET=my_random_secret_key
DATABASE_URL=postgresql://postgres:wildcats!EventEcho@eventecho-db.c1g0am6a8mrk.us-east-2.rds.amazonaws.com/eventecho
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
END

    # Create supervisor config
    sudo tee /etc/supervisor/conf.d/event-echo.conf << 'END'
[program:event-echo]
directory=/home/ubuntu/event-echo
command=/home/ubuntu/event-echo/venv/bin/python -m backend.gateway.server
user=ubuntu
autostart=true
autorestart=true
stderr_logfile=/var/log/event-echo/err.log
stdout_logfile=/var/log/event-echo/out.log
environment=
    PYTHONPATH="/home/ubuntu/event-echo",
    PATH="/home/ubuntu/event-echo/venv/bin"
END

    # Create log directory
    sudo mkdir -p /var/log/event-echo
    sudo chown -R ubuntu:ubuntu /var/log/event-echo

    # Setup nginx reverse proxy
    sudo tee /etc/nginx/sites-available/event-echo << 'END'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
END

    # Enable nginx site
    sudo ln -sf /etc/nginx/sites-available/event-echo /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Start services
    sudo supervisorctl reread
    sudo supervisorctl update
    sudo supervisorctl restart event-echo
    sudo service nginx restart

    # Show status
    echo "Checking service status..."
    sudo supervisorctl status event-echo
    echo "Checking nginx status..."
    sudo service nginx status
EOF

echo "Setup complete! The backend should now be running on $EC2_IP:80"
echo "Check the logs at:"
echo "  - Application logs: /var/log/event-echo/out.log and err.log"
echo "  - Nginx logs: /var/log/nginx/error.log and access.log"