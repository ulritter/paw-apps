# PAW Systems - Unified Application Platform

A unified platform combining Freelance Job Crawler and AI-powered PDF Converter with shared authentication, database, and infrastructure.

## 🎯 Overview

This platform provides two powerful applications:

1. **Freelance Crawler** - Automated crawling of freelance projects from German job portals
2. **PDF Converter** - AI-powered PDF to Excel conversion using Claude AI

Both applications share:
- ✅ Unified authentication system (email-based with JWT)
- ✅ Single PostgreSQL database
- ✅ Nginx reverse proxy gateway
- ✅ Centralized configuration
- ✅ Consistent user experience

## 🏗️ Architecture

```
paw-apps/
├── docker-compose.yml          # Unified orchestration
├── .env                        # Configuration (create from .env.example)
├── nginx/                      # Reverse proxy
│   ├── Dockerfile
│   └── nginx.conf
├── frontend/                   # Landing page & login
│   ├── Dockerfile
│   ├── nginx.conf
│   └── public/
│       ├── index.html         # Landing page
│       ├── login.html         # Login page
│       └── pws-logo.png       # PAW Systems logo
├── freelance-crawler/          # Crawler application
│   ├── api/                   # FastAPI backend
│   ├── web/                   # Frontend
│   ├── crawlers/              # Selenium crawlers
│   └── ...
└── pdf-converter/              # PDF converter application
    ├── backend/               # FastAPI + Claude AI
    └── ...
```

## 🚀 Quick Start

### 1. Prerequisites

- Docker & Docker Compose
- Git

### 2. Clone & Configure

```bash
cd /Users/uritter/Development/Agentic/paw-apps

# Create environment file
cp .env.example .env

# Edit .env and configure:
# - Database credentials
# - SECRET_KEY (generate a random string)
# - SMTP settings (for email authentication)
# - ANTHROPIC_API_KEY (for PDF converter)
nano .env
```

### 3. Start Services

```bash
docker compose up --build
```

### 4. Access Applications

- **Landing Page**: http://localhost
- **Login**: http://localhost/login.html
- **Crawler**: http://localhost/crawler/
- **Converter**: http://localhost/converter/

## 🔐 Authentication

### User Management

Users must be added to the database manually:

```bash
# Connect to database
docker compose exec db psql -U pawuser -d pawsystems

# Add a user
INSERT INTO users (email, created_at) 
VALUES ('user@paw-systems.com', NOW());
```

### Login Flow

1. User enters email (@paw-systems.com domain required)
2. System sends 8-character code to email
3. User enters code to authenticate
4. JWT token stored in cookie (configurable expiry)

### Session Management

- Default session: 60 minutes
- Per-user session duration can be configured in database
- Global session duration configurable via settings table

## 📡 API Endpoints

### Crawler API (`/api/crawler/`)

- `POST /auth/send-code` - Request authentication code
- `POST /auth/verify-code` - Verify code and login
- `GET /auth/check` - Check authentication status
- `POST /auth/logout` - Logout
- `GET /jobs` - Get job listings
- `POST /crawler/run` - Trigger crawler manually
- `GET /crawler/progress` - Get crawler progress
- `GET /config` - Get configuration
- `POST /config/save` - Save configuration version

### Converter API (`/api/converter/`)

- `POST /convert` - Convert PDF to Excel (requires auth)
- `GET /health` - Health check

## 🔧 Configuration

### Environment Variables

See `.env.example` for all available options.

**Critical Settings:**

```bash
# Security
SECRET_KEY=your-random-secret-key-here

# Database
POSTGRES_PASSWORD=strong-password-here

# Email (for auth codes)
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# AI
ANTHROPIC_API_KEY=sk-ant-...
```

### Nginx Routing

- `/` → Landing page
- `/login.html` → Login page
- `/api/crawler/` → Crawler API
- `/api/converter/` → Converter API
- `/crawler/` → Crawler frontend
- `/converter/` → Converter frontend

### Rate Limiting

- API endpoints: 10 requests/second (burst: 20)
- Auth endpoints: 5 requests/minute

## 🛠️ Development

### Running Individual Services

```bash
# Crawler API only
docker compose up db crawler-api

# Converter API only
docker compose up db converter-api

# All services
docker compose up
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f crawler-api
docker compose logs -f converter-api
docker compose logs -f nginx
```

### Database Access

```bash
# Connect to PostgreSQL
docker compose exec db psql -U pawuser -d pawsystems

# View users
SELECT * FROM users;

# View jobs
SELECT source, COUNT(*) FROM jobs GROUP BY source;
```

## 📊 Database Schema

### Users Table

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    session_validity_minutes INTEGER,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Jobs Table

```sql
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    source TEXT,
    title TEXT,
    link TEXT UNIQUE,
    company TEXT,
    location TEXT,
    posted TEXT,
    posted_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE
);
```

### Auth Codes Table

```sql
CREATE TABLE auth_codes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    code TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Settings Table

```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## 🔍 Features

### Freelance Crawler

- **Multi-source crawling**: FreelancerMap, Solcom, Hays
- **Intelligent filtering**: Keyword-based job filtering
- **Automated scheduling**: Runs every 3 hours
- **Configuration management**: Version control for search configs
- **Job tracking**: Mark jobs as processed
- **Multiple views**: Table and card views with grouping options

### PDF Converter

- **AI-powered extraction**: Claude Sonnet 4.5 for intelligent data extraction
- **DATEV support**: Optimized for German payroll documents
- **Smart formatting**: Automatic Euro/cent column merging
- **German formatting**: Comma decimal separators
- **CSV export**: Export with German formatting

## 🐛 Troubleshooting

### Services Not Starting

```bash
# Check service status
docker compose ps

# View service logs
docker compose logs [service-name]

# Restart services
docker compose restart
```

### Authentication Issues

```bash
# Check if user exists
docker compose exec db psql -U pawuser -d pawsystems -c "SELECT * FROM users WHERE email='user@paw-systems.com';"

# Check SMTP configuration in .env
# Verify SECRET_KEY is set
```

### Database Connection Issues

```bash
# Check database is running
docker compose ps db

# Test connection
docker compose exec db psql -U pawuser -d pawsystems -c "SELECT 1;"
```

### Crawler Not Finding Jobs

```bash
# Enable debug mode
# In .env: DEBUG_MODE=true

# Check crawler logs
docker compose logs -f crawler

# View debug artifacts
ls -la freelance-crawler/debug_artifacts/
```

## 📝 Maintenance

### Backup Database

```bash
# Manual backup
docker compose exec db pg_dump -U pawuser pawsystems > backup_$(date +%Y%m%d).sql

# Restore from backup
docker compose exec -T db psql -U pawuser pawsystems < backup_20250101.sql
```

### Clean Old Jobs

```bash
# Delete jobs older than 30 days
docker compose exec db psql -U pawuser -d pawsystems -c \
  "DELETE FROM jobs WHERE created_at < NOW() - INTERVAL '30 days';"
```

### Update Configuration

```bash
# Edit crawler configuration
nano freelance-crawler/crawlers/search_config.json

# Restart crawler service
docker compose restart crawler crawler-api
```

## 🔒 Security

- **HTTPS**: Configure SSL certificates in `ssl/` directory
- **Secrets**: Never commit `.env` file
- **Database**: Use strong passwords
- **Email**: Use app-specific passwords for Gmail
- **API Keys**: Rotate regularly
- **Rate Limiting**: Configured in nginx

## 📄 License

MIT

## 🤝 Support

For issues or questions:
1. Check logs: `docker compose logs -f`
2. Verify configuration in `.env`
3. Check database connectivity
4. Review nginx routing

---

**PAW Systems - Unified Application Platform**
