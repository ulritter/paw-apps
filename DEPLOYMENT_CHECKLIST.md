# PAW Systems - Deployment Checklist

## Pre-Deployment

### Environment Configuration
- [ ] Copy `.env.example` to `.env`
- [ ] Generate random `SECRET_KEY` (use: `openssl rand -hex 32`)
- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Configure `SMTP_*` settings for email
- [ ] Add `ANTHROPIC_API_KEY` for PDF converter
- [ ] Review and adjust `MAX_FILE_SIZE` if needed
- [ ] Set `DEBUG_MODE=false` for production

### Security
- [ ] Verify `SECRET_KEY` is random and secure
- [ ] Ensure `.env` is in `.gitignore`
- [ ] Review nginx security headers
- [ ] Configure SSL certificates (optional but recommended)
- [ ] Set up firewall rules
- [ ] Review rate limiting settings

### Infrastructure
- [ ] Docker and Docker Compose installed
- [ ] Sufficient disk space for database
- [ ] Network ports 80 and 443 available
- [ ] SMTP server accessible
- [ ] Anthropic API accessible

## Deployment

### Initial Setup
- [ ] Clone repository
- [ ] Configure `.env` file
- [ ] Make scripts executable: `chmod +x start.sh add-user.sh`
- [ ] Review `docker-compose.yml` for any environment-specific changes

### Start Services
- [ ] Run `./start.sh`
- [ ] Verify all 8 services are running: `docker compose ps`
- [ ] Check logs for errors: `docker compose logs -f`
- [ ] Wait for database to be ready (health check)

### Database Setup
- [ ] Verify database tables created
- [ ] Add first admin user: `./add-user.sh admin@paw-systems.com`
- [ ] Test database connectivity

### Application Testing
- [ ] Access landing page: http://localhost
- [ ] Test login flow
- [ ] Verify email delivery
- [ ] Access crawler: http://localhost/crawler/
- [ ] Access converter: http://localhost/converter/
- [ ] Test crawler job fetching
- [ ] Test PDF conversion
- [ ] Verify logout works

## Post-Deployment

### Monitoring
- [ ] Set up log monitoring
- [ ] Configure health check monitoring
- [ ] Set up disk space alerts
- [ ] Monitor database size
- [ ] Track API usage

### Backups
- [ ] Configure automated database backups
- [ ] Test backup restoration
- [ ] Document backup procedures
- [ ] Set up off-site backup storage

### Documentation
- [ ] Document custom configurations
- [ ] Create runbook for common issues
- [ ] Document user onboarding process
- [ ] Create admin procedures

### User Management
- [ ] Add all required users
- [ ] Test user authentication
- [ ] Verify email notifications
- [ ] Document user management procedures

## Production Checklist

### Security (Production)
- [ ] Enable HTTPS (SSL/TLS)
- [ ] Configure proper CORS origins (not `*`)
- [ ] Set up fail2ban or similar
- [ ] Enable audit logging
- [ ] Review and harden nginx configuration
- [ ] Implement IP whitelisting if needed
- [ ] Set up intrusion detection

### Performance
- [ ] Configure nginx caching
- [ ] Set up CDN for static assets (optional)
- [ ] Optimize database indexes
- [ ] Configure connection pooling
- [ ] Set appropriate resource limits

### Reliability
- [ ] Set up health check endpoints
- [ ] Configure automatic restarts
- [ ] Set up alerting
- [ ] Document disaster recovery procedures
- [ ] Test failover scenarios

### Compliance
- [ ] Review data retention policies
- [ ] Configure log retention
- [ ] Document data handling procedures
- [ ] Ensure GDPR compliance (if applicable)
- [ ] Review privacy policy

## Maintenance

### Regular Tasks
- [ ] Weekly: Review logs for errors
- [ ] Weekly: Check disk space
- [ ] Weekly: Review user activity
- [ ] Monthly: Update dependencies
- [ ] Monthly: Review and rotate secrets
- [ ] Monthly: Test backup restoration
- [ ] Quarterly: Security audit
- [ ] Quarterly: Performance review

### Updates
- [ ] Document update procedures
- [ ] Test updates in staging first
- [ ] Plan maintenance windows
- [ ] Notify users of downtime
- [ ] Keep changelog updated

## Troubleshooting Checklist

### Services Won't Start
- [ ] Check Docker is running
- [ ] Verify `.env` file exists and is valid
- [ ] Check port availability
- [ ] Review docker compose logs
- [ ] Verify disk space

### Authentication Issues
- [ ] Verify SMTP configuration
- [ ] Check user exists in database
- [ ] Verify SECRET_KEY is set
- [ ] Check email delivery logs
- [ ] Review auth_codes table

### Database Issues
- [ ] Check database is running
- [ ] Verify connection string
- [ ] Check database logs
- [ ] Verify disk space
- [ ] Test database connectivity

### Application Errors
- [ ] Check application logs
- [ ] Verify API keys are set
- [ ] Check network connectivity
- [ ] Review nginx error logs
- [ ] Verify file permissions

## Rollback Plan

### If Deployment Fails
- [ ] Document the issue
- [ ] Stop services: `docker compose down`
- [ ] Restore database from backup
- [ ] Revert to previous version
- [ ] Investigate root cause
- [ ] Update deployment procedures

## Sign-Off

### Deployment Team
- [ ] Technical Lead approval
- [ ] Security review completed
- [ ] Documentation reviewed
- [ ] Backup procedures tested
- [ ] Monitoring configured

### Stakeholders
- [ ] Users notified
- [ ] Training completed
- [ ] Support team briefed
- [ ] Documentation distributed

---

## Quick Commands Reference

```bash
# Start services
./start.sh

# Stop services
docker compose down

# View logs
docker compose logs -f

# Add user
./add-user.sh user@paw-systems.com

# Restart service
docker compose restart [service-name]

# Database backup
docker compose exec db pg_dump -U pawuser pawsystems > backup.sql

# Database restore
docker compose exec -T db psql -U pawuser pawsystems < backup.sql

# Check service status
docker compose ps

# View resource usage
docker stats
```

---

**Deployment Date:** _________________

**Deployed By:** _________________

**Version:** _________________

**Notes:** _________________
