#!/bin/bash

# PAW Systems - Unified Platform Startup Script

set -e

# Determine environment (default to dev)
ENV=${1:-dev}

if [ "$ENV" != "dev" ] && [ "$ENV" != "prod" ]; then
    echo "❌ Error: Invalid environment '$ENV'"
    echo "Usage: $0 [dev|prod]"
    echo "  dev  - Development environment (ports 8080/8443)"
    echo "  prod - Production environment (ports 80/443, requires SSL)"
    exit 1
fi

echo "🚀 PAW Systems - Starting Unified Platform ($ENV)"
echo "=========================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "📝 Please create .env from .env.example:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running!"
    echo "   Please start Docker Desktop and try again."
    exit 1
fi

# Load environment variables
source .env

# Check critical environment variables
if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "change-this-secret-key-to-something-random" ]; then
    echo "⚠️  Warning: SECRET_KEY not configured!"
    echo "   Please set a random SECRET_KEY in .env"
fi

if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "your-anthropic-api-key-here" ]; then
    echo "⚠️  Warning: ANTHROPIC_API_KEY not configured!"
    echo "   PDF Converter will not work without a valid API key"
fi

# Production-specific checks
if [ "$ENV" = "prod" ]; then
    if [ -z "$DOMAIN_NAME" ] || [ "$DOMAIN_NAME" = "your-domain.com" ]; then
        echo "❌ Error: DOMAIN_NAME not configured for production!"
        echo "   Please set DOMAIN_NAME in .env"
        exit 1
    fi
    
    if [ -z "$CERTBOT_EMAIL" ] || [ "$CERTBOT_EMAIL" = "your-email@example.com" ]; then
        echo "❌ Error: CERTBOT_EMAIL not configured for production!"
        echo "   Please set CERTBOT_EMAIL in .env"
        exit 1
    fi
    
    echo "🔒 Production mode: SSL certificates will be managed by Let's Encrypt"
    echo "   Domain: $DOMAIN_NAME"
fi

# Set compose file based on environment
if [ "$ENV" = "dev" ]; then
    COMPOSE_FILE="docker-compose-dev.yml"
else
    COMPOSE_FILE="docker-compose.yml"
fi

echo ""
echo "📦 Building and starting services with $COMPOSE_FILE..."
echo ""

# Build and start services
docker compose -f $COMPOSE_FILE up --build -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check service health
echo ""
echo "🔍 Checking service status..."
docker compose -f $COMPOSE_FILE ps

echo ""
echo "✅ PAW Systems is starting up!"
echo ""

# Show appropriate URLs based on environment
if [ "$ENV" = "dev" ]; then
    echo "📍 Access Points (Development):"
    echo "   - Landing Page:  http://localhost:8080"
    echo "   - Login:         http://localhost:8080/login.html"
    echo "   - Crawler:       http://localhost:8080/crawler/"
    echo "   - Converter:     http://localhost:8080/converter/"
else
    echo "📍 Access Points (Production):"
    echo "   - Landing Page:  https://$DOMAIN_NAME"
    echo "   - Login:         https://$DOMAIN_NAME/login.html"
    echo "   - Crawler:       https://$DOMAIN_NAME/crawler/"
    echo "   - Converter:     https://$DOMAIN_NAME/converter/"
    echo ""
    echo "⚠️  Note: First-time setup requires running SSL initialization:"
    echo "   ./scripts/init-letsencrypt.sh"
fi

echo ""
echo "📊 Management:"
echo "   - View logs:     docker compose -f $COMPOSE_FILE logs -f"
echo "   - Stop:          docker compose -f $COMPOSE_FILE down"
echo "   - Restart:       docker compose -f $COMPOSE_FILE restart"
echo ""
echo "📝 Next Steps:"
echo "   1. Add users to database (see README.md)"
echo "   2. Configure SMTP for email authentication"
echo "   3. Set ANTHROPIC_API_KEY for PDF converter"

if [ "$ENV" = "prod" ]; then
    echo "   4. Set up SSL certificate renewal cron job (see docs/SSL_SETUP.md)"
fi

echo ""
echo "🎉 Happy crawling and converting!"
