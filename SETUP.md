## 1. Create and activate a virtual environment
From a terminal at the project root (`Event-Echo-Lite`):

```bash
python -m venv .venv
```

Then activate it:

- Mac/Linux:
```bash
source .venv/bin/activate
```

- Windows (PowerShell):
```powershell
.venv\Scripts\Activate.ps1
```

## 2. Install requirements
```bash
pip install -r requirements.txt
```

## 3. Configure ports (backend 5002, frontend 3002)
The backend reads configuration from a `.env` file at the project root. Create it with:

```bash
# file: .env
GATEWAY_PORT=5002
```

Notes:
- Backend will listen on `0.0.0.0:5002` by default when `.env` is present.
- The frontend is already configured to call the API at `http://localhost:5002` via `frontend/js/config.js`.

## 4. Run the backend server (port 5002)
From the project root:
```bash
python -m backend.gateway.server
```
This starts the Flask gateway on port 5002.

## 5. Serve the frontend (port 3002)
In a separate terminal, from the project root:
```bash
cd frontend
python -m http.server 3002
```
Open the site at:
```
http://localhost:3002
```
The frontend will call the backend API at `http://localhost:5002`.

---

## Deploying on a server (exact files and locations)
Below is a minimal, working layout and the files you need to place.

### Directory layout on the server
- `/opt/event-echo-lite/` — project root (clone the repo here)
  - `.env` — backend configuration
  - `.venv/` — Python virtual environment
  - `backend/` — backend source
  - `frontend/` — static frontend files
  - `requirements.txt`
  - `SETUP.md`

### Create `.env` at project root
`/opt/event-echo-lite/.env`:
```bash
GATEWAY_PORT=5002
```

### Create the virtual environment and install dependencies
```bash
cd /opt/event-echo-lite
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Systemd services (optional but recommended)
Create these two unit files so the services start on boot.

1) `/etc/systemd/system/event-echo-backend.service`
```
[Unit]
Description=Event Echo Lite Backend (Flask Gateway)
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/event-echo-lite
Environment=PYTHONUNBUFFERED=1
Environment=FLASK_ENV=production
EnvironmentFile=/opt/event-echo-lite/.env
ExecStart=/opt/event-echo-lite/.venv/bin/python -m backend.gateway.server
Restart=always
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```

2) `/etc/systemd/system/event-echo-frontend.service`
```
[Unit]
Description=Event Echo Lite Frontend Static Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/event-echo-lite/frontend
ExecStart=/usr/bin/python3 -m http.server 3002
Restart=always
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```

Enable and start services:
```bash
sudo systemctl daemon-reload
sudo systemctl enable event-echo-backend.service event-echo-frontend.service
sudo systemctl start event-echo-backend.service event-echo-frontend.service
```

### Firewall (if applicable)
Open ports 3002 (frontend) and 5002 (backend):
```bash
# Ubuntu with UFW
sudo ufw allow 3002/tcp
sudo ufw allow 5002/tcp
```

### Optional: Reverse proxy with Nginx
If you prefer to serve the frontend on port 80 and proxy API calls:
- Serve static files from `/opt/event-echo-lite/frontend` as site root
- Proxy `/auth` and `/events` paths to `http://127.0.0.1:5002`

Minimal Nginx server block (example):
```
server {
    listen 80;
    server_name _;

    root /opt/event-echo-lite/frontend;
    index index.html;

    location /auth { proxy_pass http://127.0.0.1:5002; }
    location /events { proxy_pass http://127.0.0.1:5002; }

    # Static file fallthrough
    location / { try_files $uri $uri/ =404; }
}
```

Reload Nginx after adding the site.

---

## Quick commands recap
```bash
# Backend (root)
python -m backend.gateway.server  # listens on 5002

# Frontend (from ./frontend)
python -m http.server 3002        # serves static files on 3002

# Visit the app
http://localhost:3002
```

