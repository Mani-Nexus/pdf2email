# Deploying to Hostinger VPS (Ubuntu/Debian)

This guide explains how to set up your Streamlit application on your Hostinger VPS (`148.230.97.209`) with automatic updates from GitHub.

## 1. Server Preparation
Connect to your VPS:
```bash
ssh root@148.230.97.209
```

Update system and install dependencies:
```bash
sudo apt update
sudo apt install python3.12-venv python3-pip git -y
```

## 2. Project Setup
```bash
cd /root
git clone https://github.com/Mani-Nexus/pdf2email.git
cd pdf2email

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install all dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Firewall Setup (Very Important)
Ensure port 8502 is open to the public:
```bash
sudo ufw allow 8502/tcp
sudo ufw allow 80/tcp
sudo ufw reload
```

## 4. Persistent Running with Systemd
Create/Edit the service file:
```bash
sudo nano /etc/systemd/system/pdf2email.service
```

Paste this configuration (Optimized for Port 8502 and VPS access):
```ini
[Unit]
Description=Streamlit PDF Extractor (App 2)
After=network.target

[Service]
User=root
WorkingDirectory=/root/pdf2email
# IMPORTANT: Tell Python where the source files are
Environment=PYTHONPATH=/root/pdf2email
ExecStart=/root/pdf2email/venv/bin/streamlit run app.py --server.port 8502 --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false --server.headless true
Restart=always

[Install]
WantedBy=multi-user.target
```

## 5. Nginx Config for 50GB Uploads (Optional)
If you use Nginx to access the app via a domain, you MUST increase the upload limit:
```bash
sudo nano /etc/nginx/sites-available/pdf2email
```
Add `client_max_body_size 50G;` inside the server block:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    client_max_body_size 50G;

    location / {
        proxy_pass http://localhost:8502;
        ...
    }
}
```

## 6. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable pdf2email
sudo systemctl restart pdf2email
```

## 5. Troubleshooting
If the app doesn't load, check the logs for errors:
```bash
sudo journalctl -u pdf2email.service -n 50
```

## 6. Updates
Whenever you push new changes to GitHub, run these commands on the VPS:
```bash
cd /root/pdf2email
git pull
sudo systemctl restart pdf2email
```
