# Deployment Environments

PAW Systems supports two deployment environments: **Development** and **Production**.

## Quick Start

```bash
# Development (default)
./start.sh dev

# Production
./start.sh prod
```

## Development Environment

### Configuration
- **Compose file**: `docker-compose-dev.yml`
- **Ports**: 10080 (HTTP), 10443 (HTTPS)
- **SSL**: Optional, uses self-signed certificates from `./ssl/`
- **Domain**: localhost

### Usage
```bash
# Start development environment
./start.sh dev
# or simply
./start.sh

# Access points
http://localhost:10080
http://localhost:10080/crawler/
http://localhost:10080/converter/
```

### Features
- Non-standard ports to avoid conflicts
- No SSL certificate validation required
- Suitable for local development and testing
- Can run alongside other local services

## Production Environment

### Configuration
- **Compose file**: `docker-compose.yml`
- **Ports**: 80 (HTTP), 443 (HTTPS)
- **SSL**: Required, managed by Let's Encrypt
- **Domain**: Configured via `DOMAIN_NAME` in `.env`

### Prerequisites
1. A registered domain name
2. Domain DNS pointing to server IP
3. Ports 80 and 443 open on firewall
4. Environment variables configured:
   ```bash
   DOMAIN_NAME=your-domain.com
   CERTBOT_EMAIL=your-email@example.com
   ```

### Initial Setup
```bash
# 1. Configure .env with production values
nano .env

# 2. Initialize SSL certificates (first time only)
./scripts/init-letsencrypt.sh

# 3. Start production environment
./start.sh prod
```

### Access Points
```
https://your-domain.com
https://your-domain.com/crawler/
https://your-domain.com/converter/
```

### Features
- Automatic SSL certificate management
- HTTPS-only (HTTP redirects to HTTPS)
- Production-grade security headers
- Rate limiting enabled
- OCSP stapling for better SSL performance

## Environment Comparison

| Feature | Development | Production |
|---------|-------------|------------|
| Compose File | `docker-compose-dev.yml` | `docker-compose.yml` |
| HTTP Port | 10080 | 80 |
| HTTPS Port | 10443 | 443 |
| SSL Certificates | Self-signed (optional) | Let's Encrypt (required) |
| Domain | localhost | Custom domain |
| SSL Validation | No | Yes |
| Certificate Renewal | Manual | Automatic |
| Security Headers | Basic | Enhanced |
| Rate Limiting | Disabled | Enabled |

## Switching Environments

### From Dev to Prod
```bash
# Stop dev environment
docker compose -f docker-compose-dev.yml down

# Configure production settings
nano .env  # Set DOMAIN_NAME and CERTBOT_EMAIL

# Initialize SSL
./scripts/init-letsencrypt.sh

# Start production
./start.sh prod
```

### From Prod to Dev
```bash
# Stop production
docker compose -f docker-compose.yml down

# Start development
./start.sh dev
```

## Common Commands

### Development
```bash
# Start
./start.sh dev

# View logs
docker compose -f docker-compose-dev.yml logs -f

# Stop
docker compose -f docker-compose-dev.yml down

# Restart specific service
docker compose -f docker-compose-dev.yml restart nginx
```

### Production
```bash
# Start
./start.sh prod

# View logs
docker compose -f docker-compose.yml logs -f

# Stop
docker compose -f docker-compose.yml down

# Restart specific service
docker compose -f docker-compose.yml restart nginx

# Renew SSL certificates
./scripts/renew-certificates.sh
```

## Troubleshooting

### Development Issues

**Port already in use**
```bash
# Check what's using the port
lsof -i :10080

# Use different ports by modifying docker-compose-dev.yml
```

**SSL certificate errors**
- Development doesn't require valid SSL certificates
- Browser warnings for self-signed certs are expected

### Production Issues

**SSL certificate not working**
- Ensure domain DNS is correctly configured
- Check firewall allows ports 80 and 443
- Verify `DOMAIN_NAME` matches actual domain
- Run `./scripts/init-letsencrypt.sh` if certificates missing

**Cannot access via HTTPS**
- Check nginx logs: `docker compose logs nginx`
- Verify certificates exist: `docker compose exec nginx ls -la /etc/letsencrypt/live/`
- Ensure HTTP redirects to HTTPS

**Rate limiting errors**
- Production has rate limits enabled
- Adjust in `nginx/nginx.conf` if needed for your use case

## Best Practices

### Development
1. Use dev environment for all local testing
2. Don't commit `.env` file
3. Use `docker-compose-dev.yml` for custom dev configurations
4. Test SSL locally with self-signed certificates if needed

### Production
1. Always use strong `SECRET_KEY` and passwords
2. Set up SSL certificate auto-renewal cron job
3. Monitor certificate expiration
4. Keep Docker images updated
5. Regular backups of database and certificates
6. Use environment-specific `.env` files (never commit to git)

## Security Considerations

### Development
- Exposed on non-standard ports
- Suitable for trusted networks only
- Not intended for public internet access

### Production
- HTTPS enforced
- Strong SSL configuration (TLS 1.2+)
- Security headers enabled
- Rate limiting active
- Regular security updates required

## Additional Resources

- [SSL Setup Guide](./SSL_SETUP.md)
- [Main README](../README.md)
- [Deployment Checklist](../DEPLOYMENT_CHECKLIST.md)
