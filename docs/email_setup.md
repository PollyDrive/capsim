# 📧 Email Setup for Grafana Alerting

## Quick Setup

### 1. Gmail App Password Setup
1. Enable 2FA in your Gmail account (required for app passwords)
2. Go to [Google Account Security](https://myaccount.google.com/security)
3. Under "2-Step Verification", click "App passwords"
4. Generate a new app password for "Mail"
5. Copy the 16-character password (no spaces)

### 2. Update .env File
Add these lines to your `.env` file:

```bash
# Email configuration for Grafana alerting
GRAFANA_SMTP_USER=your-email@gmail.com
GRAFANA_SMTP_PASSWORD=your-16-char-app-password
GRAFANA_SMTP_FROM=your-email@gmail.com
```

### 3. Update Docker Compose
The `docker-compose.yml` is already configured with these environment variables:

```yaml
environment:
  - GF_SMTP_ENABLED=true
  - GF_SMTP_HOST=smtp.gmail.com:587
  - GF_SMTP_USER=${GRAFANA_SMTP_USER}
  - GF_SMTP_PASSWORD=${GRAFANA_SMTP_PASSWORD}
  - GF_SMTP_FROM_ADDRESS=${GRAFANA_SMTP_FROM}
```

### 4. Restart Grafana
```bash
make restart-grafana
```

## Test Email Notifications

### Test with Makefile
```bash
make test-browser-push
```

### Manual Test
```bash
curl -X POST http://localhost:8001/api/notifications/browser-push \
  -H "Content-Type: application/json" \
  -d '{
    "title": "🧪 Test Alert",
    "body": "This is a test notification",
    "data": {
      "severity": "info",
      "dashboard_url": "http://localhost:3000/d/performance-tuning"
    }
  }'
```

## Email Providers

### Gmail (Recommended)
- **Host**: smtp.gmail.com:587
- **Security**: TLS (STARTTLS)
- **App Password**: Required (not your regular password)

### Outlook/Hotmail
- **Host**: smtp-mail.outlook.com:587
- **Security**: TLS (STARTTLS)
- **Authentication**: Regular password

### Custom SMTP
Update docker-compose.yml with your SMTP settings:

```yaml
environment:
  - GF_SMTP_HOST=your-smtp-server:587
  - GF_SMTP_USER=your-username
  - GF_SMTP_PASSWORD=your-password
```

## Alert Types

### Critical Alerts (Immediate)
- **Multiple Simulations**: CAPSIM architectural violation
- **CPU Temperature > 85°C**: Thermal throttling risk
- **Memory Pressure**: System running out of memory

### Warning Alerts (5-10 minutes)
- **IO Wait > 25%**: Disk performance issues
- **System Load > 2.0**: High system load
- **WAL Growth**: Database write activity spike

### Info Alerts (Monitoring)
- **Low HTTP Request Rate**: Application activity monitoring
- **WAL Size Growth**: Database write activity tracking

## Dashboard URLs

### Performance Tuning Dashboard
- **URL**: http://localhost:3000/d/performance-tuning
- **Features**: Real-time metrics, alert annotations, SLA tracking

### Browser Alerts Dashboard
- **URL**: http://localhost:8001
- **Features**: Live alerts, browser notifications, alert dismissal

### Grafana Alerting
- **URL**: http://localhost:3000/alerting
- **Features**: Alert rules, contact points, notification policies

## Troubleshooting

### No Emails Received
1. Check Gmail app password is correct
2. Verify 2FA is enabled in Gmail
3. Check Grafana logs: `docker-compose logs grafana`
4. Test SMTP connection manually

### Browser Notifications Not Working
1. Check browser notification permissions
2. Ensure browser-push server is running: `make start-browser-push`
3. Test endpoint: `make test-browser-push`

### Grafana Alerts Not Firing
1. Check Prometheus metrics availability
2. Verify alert rule queries in Grafana
3. Check alert evaluation frequency (30s default)

## Commands Reference

```bash
# Setup and management
make setup-grafana-alerting    # Show email setup instructions
make restart-grafana           # Restart Grafana service
make check-grafana-alerts      # Check alert rules status

# Browser notifications
make start-browser-push        # Start browser notification server
make stop-browser-push         # Stop browser notification server
make test-browser-push         # Test browser notifications
make open-alerts-dashboard     # Open alerts dashboard

# Help
make grafana-alerting-help     # Show all alerting commands
```

## Security Notes

⚠️ **Important**: 
- Never commit your actual email passwords to git
- Use app passwords, not regular passwords
- Keep your `.env` file in `.gitignore`
- Consider using environment-specific email accounts for alerts 