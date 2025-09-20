# Signal Bot Installation Guide

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Quick Install](#quick-install)
3. [Detailed Installation](#detailed-installation)
4. [Docker Installation](#docker-installation)
5. [Production Setup](#production-setup)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements

- **OS**: Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+)
- **Python**: 3.8 or higher
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 1GB for application + space for database
- **Network**: Internet connection for Signal communication

### Recommended Requirements

- **OS**: Ubuntu 22.04 LTS or Debian 12
- **Python**: 3.10 or higher
- **RAM**: 4GB or more
- **Storage**: 10GB+ for logs and message history
- **CPU**: 2+ cores for better performance

### Software Dependencies

- signal-cli (0.13.4 or higher)
- SQLite3
- Java Runtime (for signal-cli)
- Git (for cloning repository)
- curl or wget (for downloads)

## Quick Install

### One-Line Installation

```bash
curl -fsSL https://raw.githubusercontent.com/yourusername/signal-bot/main/install.sh | bash
```

### Manual Quick Install

```bash
# 1. Clone repository
git clone https://github.com/yourusername/signal-bot.git
cd signal-bot

# 2. Run installer
./install_signal_cli.sh

# 3. Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Start services
./manage.sh start

# 5. Open web interface
# Navigate to http://localhost:8084
```

## Detailed Installation

### Step 1: System Preparation

#### Ubuntu/Debian

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y \
    python3 python3-pip python3-venv \
    default-jre wget curl git \
    sqlite3 build-essential

# Install additional tools
sudo apt install -y screen tmux htop
```

#### RHEL/CentOS/Fedora

```bash
# Update system
sudo dnf update -y

# Install dependencies
sudo dnf install -y \
    python3 python3-pip python3-virtualenv \
    java-latest-openjdk wget curl git \
    sqlite gcc make

# Install additional tools
sudo dnf install -y screen tmux htop
```

#### Arch Linux

```bash
# Update system
sudo pacman -Syu

# Install dependencies
sudo pacman -S \
    python python-pip python-virtualenv \
    jre-openjdk wget curl git \
    sqlite base-devel

# Install additional tools
sudo pacman -S screen tmux htop
```

### Step 2: Install signal-cli

#### Automated Installation

```bash
# Run the provided installer
./install_signal_cli.sh
```

#### Manual Installation

```bash
# Download signal-cli
SIGNAL_VERSION="0.13.4"
wget https://github.com/AsamK/signal-cli/releases/download/v${SIGNAL_VERSION}/signal-cli-${SIGNAL_VERSION}.tar.gz

# Extract to /opt
sudo tar xf signal-cli-${SIGNAL_VERSION}.tar.gz -C /opt/
sudo mv /opt/signal-cli-${SIGNAL_VERSION} /opt/signal-cli

# Create symlink
sudo ln -sf /opt/signal-cli/bin/signal-cli /usr/local/bin/signal-cli

# Verify installation
signal-cli --version
```

### Step 3: Clone Repository

```bash
# Clone the repository
git clone https://github.com/yourusername/signal-bot.git
cd signal-bot

# Or download as archive
wget https://github.com/yourusername/signal-bot/archive/main.zip
unzip main.zip
cd signal-bot-main
```

### Step 4: Python Environment Setup

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Optional: Install development dependencies
pip install -r requirements-dev.txt
```

### Step 5: Initial Configuration

#### Create Configuration File

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration
nano .env
```

#### Basic .env Configuration

```env
# Signal CLI Configuration
SIGNAL_CLI_PATH=/usr/local/bin/signal-cli

# Database Configuration
DATABASE_PATH=signal_bot.db

# Web Server Configuration
WEB_HOST=0.0.0.0
WEB_PORT=8084

# Logging
LOG_LEVEL=INFO

# AI Configuration (Optional)
OLLAMA_HOST=http://localhost:11434/
```

### Step 6: Signal Account Setup

#### Option A: Link Existing Account (Recommended)

```bash
# Start the bot
./manage.sh start

# Open web browser
# Navigate to http://localhost:8084/setup
# Click "Link Device" and scan QR code with Signal app
```

#### Option B: Register New Account

```bash
# Register with phone number
signal-cli -u +YOUR_PHONE_NUMBER register

# Wait for SMS verification code, then:
signal-cli -u +YOUR_PHONE_NUMBER verify YOUR_CODE

# Set profile name
signal-cli -u +YOUR_PHONE_NUMBER updateProfile --name "Signal Bot"
```

### Step 7: Start Services

```bash
# Start all services
./manage.sh start

# Or start individually
./run_signal_service.sh    # Start Signal polling
./run_web_server.sh        # Start web interface

# Check status
./manage.sh status
```

## Docker Installation

### Using Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  signal-bot:
    build: .
    container_name: signal-bot
    restart: unless-stopped
    ports:
      - "8084:8084"
    volumes:
      - ./signal_bot.db:/app/signal_bot.db
      - ./config:/app/config
      - ./logs:/app/logs
    environment:
      - SIGNAL_CLI_PATH=/usr/local/bin/signal-cli
      - DATABASE_PATH=/app/signal_bot.db
      - WEB_HOST=0.0.0.0
      - WEB_PORT=8084
```

Build and run:

```bash
# Build image
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Using Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    default-jre wget curl \
    && rm -rf /var/lib/apt/lists/*

# Install signal-cli
RUN wget https://github.com/AsamK/signal-cli/releases/download/v0.13.4/signal-cli-0.13.4.tar.gz \
    && tar xf signal-cli-0.13.4.tar.gz -C /opt/ \
    && ln -s /opt/signal-cli-0.13.4/bin/signal-cli /usr/local/bin/signal-cli \
    && rm signal-cli-0.13.4.tar.gz

# Set working directory
WORKDIR /app

# Copy application
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8084

# Start services
CMD ["./manage.sh", "start"]
```

## Production Setup

### System Service Setup

Create systemd service files:

#### Signal Service (`/etc/systemd/system/signal-bot-service.service`)

```ini
[Unit]
Description=Signal Bot Polling Service
After=network.target

[Service]
Type=simple
User=signalbot
Group=signalbot
WorkingDirectory=/opt/signal-bot
Environment="PATH=/opt/signal-bot/venv/bin:/usr/local/bin:/usr/bin"
ExecStart=/opt/signal-bot/venv/bin/python /opt/signal-bot/signal_service.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Web Server (`/etc/systemd/system/signal-bot-web.service`)

```ini
[Unit]
Description=Signal Bot Web Interface
After=network.target signal-bot-service.service

[Service]
Type=simple
User=signalbot
Group=signalbot
WorkingDirectory=/opt/signal-bot
Environment="PATH=/opt/signal-bot/venv/bin:/usr/local/bin:/usr/bin"
ExecStart=/opt/signal-bot/venv/bin/python /opt/signal-bot/web_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start services:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable signal-bot-service
sudo systemctl enable signal-bot-web

# Start services
sudo systemctl start signal-bot-service
sudo systemctl start signal-bot-web

# Check status
sudo systemctl status signal-bot-service
sudo systemctl status signal-bot-web
```

### Nginx Reverse Proxy

Install and configure Nginx:

```nginx
# /etc/nginx/sites-available/signal-bot

server {
    listen 80;
    server_name bot.example.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name bot.example.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/bot.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bot.example.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy settings
    location / {
        proxy_pass http://localhost:8084;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/signal-bot /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### SSL with Let's Encrypt

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d bot.example.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

### Security Hardening

#### Create dedicated user

```bash
# Create user
sudo useradd -r -m -d /opt/signal-bot -s /bin/bash signalbot

# Set ownership
sudo chown -R signalbot:signalbot /opt/signal-bot

# Set permissions
sudo chmod 750 /opt/signal-bot
sudo chmod 640 /opt/signal-bot/.env
sudo chmod 660 /opt/signal-bot/signal_bot.db
```

#### Firewall Configuration

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 80/tcp     # HTTP
sudo ufw allow 443/tcp    # HTTPS
sudo ufw enable

# Firewalld (RHEL/CentOS)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

## Verification

### Post-Installation Checks

```bash
# 1. Check service status
./manage.sh status

# 2. Test configuration
./manage.sh config

# 3. Test module loading
./manage.sh test

# 4. Check API endpoint
curl http://localhost:8084/api/status

# 5. Check logs for errors
tail -50 signal_service.log
tail -50 web_server.log
```

### Web Interface Verification

1. Open browser to http://localhost:8084
2. Check dashboard loads properly
3. Navigate to Setup page
4. Verify Signal CLI status shows "Available"
5. Test user sync functionality
6. Test group sync functionality

## Troubleshooting

### Installation Issues

#### Python Version Error

```bash
# Check Python version
python3 --version

# If too old, install newer version
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.10
```

#### signal-cli Not Found

```bash
# Check installation
which signal-cli

# Add to PATH if needed
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### Permission Denied

```bash
# Fix script permissions
chmod +x *.sh

# Fix database permissions
chmod 660 signal_bot.db
```

### Common Problems

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions.

## Upgrading

### From Source

```bash
# Backup database
cp signal_bot.db signal_bot.db.backup

# Pull latest changes
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Restart services
./manage.sh restart
```

### Database Migration

```bash
# Run migration script (if provided)
python3 migrate_database.py

# Or manual migration
sqlite3 signal_bot.db < migrations/latest.sql
```

## Uninstallation

### Complete Removal

```bash
# Stop services
./manage.sh stop

# Remove systemd services (if configured)
sudo systemctl stop signal-bot-service signal-bot-web
sudo systemctl disable signal-bot-service signal-bot-web
sudo rm /etc/systemd/system/signal-bot-*.service

# Remove application
cd ..
rm -rf signal-bot/

# Remove signal-cli (optional)
sudo rm -rf /opt/signal-cli
sudo rm /usr/local/bin/signal-cli

# Remove Python virtual environment
rm -rf venv/
```

## Next Steps

1. Configure the bot via web interface
2. Link Signal account or register new one
3. Set up group monitoring
4. Configure user reactions
5. Set up AI providers (optional)
6. Review security settings

## Support

- Check [README.md](../README.md) for overview
- See [CONFIGURATION.md](CONFIGURATION.md) for settings
- Read [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for issues
- Visit [API.md](API.md) for API documentation