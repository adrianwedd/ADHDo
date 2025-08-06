# MCP ADHD Server - Deployment Guide 🚀

> **TL;DR for ADHD minds**: Three ways to deploy: Docker (easiest), manual setup (full control), or cloud platforms. All include step-by-step instructions with no overwhelm! 

Complete deployment guide for getting your ADHD support server running in production.

## 🎯 Deployment Options

**TL;DR**: Pick what works for your brain:

1. **🐳 Docker**: One command, everything works
2. **⚙️ Manual**: Full control, more steps  
3. **☁️ Cloud**: Managed hosting, less maintenance

## 🐳 Option 1: Docker Deployment (Recommended)

**TL;DR**: Copy, paste, edit .env, run one command. Done in 5 minutes.

### Prerequisites
- Docker and Docker Compose installed
- Domain name (for HTTPS)
- 2GB+ RAM, 10GB+ disk space

### Quick Setup

```bash
# 1. Clone the repository
git clone https://github.com/adrianwedd/ADHDo.git
cd ADHDo

# 2. Copy environment template
cp .env.example .env

# 3. Edit .env file with your settings
nano .env
```

### Required Environment Variables

**TL;DR**: These are the minimum you MUST set:

```bash
# OpenAI API Key (required for AI chat)
OPENAI_API_KEY=sk-your-openai-key-here

# Database URL (PostgreSQL)
DATABASE_URL=postgresql://adhd_user:secure_password@db:5432/adhd_db

# Redis Cache
REDIS_URL=redis://redis:6379/0

# Security (generate a random 32-character string)
SECRET_KEY=your-super-secret-key-32-characters-long

# Domain and SSL
DOMAIN=your-domain.com
SSL_EMAIL=your-email@domain.com
```

### Optional but Recommended

```bash
# Telegram Bot (for mobile support)
TELEGRAM_BOT_TOKEN=123456789:ABC-DEF-your-telegram-bot-token

# Monitoring
ENABLE_METRICS=true
LOG_LEVEL=INFO
```

### Launch the Server

```bash
# Start everything (database, redis, web server, monitoring)
docker-compose up -d

# Check logs to make sure everything started
docker-compose logs -f adhd-server

# Test the deployment
curl https://your-domain.com/health
```

### SSL Certificate Setup

**TL;DR**: Automatic HTTPS with Let's Encrypt, no manual certificate management.

The Docker setup includes automatic SSL certificate generation via Let's Encrypt. Just make sure:

1. Your domain points to your server's IP
2. Ports 80 and 443 are open  
3. `DOMAIN` and `SSL_EMAIL` are set in `.env`

### Maintenance

```bash
# Update to latest version
docker-compose pull
docker-compose up -d

# Backup database
docker-compose exec db pg_dump -U adhd_user adhd_db > backup.sql

# View logs
docker-compose logs -f adhd-server

# Restart services
docker-compose restart
```

---

## ⚙️ Option 2: Manual Setup

**TL;DR**: More steps but full control. Good for developers who want to customize everything.

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Nginx (recommended)
- Supervisor (for process management)

### System Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip
sudo apt install -y postgresql postgresql-contrib redis-server
sudo apt install -y nginx supervisor

# Create database
sudo -u postgres createdb adhd_db
sudo -u postgres createuser adhd_user
sudo -u postgres psql -c "ALTER USER adhd_user WITH PASSWORD 'secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE adhd_db TO adhd_user;"
```

### Application Setup

```bash
# 1. Clone and setup application
git clone https://github.com/adrianwedd/ADHDo.git
cd ADHDo

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your settings

# 4. Initialize database
alembic upgrade head

# 5. Test the application
cd src
PYTHONPATH=. python -m uvicorn mcp_server.main:app --host 0.0.0.0 --port 8000
```

### Process Management (Supervisor)

Create `/etc/supervisor/conf.d/adhd-server.conf`:

```ini
[program:adhd-server]
directory=/path/to/ADHDo/src
command=/path/to/ADHDo/venv/bin/python -m uvicorn mcp_server.main:app --host 127.0.0.1 --port 8000
environment=PYTHONPATH=/path/to/ADHDo/src
user=www-data
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=60
stdout_logfile=/var/log/adhd-server.log
stderr_logfile=/var/log/adhd-server-error.log
```

```bash
# Start the service
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start adhd-server
```

### Nginx Configuration

Create `/etc/nginx/sites-available/adhd-server`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Configuration (use certbot for Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # Main application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (for future features)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeout for ADHD-friendly response times
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
    
    # Static files
    location /static {
        alias /path/to/ADHDo/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/adhd-server /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

---

## ☁️ Option 3: Cloud Platform Deployment

**TL;DR**: Deploy to major cloud platforms with pre-configured templates. Less setup, more reliability.

### Railway (Recommended for beginners)

**TL;DR**: Connect GitHub, set environment variables, deploy automatically.

1. Fork the repository to your GitHub
2. Visit [railway.app](https://railway.app) and connect GitHub
3. Create new project from your fork
4. Add environment variables in Railway dashboard
5. Deploy automatically on every git push

### DigitalOcean App Platform

**TL;DR**: One-click deploy with managed database and Redis.

1. Click "Deploy to DigitalOcean" button (add to your repo)
2. Configure environment variables
3. Choose managed PostgreSQL and Redis
4. Deploy and scale automatically

### Heroku

```bash
# Install Heroku CLI
heroku create your-app-name

# Add managed Postgres and Redis
heroku addons:create heroku-postgresql:mini
heroku addons:create heroku-redis:mini

# Set environment variables
heroku config:set OPENAI_API_KEY=sk-your-key
heroku config:set SECRET_KEY=your-secret-key

# Deploy
git push heroku main
```

### AWS/GCP/Azure

**TL;DR**: Use container services for easy scaling and management.

- **AWS**: ECS with RDS and ElastiCache
- **Google Cloud**: Cloud Run with Cloud SQL and Memorystore  
- **Azure**: Container Instances with PostgreSQL and Redis Cache

---

## 📊 Production Optimization

**TL;DR**: Settings to make your ADHD server fast, reliable, and scalable.

### Performance Tuning

```bash
# Environment variables for production
export WORKERS=4  # CPU cores * 2
export MAX_CONNECTIONS=100
export KEEP_ALIVE=2
export TIMEOUT=30

# Start with optimized settings
uvicorn mcp_server.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers $WORKERS \
  --timeout-keep-alive $KEEP_ALIVE
```

### Database Optimization

```sql
-- PostgreSQL optimization for ADHD workloads
-- Add to postgresql.conf

# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB

# Connection settings
max_connections = 100

# Performance settings
random_page_cost = 1.1  # For SSD storage
checkpoint_completion_target = 0.9
```

### Redis Configuration

```redis
# redis.conf optimizations
maxmemory 512mb
maxmemory-policy allkeys-lru
timeout 300
tcp-keepalive 60
```

---

## 🔍 Monitoring & Alerting

**TL;DR**: Built-in health checks, Prometheus metrics, and Grafana dashboards for keeping your ADHD server healthy.

### Health Checks

```bash
# Basic health check
curl https://your-domain.com/health

# Detailed system status  
curl https://your-domain.com/health/detailed

# Prometheus metrics
curl https://your-domain.com/metrics
```

### Grafana Dashboard

The Docker deployment includes a pre-configured Grafana dashboard with ADHD-specific metrics:

- Response time percentiles (P50, P95, P99)
- User session duration
- Crisis detection triggers
- API endpoint performance
- Database and Redis health

Access at: `https://your-domain.com:3000` (admin/admin)

### Custom Alerts

```yaml
# alertmanager.yml - Sample ADHD-focused alerts
groups:
- name: adhd_server
  rules:
  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 3
    for: 2m
    annotations:
      summary: "ADHD server response time too high - may affect user focus"
      
  - alert: DatabaseConnections
    expr: postgresql_connections > 80
    annotations:
      summary: "High database load - may impact ADHD user experience"
```

---

## 🔒 Security & Backup

**TL;DR**: Essential security settings and backup procedures for protecting ADHD user data.

### Security Checklist

**TL;DR**: Must-have security for ADHD user data protection.

- [ ] HTTPS enabled with valid SSL certificate
- [ ] Strong SECRET_KEY (32+ characters)
- [ ] Database passwords are strong and unique
- [ ] Rate limiting enabled to prevent abuse
- [ ] Regular security updates applied
- [ ] Backup strategy implemented
- [ ] Monitoring and alerting configured

### Backup Strategy

```bash
# Automated database backup script
#!/bin/bash
# save as /etc/cron.daily/backup-adhd-db

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/adhd-server"
mkdir -p $BACKUP_DIR

# Database backup
docker-compose exec -T db pg_dump -U adhd_user adhd_db | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Redis backup (if needed)
docker-compose exec -T redis redis-cli BGSAVE
docker cp $(docker-compose ps -q redis):/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Keep only last 30 days
find $BACKUP_DIR -type f -mtime +30 -delete

# Upload to cloud storage (optional)
# aws s3 cp $BACKUP_DIR/ s3://your-backup-bucket/ --recursive
```

### SSL Certificate Renewal

```bash
# Automatic renewal (already configured in Docker setup)
# For manual setups, add to crontab:
0 12 * * * /usr/bin/certbot renew --quiet
```

---

## 🐛 Troubleshooting

**TL;DR**: Common problems and quick fixes for ADHD server deployment.

### Server Won't Start

```bash
# Check logs
docker-compose logs adhd-server

# Common issues:
# 1. Database not ready - wait 30 seconds and retry
# 2. Port already in use - change port in docker-compose.yml  
# 3. Missing environment variables - check .env file
```

### Slow Response Times

```bash
# Check system resources
docker stats

# Common fixes:
# 1. Increase server resources (RAM/CPU)
# 2. Optimize database queries
# 3. Add Redis caching
# 4. Check network connectivity
```

### Database Connection Issues

```bash
# Test database connection
docker-compose exec db psql -U adhd_user -d adhd_db -c "SELECT NOW();"

# Reset database if needed
docker-compose down
docker volume rm adhd_database_data
docker-compose up -d
```

### SSL Certificate Problems

```bash
# Check certificate status
openssl x509 -in /etc/letsencrypt/live/your-domain.com/fullchain.pem -text -noout

# Renew certificate
docker-compose exec nginx certbot renew
```

---

## 📞 Support & Maintenance

**TL;DR**: How to keep your ADHD server running smoothly and get help when needed.

### Regular Maintenance

**Weekly Tasks (5 minutes):**
- [ ] Check server health: `curl your-domain.com/health`
- [ ] Review error logs: `docker-compose logs --tail=100`
- [ ] Verify backups are working

**Monthly Tasks (15 minutes):**
- [ ] Update Docker images: `docker-compose pull && docker-compose up -d`
- [ ] Review monitoring dashboards
- [ ] Test disaster recovery procedure

### Getting Help

**TL;DR**: Multiple ways to get support for your ADHD server.

1. **📚 Documentation**: Check `/docs` endpoint on your server
2. **🐛 GitHub Issues**: Report bugs and request features
3. **💬 Community**: Join ADHD developer community (link)
4. **📧 Email**: Support for production deployments

### Performance Monitoring

Your ADHD server includes built-in performance monitoring optimized for ADHD users:

- **Response Time Tracking**: Alerts if responses >3s (critical for ADHD)
- **User Session Monitoring**: Track engagement patterns
- **Crisis Detection Metrics**: Monitor intervention effectiveness
- **Resource Usage**: Ensure server can handle user load

---

## 🎯 Production Readiness Checklist

**TL;DR**: Final checklist before going live with ADHD users.

### Infrastructure
- [ ] Server resources adequate (2GB+ RAM, 2+ CPU cores)
- [ ] Database configured with backups
- [ ] SSL certificate installed and auto-renewing
- [ ] Monitoring and alerting configured
- [ ] Load balancing (if multiple servers)

### Security
- [ ] All environment variables secured
- [ ] Rate limiting configured
- [ ] HTTPS enforced
- [ ] Security headers configured
- [ ] Regular backup testing

### ADHD-Specific
- [ ] Response times <3 seconds (95th percentile)
- [ ] Error messages are supportive and helpful
- [ ] Mobile experience optimized
- [ ] Crisis detection system tested
- [ ] Overwhelm detection calibrated

### Testing
- [ ] Phase 0 beta testing passed
- [ ] Load testing completed
- [ ] Security scan performed
- [ ] Accessibility testing completed
- [ ] Mobile device testing done

**Ready to launch your ADHD support server!** 🚀

---

*Built with 🧠 for ADHD minds everywhere. Making executive function support accessible and effective.*