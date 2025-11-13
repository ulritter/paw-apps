# PAW Systems - Application Documentation

## 📋 Overview

PAW Systems is a secure, multi-service web application platform consisting of:

1. **Landing Page** - Protected entry point with service selection
2. **Freelance Crawler** - Automated job scraping and management system
3. **PDF Converter** - AI-powered PDF to Excel conversion using Claude AI

All services require authentication and are designed for internal company use.

## 🏗️ Architecture

### Services

```
┌─────────────────────────────────────────────────────────────┐
│                         Nginx (Reverse Proxy)                │
│                    Ports: 8080/8443 (dev)                   │
│                         80/443 (prod)                        │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼────────┐   ┌────────▼────────┐   ┌───────▼────────┐
│   Frontend     │   │ Crawler Service │   │Converter Service│
│  (Landing Page)│   │                 │   │                 │
└────────────────┘   └─────────────────┘   └────────────────┘
                              │                     │
                     ┌────────┴────────┐   ┌────────┴────────┐
                     │  Crawler API    │   │ Converter API   │
                     │  (FastAPI)      │   │  (FastAPI)      │
                     └────────┬────────┘   └─────────────────┘
                              │
                     ┌────────▼────────┐
                     │   PostgreSQL    │
                     │   (Database)    │
                     └─────────────────┘
```

### Technology Stack

- **Frontend**: HTML/CSS/JavaScript, React (Converter)
- **Backend**: Python FastAPI
- **Database**: PostgreSQL
- **Reverse Proxy**: Nginx
- **Containerization**: Docker & Docker Compose
- **SSL**: Let's Encrypt (production)
- **AI**: Anthropic Claude API (PDF conversion)

## 🔐 Authentication & Security

### Authentication Flow

1. User attempts to access any protected page (/, /crawler/, /converter/)
2. Frontend checks `/api/crawler/auth/check` endpoint
3. If not authenticated → redirect to `/login.html`
4. User enters email → receives authentication code via email
5. User enters code → JWT token set as httpOnly cookie
6. Cookie valid across all services (path="/")

### Security Features

- **All pages require authentication** (except login page)
- **JWT tokens** stored in httpOnly cookies
- **Session management** with configurable expiry
- **Secure cookies** in production (HTTPS)
- **Rate limiting** on API endpoints
- **CORS protection**
- **Security headers** (X-Frame-Options, CSP, etc.)

### Cookie Configuration

```python
# Development: secure=False (HTTP allowed)
# Production: secure=True (HTTPS only)
response.set_cookie(
    key="auth_token",
    value=access_token,
    httponly=True,
    samesite="lax",
    secure=is_production,  # Environment-aware
    path="/"  # Available across all routes
)
```

## 🛣️ Routing Configuration

### Nginx Route Order (CRITICAL)

Routes must be defined in this order for correct matching:

```nginx
# 1. API routes FIRST (most specific)
location /api/crawler/ { ... }
location /api/converter/ { ... }

# 2. Frontend routes
location /crawler/ { ... }
location /converter { ... }  # No trailing slash for React

# 3. Health check
location /health { ... }

# 4. Catch-all LAST
location / { ... }
```

### URL Mapping

| URL | Service | Description |
|-----|---------|-------------|
| `/` | frontend | Landing page (protected) |
| `/login.html` | frontend | Login page (public) |
| `/crawler/` | crawler-web | Job crawler UI (protected) |
| `/converter/` | converter-web | PDF converter UI (protected) |
| `/api/crawler/*` | crawler-api | Crawler API endpoints |
| `/api/converter/*` | converter-api | Converter API endpoints |

## 📁 Project Structure

```
paw-apps/
├── frontend/                    # Landing page
│   └── public/
│       ├── index.html          # Protected landing page
│       └── login.html          # Login page
├── freelance-crawler/
│   ├── api/                    # Crawler backend (FastAPI)
│   │   └── main.py            # Auth, jobs, config endpoints
│   └── web/                    # Crawler frontend
│       ├── index.html         # Main UI
│       ├── app.js             # Frontend logic
│       └── styles.css         # Styling
├── pdf-converter/
│   ├── backend/               # Converter API (FastAPI)
│   │   └── app.py            # PDF conversion logic
│   └── frontend/             # React app
│       └── src/
│           └── App.jsx       # Main component
├── nginx/
│   ├── nginx.conf            # Production config (SSL)
│   └── nginx-dev.conf        # Development config (HTTP)
├── docker-compose.yml        # Production compose
├── docker-compose-dev.yml    # Development compose
├── start.sh                  # Startup script
└── .env                      # Environment variables
```

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Database
POSTGRES_USER=freelance
POSTGRES_PASSWORD=your-password
POSTGRES_DB=pawsystems
DATABASE_URL=postgresql://freelance:password@db:5432/pawsystems

# Security
SECRET_KEY=your-secret-key-here
API_KEY=your-api-key

# Email (for auth codes)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com

# AI Service
ANTHROPIC_API_KEY=sk-ant-...

# Production
DOMAIN_NAME=your-domain.com
CERTBOT_EMAIL=admin@your-domain.com

# Environment
ENV=production  # or development
```

### Docker Compose Services

**Development** (`docker-compose-dev.yml`):
- Ports: 8080 (HTTP), 8443 (HTTPS)
- Uses `nginx-dev.conf` (no SSL)
- Hot reload enabled

**Production** (`docker-compose.yml`):
- Ports: 80 (HTTP), 443 (HTTPS)
- Uses `nginx.conf` (with SSL)
- Let's Encrypt certificates
- `ENV=production` set for all services

## 🚀 Deployment

### Development

```bash
# Start services
./start.sh dev

# Access at:
# http://localhost:8080
```

### Production

```bash
# First time setup (generates SSL certificates)
./start.sh prod

# Subsequent starts
docker compose up -d

# Access at:
# https://your-domain.com
```

### SSL Certificate Setup

Production uses Let's Encrypt for SSL:

```bash
# Initial certificate generation
./init-letsencrypt.sh

# Auto-renewal (runs via cron)
./renew-certificates.sh
```

## 🗄️ Database

### Database Name

**Important**: The actual database name is `freelance`, not `pawsystems` as mentioned in some configuration examples.

### Schema

#### 1. users
User accounts for authentication and session management.

```sql
CREATE TABLE users (
    id                       SERIAL PRIMARY KEY,
    email                    TEXT NOT NULL UNIQUE,
    session_validity_minutes INTEGER,
    created_at               TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    last_login               TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT email_domain_check CHECK (email LIKE '%@paw-systems.com')
);
```

**Columns**:
- `id`: Auto-incrementing primary key
- `email`: Unique email address (must be @paw-systems.com domain)
- `session_validity_minutes`: Custom session timeout per user
- `created_at`: Account creation timestamp
- `last_login`: Last successful login timestamp

**Constraints**:
- Email must end with `@paw-systems.com`

#### 2. jobs
Job listings scraped from various sources.

```sql
CREATE TABLE jobs (
    id          SERIAL PRIMARY KEY,
    source      TEXT,
    title       TEXT,
    link        TEXT UNIQUE,
    company     TEXT,
    location    TEXT,
    posted      TEXT,
    posted_date TIMESTAMP WITHOUT TIME ZONE,
    created_at  TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    processed   BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_jobs_posted_date ON jobs (posted_date DESC);
CREATE UNIQUE INDEX idx_jobs_unique_title_company_source
    ON jobs (LOWER(title), LOWER(COALESCE(company, '')), source)
    WHERE title IS NOT NULL;
```

**Columns**:
- `id`: Auto-incrementing primary key
- `source`: Job board source (e.g., "Indeed", "LinkedIn")
- `title`: Job title
- `link`: Unique URL to the job posting
- `company`: Company name
- `location`: Job location
- `posted`: Posted date as text (from source)
- `posted_date`: Parsed timestamp for sorting
- `created_at`: When job was scraped
- `processed`: Whether job has been reviewed/processed

**Indexes**:
- Unique constraint on `link` to prevent duplicates
- Unique constraint on `(title, company, source)` combination (case-insensitive)
- Performance index on `posted_date` for chronological queries

#### 3. settings
Application configuration key-value store.

```sql
CREATE TABLE settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    description TEXT,
    updated_at  TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
```

**Columns**:
- `key`: Setting identifier (primary key)
- `value`: Setting value (stored as text)
- `description`: Human-readable description of the setting
- `updated_at`: Last modification timestamp

#### 4. auth_codes
Temporary authentication codes for email-based login.

```sql
CREATE TABLE auth_codes (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code       TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    used       BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_auth_codes_user_id ON auth_codes (user_id);
CREATE INDEX idx_auth_codes_code ON auth_codes (code);
```

**Columns**:
- `id`: Auto-incrementing primary key
- `user_id`: Foreign key to users table
- `code`: 6-digit authentication code
- `created_at`: When code was generated
- `expires_at`: When code expires (typically 10 minutes)
- `used`: Whether code has been used

**Relationships**:
- Foreign key to `users(id)` with CASCADE delete
- When a user is deleted, all their auth codes are removed

**Indexes**:
- Index on `user_id` for fast user lookup
- Index on `code` for fast code validation

### User Management

Users must be manually added to the database:

```sql
INSERT INTO users (email, session_validity_minutes)
VALUES ('user@company.com', 60);
```

## 🎨 UI/UX Design

### Design System

**Colors**:
- Primary: Purple gradient (#667eea → #764ba2)
- Accent: Indigo (#8b5cf6)
- Background: White with gradient overlays

**Components**:
- Rounded pill buttons (border-radius: 50px)
- Glassmorphism effects (backdrop-filter: blur)
- Smooth transitions (0.3s)
- Hover effects (translateY, opacity)

### Navigation

All protected pages include:
- **← Home button** (top left) - Returns to landing page
- **User info pill** (top right) - Shows email + logout button
- Consistent styling across all pages

## 🔍 Key Features

### Freelance Crawler
- Multi-provider job scraping
- Selenium-based automation
- Job filtering and processing
- Configuration management
- Document upload/management
- Export to CSV

### PDF Converter
- AI-powered PDF analysis (Claude Sonnet)
- Automatic table detection
- Excel/CSV export
- German formatting support
- Drag-and-drop upload

## 🐛 Troubleshooting

### Common Issues

**1. Redirect Loop**
- **Cause**: Nginx route order incorrect
- **Fix**: Ensure API routes are before catch-all `/`

**2. 404 on Static Files**
- **Cause**: React app routing misconfigured
- **Fix**: Remove trailing slash in nginx `proxy_pass` for `/converter`

**3. Authentication Not Working**
- **Cause**: Cookie not being sent
- **Fix**: Add `credentials: 'include'` to all fetch calls

**4. Browser Cache Issues**
- **Cause**: Old responses cached
- **Fix**: Hard refresh (Cmd+Shift+R) or clear cache

**5. Cookie Not Set**
- **Cause**: Secure flag mismatch
- **Fix**: Ensure `ENV` variable is set correctly

### Debug Commands

```bash
# Check service logs
docker compose -f docker-compose-dev.yml logs -f [service-name]

# Check nginx config
docker compose -f docker-compose-dev.yml exec nginx cat /etc/nginx/conf.d/default.conf

# Test API endpoint
curl -v http://localhost:8080/api/crawler/auth/check

# Check database
docker compose -f docker-compose-dev.yml exec db psql -U freelance -d pawsystems
```

## 📝 Important Notes

### For Claude AI Context

When working with this application:

1. **Always check nginx route order** - API routes must come before `/`
2. **Cookie configuration is environment-aware** - Uses `ENV` variable
3. **All pages require authentication** - Except `/login.html`
4. **React app needs special routing** - No trailing slash in nginx
5. **Browser cache can cause issues** - Always test with hard refresh
6. **Database schema is simple** - Users must be manually added
7. **Authentication uses email codes** - No passwords
8. **JWT tokens in httpOnly cookies** - Path must be "/"

### Production Checklist

- [ ] Set strong `SECRET_KEY` and `POSTGRES_PASSWORD`
- [ ] Configure SMTP settings for email
- [ ] Add Anthropic API key for PDF converter
- [ ] Set correct `DOMAIN_NAME` and `CERTBOT_EMAIL`
- [ ] Run `init-letsencrypt.sh` for SSL certificates
- [ ] Add users to database
- [ ] Test all authentication flows
- [ ] Verify all pages require login
- [ ] Check SSL certificate auto-renewal

## 🔄 Maintenance

### Regular Tasks

- Monitor SSL certificate expiry (auto-renewed)
- Check application logs for errors
- Update Docker images periodically
- Backup PostgreSQL database
- Review and rotate API keys

### Backup Database

```bash
docker compose exec db pg_dump -U freelance pawsystems > backup.sql
```

### Restore Database

```bash
docker compose exec -T db psql -U freelance pawsystems < backup.sql
```

## 📞 Support

For issues or questions, refer to:
- Application logs: `docker compose logs`
- Nginx logs: `docker compose exec nginx cat /var/log/nginx/error.log`
- Database logs: `docker compose logs db`

---

**Last Updated**: November 2025  
**Version**: 1.0  
**Maintained by**: PAW Systems Team
