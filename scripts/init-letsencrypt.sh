#!/bin/bash

# Initialize Let's Encrypt SSL certificates for production
# This script should be run once before starting the production environment

set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Error: .env file not found"
    exit 1
fi

# Check required environment variables
if [ -z "$DOMAIN_NAME" ]; then
    echo "Error: DOMAIN_NAME not set in .env"
    exit 1
fi

if [ -z "$CERTBOT_EMAIL" ]; then
    echo "Error: CERTBOT_EMAIL not set in .env"
    exit 1
fi

echo "Initializing Let's Encrypt for domain: $DOMAIN_NAME"
echo "Email: $CERTBOT_EMAIL"

# Create temporary nginx config for initial certificate request
mkdir -p nginx/temp
cat > nginx/temp/init.conf << 'EOF'
server {
    listen 80;
    server_name _;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 200 "OK";
        add_header Content-Type text/plain;
    }
}
EOF

echo "Starting nginx with temporary configuration..."
docker-compose -f docker-compose.yml up -d nginx

# Wait for nginx to be ready
sleep 5

echo "Requesting Let's Encrypt certificate..."
docker-compose -f docker-compose.yml run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/html \
    --email $CERTBOT_EMAIL \
    --agree-tos \
    --no-eff-email \
    --staging \
    -d $DOMAIN_NAME

echo ""
echo "Certificate request completed!"
echo ""
echo "If the staging certificate was successful, run this script again with production certificates:"
echo "Remove the --staging flag from the certbot command in this script."
echo ""
echo "Then restart with the full configuration:"
echo "docker-compose -f docker-compose.yml down"
echo "docker-compose -f docker-compose.yml up -d"
