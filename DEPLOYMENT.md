# Deploying to Hostinger VPS (Ubuntu/Debian)

This guide explains how to set up your Streamlit application on your Hostinger VPS (`148.230.97.209`) with automatic updates from GitHub.

## 1. Server Preparation
Connect to your VPS:
```bash
ssh root@148.230.97.209
```

Update system and install dependencies:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3.12-venv python3-pip git nginx -y
```

## 2. Project Setup
Clone the repo:
```bash
git clone https://github.com/Mani-Nexus/pdf2email.git
cd pdf2email
```

Set up virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Persistent Running with Systemd
Create a service file to keep the app running:
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
ExecStart=/root/pdf2email/venv/bin/streamlit run app.py --server.port 8502 --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable pdf2email
sudo systemctl start pdf2email
```

## 4. Accessing the App
Your application is live at:
👉 **http://148.230.97.209:8502**

## 5. Updates
Whenever you push new changes to GitHub, run these commands on the VPS to update:
```bash
cd /root/pdf2email
git pull
sudo systemctl restart pdf2email
```
