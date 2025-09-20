# 🚀 Deployment Guide

Production deployment strategies for the Universal Video Downloader.

## 📋 Prerequisites

### Configuration Setup

Before deploying, you need to set up your configuration files:

```bash
# 1. Copy sample configurations
cp docker-compose.yml.sample docker-compose.yml
cp .env.sample .env

# 2. Customize for your environment
nano docker-compose.yml  # Configure volumes, ports, etc.
nano .env                # Configure paths, cookies, etc.
```

💡 **Note**: Both `docker-compose.yml` and `.env` are excluded from Git tracking, so you can safely customize them.

## 🏠 HomeLab Deployment

### Docker Compose (Recommended)

**Single Service**:
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  hometube:
    image: ghcr.io/EgalitarianMonkey/hometube:latest
    container_name: hometube
    restart: unless-stopped
    ports:
      - "8501:8501"
    volumes:
      - /data/videos:/data/Videos
      - /data/temp:/data/tmp
      - /config/cookies:/config
    environment:
      - TZ=Europe/Paris
      - STREAMLIT_SERVER_HEADLESS=true
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**With Reverse Proxy**:
```yaml
# Full stack with nginx
version: '3.8'

services:
  hometube:
    image: ghcr.io/EgalitarianMonkey/hometube:latest
    restart: unless-stopped
    volumes:
      - /data/videos:/data/Videos
      - /config/cookies:/config
    environment:
      - TZ=Europe/Paris
    networks:
      - app-network

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl/certs:ro
    depends_on:
      - hometube
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
```

### Automated Deployment Script

```bash
# Download and run deployment script
curl -sSL https://raw.githubusercontent.com/EgalitarianMonkey/hometube/main/deploy.sh | bash -s -- v1.0.0

# Or manual deployment
./deploy.sh v1.0.0 --backup --production
```

## ☁️ Cloud Deployment

### VPS/Cloud Server

**Requirements**:
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 50GB+ for video storage
- **CPU**: 2 cores minimum
- **Network**: Unmetered bandwidth preferred

**Setup Steps**:
```bash
# 1. Server preparation (Ubuntu 22.04)
sudo apt update && sudo apt upgrade -y
sudo apt install docker.io docker-compose-v2 nginx certbot

# 2. Clone repository
git clone https://github.com/EgalitarianMonkey/hometube.git
cd hometube

# 3. Configure environment
cp .env.example .env
nano .env  # Edit configuration

# 4. Setup SSL (if using domain)
sudo certbot --nginx -d your-domain.com

# 5. Deploy application
docker-compose -f docker-compose.prod.yml up -d
```

### Digital Ocean Droplet

**One-Click Deployment**:
```bash
# Create droplet with Docker pre-installed
# Size: 2GB RAM, 1 vCPU minimum

# Quick setup
git clone https://github.com/EgalitarianMonkey/hometube.git
cd hometube
./deploy.sh latest --production
```

### AWS ECS/Fargate

**Task Definition**:
```json
{
  "family": "hometube",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "hometube",
      "image": "ghcr.io/EgalitarianMonkey/hometube:latest",
      "portMappings": [
        {
          "containerPort": 8501,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "STREAMLIT_SERVER_HEADLESS",
          "value": "true"
        }
      ],
      "mountPoints": [
        {
          "sourceVolume": "videos-storage",
          "containerPath": "/data/Videos"
        }
      ]
    }
  ]
}
```

## 🔒 Security Configuration

### SSL/TLS Setup

**With Nginx and Let's Encrypt**:
```nginx
# /etc/nginx/sites-available/hometube
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Authentication Options

**Basic Auth with Nginx**:
```nginx
# Create password file
sudo htpasswd -c /etc/nginx/.htpasswd username

# Add to nginx config
location / {
    auth_basic "Videos Downloader";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    proxy_pass http://localhost:8501;
    # ... other proxy settings
}
```

**OAuth2 Proxy**:
```yaml
# docker-compose.yml addition
oauth2-proxy:
  image: quay.io/oauth2-proxy/oauth2-proxy:latest
  ports:
    - "4180:4180"
  environment:
    - OAUTH2_PROXY_PROVIDER=github
    - OAUTH2_PROXY_CLIENT_ID=your_github_client_id
    - OAUTH2_PROXY_CLIENT_SECRET=your_github_client_secret
    - OAUTH2_PROXY_UPSTREAM=http://hometube:8501
```

### Network Security

**Firewall Configuration** (UFW):
```bash
# Basic firewall rules
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Docker-specific rules
sudo ufw allow from 172.16.0.0/12 to any port 8501
```

**Fail2Ban Protection**:
```ini
# /etc/fail2ban/jail.local
[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3
bantime = 3600
```

## 📊 Monitoring & Logging

### Health Monitoring

**Docker Health Checks**:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1
```

**External Monitoring**:
```bash
# Simple uptime monitoring script
#!/bin/bash
while true; do
    if ! curl -f http://your-domain.com/_stcore/health; then
        echo "Service down at $(date)" | mail -s "Alert: Service Down" admin@domain.com
    fi
    sleep 300
done
```

### Logging Configuration

**Centralized Logging**:
```yaml
# docker-compose.yml logging
services:
  hometube:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service=hometube"
```

**Log Analysis with ELK Stack**:
```yaml
# Add to docker-compose.yml
elasticsearch:
  image: elasticsearch:7.15.0
  environment:
    - discovery.type=single-node

logstash:
  image: logstash:7.15.0
  volumes:
    - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf

kibana:
  image: kibana:7.15.0
  ports:
    - "5601:5601"
```

### Performance Monitoring

**Resource Usage**:
```bash
# Monitor container resources
docker stats hometube

# System resource monitoring
htop
iotop
nethogs
```

**Prometheus Metrics** (Optional):
```yaml
# Add metrics exporter
node-exporter:
  image: prom/node-exporter
  ports:
    - "9100:9100"
  
cadvisor:
  image: gcr.io/cadvisor/cadvisor
  ports:
    - "8080:8080"
  volumes:
    - /:/rootfs:ro
    - /var/run:/var/run:ro
    - /sys:/sys:ro
    - /var/lib/docker/:/var/lib/docker:ro
```

## 💾 Backup & Recovery

### Data Backup Strategy

**Critical Data**:
- Downloaded videos: `/data/Videos`
- Configuration: `/config`
- Application data: Database/settings
- SSL certificates: `/etc/letsencrypt`

**Automated Backup Script**:
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup videos (if manageable size)
if [ $(du -s /data/Videos | cut -f1) -lt 10000000 ]; then
    tar -czf "$BACKUP_DIR/videos.tar.gz" -C /data Videos/
fi

# Backup configuration
tar -czf "$BACKUP_DIR/config.tar.gz" -C /config .

# Backup nginx config
tar -czf "$BACKUP_DIR/nginx.tar.gz" -C /etc/nginx .

# Upload to cloud storage (optional)
rclone copy "$BACKUP_DIR" remote:backup/hometube/
```

**Database Backup** (if using):
```bash
# PostgreSQL
pg_dump videos_downloader > backup.sql

# SQLite
sqlite3 app.db .dump > backup.sql
```

### Disaster Recovery

**Recovery Procedure**:
```bash
# 1. Stop services
docker-compose down

# 2. Restore data
tar -xzf backup/config.tar.gz -C /config
tar -xzf backup/videos.tar.gz -C /data

# 3. Restore configuration
tar -xzf backup/nginx.tar.gz -C /etc/nginx

# 4. Restart services
docker-compose up -d

# 5. Verify functionality
curl -f http://localhost:8501/_stcore/health
```

## 🔄 Updates & Maintenance

### Automatic Updates

**Watchtower for Container Updates**:
```yaml
# docker-compose.yml addition
watchtower:
  image: containrrr/watchtower
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
  environment:
    - WATCHTOWER_CLEANUP=true
    - WATCHTOWER_POLL_INTERVAL=3600
    - WATCHTOWER_INCLUDE_STOPPED=true
```

**Manual Update Process**:
```bash
# Update to latest version
./deploy.sh latest --backup

# Update to specific version
./deploy.sh v1.2.0 --backup

# Rollback if needed
./deploy.sh v1.1.0 --no-backup
```

### Maintenance Tasks

**Regular Maintenance**:
```bash
# Clean old containers and images
docker system prune -a

# Rotate logs
logrotate /etc/logrotate.d/docker

# Update system packages
sudo apt update && sudo apt upgrade

# Check disk space
df -h
du -sh /data/Videos
```

**Performance Optimization**:
```bash
# Monitor resource usage
docker stats

# Optimize video storage
find /data/Videos -name "*.tmp" -delete
find /data/Videos -empty -type d -delete

# Check for errors in logs
docker logs hometube --tail 100
```

## 📋 Production Checklist

### Pre-Deployment

- [ ] Domain name configured and DNS propagated
- [ ] SSL certificate obtained and configured
- [ ] Firewall rules configured
- [ ] Backup strategy implemented
- [ ] Monitoring set up
- [ ] Performance testing completed
- [ ] Security scan performed

### Post-Deployment

- [ ] Health check endpoints responding
- [ ] SSL/HTTPS working correctly
- [ ] Authentication functioning (if enabled)
- [ ] Video downloads working
- [ ] Logs being captured
- [ ] Backup restoration tested
- [ ] Performance monitoring active
- [ ] Documentation updated with specific configurations

### Ongoing Maintenance

- [ ] Weekly backup verification
- [ ] Monthly security updates
- [ ] Quarterly performance review
- [ ] Semi-annual disaster recovery testing
- [ ] Annual security audit

---

**Previous: [Development Guide](development.md)** | **Next: [Installation Guide](installation.md)**