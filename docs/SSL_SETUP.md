# SSL Certificate Setup with Let's Encrypt

This guide explains how to set up automatic SSL certificates using Let's Encrypt for production deployment.

## Prerequisites

1. A registered domain name pointing to your server's IP address
2. Ports 80 and 443 open on your server firewall
3. Docker and Docker Compose installed

## Environment Variables

Add the following variables to your `.env` file:

```bash
# Domain Configuration
DOMAIN_NAME=your-domain.com
CERTBOT_EMAIL=your-email@example.com
```

Replace:
- `your-domain.com` with your actual domain name
- `your-email@example.com` with your email address (for Let's Encrypt notifications)

## Initial Setup

### Step 1: Test with Staging Certificates

First, test the setup with Let's Encrypt staging certificates to avoid rate limits:

```bash
chmod +x scripts/init-letsencrypt.sh
./scripts/init-letsencrypt.sh
```

This script will:
1. Start nginx with a temporary configuration
2. Request a staging certificate from Let's Encrypt
3. Verify the domain ownership

### Step 2: Get Production Certificates

Once staging works, modify `scripts/init-letsencrypt.sh`:
- Remove the `--staging` flag from the certbot command (line 58)

Then run:

```bash
./scripts/init-letsencrypt.sh
```

### Step 3: Start Production Environment

```bash
docker-compose -f docker-compose.yml down
docker-compose -f docker-compose.yml up -d
```

## Certificate Renewal

Let's Encrypt certificates expire after 90 days. Set up automatic renewal:

### Manual Renewal

```bash
chmod +x scripts/renew-certificates.sh
./scripts/renew-certificates.sh
```

### Automatic Renewal with Cron

Add to crontab (runs twice daily):

```bash
crontab -e
```

Add this line:

```
0 0,12 * * * cd /path/to/paw-apps && ./scripts/renew-certificates.sh >> /var/log/letsencrypt-renew.log 2>&1
```

Replace `/path/to/paw-apps` with your actual project path.

## Architecture

### Docker Compose Changes

The production `docker-compose.yml` includes:

1. **Certbot Service**: Handles certificate requests and renewals
2. **Nginx Volumes**: 
   - `certbot-etc`: Stores Let's Encrypt certificates
   - `certbot-var`: Certbot working directory
   - `web-root`: ACME challenge directory

### Nginx Configuration

The nginx configuration includes:

1. **HTTP Server (Port 80)**:
   - Handles Let's Encrypt ACME challenges at `/.well-known/acme-challenge/`
   - Redirects all other traffic to HTTPS

2. **HTTPS Server (Port 443)**:
   - Uses Let's Encrypt certificates
   - Modern TLS configuration (TLS 1.2 and 1.3)
   - Strong cipher suites
   - OCSP stapling enabled

## Troubleshooting

### Certificate Request Fails

1. **DNS not propagated**: Ensure your domain points to the server IP
   ```bash
   nslookup your-domain.com
   ```

2. **Firewall blocking**: Check ports 80 and 443 are open
   ```bash
   sudo ufw status
   ```

3. **Rate limits**: Use staging certificates for testing

### Nginx Fails to Start

1. **Check certificate paths**:
   ```bash
   docker-compose exec nginx ls -la /etc/letsencrypt/live/
   ```

2. **View nginx logs**:
   ```bash
   docker-compose logs nginx
   ```

### Certificate Not Renewing

1. **Check certbot logs**:
   ```bash
   docker-compose logs certbot
   ```

2. **Manually test renewal**:
   ```bash
   docker-compose run --rm certbot renew --dry-run
   ```

## Security Best Practices

1. **Keep certificates secure**: Never commit certificates to version control
2. **Monitor expiration**: Set up email notifications via `CERTBOT_EMAIL`
3. **Regular updates**: Keep Docker images updated
4. **Backup certificates**: Backup the `certbot-etc` volume regularly

## Development vs Production

- **Development** (`docker-compose-dev.yml`): Uses ports 10080/10443, no SSL required
- **Production** (`docker-compose.yml`): Uses ports 80/443 with Let's Encrypt SSL

## Additional Resources

- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Certbot Documentation](https://certbot.eff.org/docs/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
