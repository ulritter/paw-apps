#!/bin/bash

# Renew Let's Encrypt SSL certificates
# This script should be run periodically (e.g., via cron) to renew certificates

set -e

echo "Attempting to renew Let's Encrypt certificates..."

# Renew certificates
docker-compose -f docker-compose.yml run --rm certbot renew

# Reload nginx to use new certificates
docker-compose -f docker-compose.yml exec nginx nginx -s reload

echo "Certificate renewal completed!"
