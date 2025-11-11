# PAW Systems - Quick Setup Guide

## 🚀 5-Minute Setup

### Step 1: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Required Settings:**

```bash
# Generate a random secret key (use: openssl rand -hex 32)
SECRET_KEY=your-random-secret-key-here

# Set strong database password
POSTGRES_PASSWORD=your-strong-password

# Configure email for authentication codes
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
SMTP_FROM=your-email@gmail.com

# Add Anthropic API key for PDF converter
ANTHROPIC_API_KEY=sk-ant-...
```

### Step 2: Start Services

```bash
# Make startup script executable
chmod +x start.sh

# Start all services
./start.sh
```

### Step 3: Add Your First User

```bash
# Make user script executable
chmod +x add-user.sh

# Add a user
./add-user.sh your.email@paw-systems.com
```

### Step 4: Access the Platform

Open your browser and navigate to:
- **http://localhost** - Landing page
- **http://localhost/login.html** - Login

## 📧 Email Configuration (Gmail)

### Generate App Password

1. Go to Google Account settings
2. Security → 2-Step Verification
3. App passwords → Generate new
4. Copy the 16-character password
5. Add to `.env` as `SMTP_PASSWORD`

### Alternative Email Providers

**Office 365:**
```bash
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
```

**Custom SMTP:**
```bash
SMTP_HOST=mail.yourserver.com
SMTP_PORT=587
SMTP_USER=noreply@yourserver.com
SMTP_PASSWORD=your-password
```

## 🔑 Anthropic API Key

1. Sign up at https://console.anthropic.com/
2. Create an API key
3. Add to `.env`:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-api03-...
   ```

## 🗄️ Database Setup

The database is automatically initialized with required tables.

### Manual Table Creation (if needed)

```bash
docker compose exec db psql -U pawuser -d pawsystems
```

```sql
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    session_validity_minutes INTEGER,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Auth codes table
CREATE TABLE IF NOT EXISTS auth_codes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    code TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Settings table
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Jobs table (from crawler init.sql)
CREATE TABLE IF NOT EXISTS jobs (
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

CREATE INDEX IF NOT EXISTS idx_jobs_posted_date ON jobs(posted_date DESC);
```

## 🔧 Troubleshooting

### Services Won't Start

```bash
# Check Docker is running
docker info

# View service logs
docker compose logs -f

# Restart services
docker compose restart
```

### Can't Login

```bash
# Check user exists
docker compose exec db psql -U pawuser -d pawsystems -c \
  "SELECT * FROM users WHERE email='your.email@paw-systems.com';"

# Check SMTP settings in .env
# Verify email is sent (check spam folder)
```

### PDF Converter Not Working

```bash
# Check API key is set
grep ANTHROPIC_API_KEY .env

# View converter logs
docker compose logs -f converter-api

# Test health endpoint
curl http://localhost/api/converter/health
```

### Crawler Not Finding Jobs

```bash
# Enable debug mode
echo "DEBUG_MODE=true" >> .env

# Restart crawler
docker compose restart crawler

# Check debug artifacts
ls -la freelance-crawler/debug_artifacts/
```

## 📊 Useful Commands

```bash
# View all logs
docker compose logs -f

# View specific service logs
docker compose logs -f crawler-api
docker compose logs -f converter-api

# Restart a service
docker compose restart [service-name]

# Stop all services
docker compose down

# Rebuild and restart
docker compose up --build -d

# Access database
docker compose exec db psql -U pawuser -d pawsystems

# Add user
./add-user.sh user@paw-systems.com

# Backup database
docker compose exec db pg_dump -U pawuser pawsystems > backup.sql
```

## 🎯 Next Steps

1. ✅ Configure environment variables
2. ✅ Start services
3. ✅ Add users
4. ✅ Test login
5. ✅ Configure crawler keywords
6. ✅ Test PDF converter

## 📚 Additional Resources

- **Main README**: `README.md` - Complete documentation
- **Crawler README**: `freelance-crawler/README.md` - Crawler details
- **Converter README**: `pdf-converter/README.md` - Converter details

## 🆘 Support

If you encounter issues:

1. Check logs: `docker compose logs -f`
2. Verify `.env` configuration
3. Ensure all required services are running
4. Check database connectivity
5. Review nginx routing configuration

---

**Ready to go! 🎉**
