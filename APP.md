# PAW Systems - Application Documentation

## 📋 Overview

PAW Systems is a secure, multi-service web application platform consisting of:

1. **Landing Page** - Protected entry point with service selection
2. **Freelance Crawler** - Automated job scraping and management system
3. **PDF Converter** - AI-powered PDF to Excel conversion using Claude AI
4. **Team Todo List** - Shared team task management with priorities and categories
5. **User Management** - Administrative interface for managing users, roles, and permissions (Admin only)

All services require authentication and are designed for internal company use.

## 🏗️ Architecture

### Services

```
┌───────────────────────────────────────────────────────────────────┐
│                        Nginx (Reverse Proxy)                       │
│                       Ports: 8080/8443 (dev)                      │
│                            80/443 (prod)                           │
└───────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼──────────────────────┬──────────────┐
        │                       │                      │              │
┌───────▼────────┐   ┌──────────▼─────────┐   ┌───────▼────────┐   │
│   Frontend     │   │  Crawler Service   │   │Converter Service│   │
│  (Landing Page)│   │                    │   │                 │   │
└────────────────┘   └────────────────────┘   └─────────────────┘   │
                              │                       │              │
                     ┌────────┴────────┐   ┌──────────┴──────┐ ┌────▼──────┐
                     │  Crawler API    │   │ Converter API   │ │  Todo API │
                     │  (FastAPI)      │   │  (FastAPI)      │ │ (FastAPI) │
                     └────────┬────────┘   └─────────────────┘ └─────┬─────┘
                              │                                       │
                     ┌────────▼───────────────────────────────────────▼─────┐
                     │                    PostgreSQL                         │
                     │                    (Database)                         │
                     └──────────────────────────────────────────────────────┘
```

### Technology Stack

- **Frontend**: HTML/CSS/JavaScript, React (Converter & Todo List)
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
location ~ ^/api/todos(/.*)?$ { ... }

# 2. Frontend routes
location /crawler/ { ... }
location /converter { ... }  # No trailing slash for React
location /todos { ... }  # React app

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
| `/todos/` | todo-web | Team todo list UI (protected) |
| `/user-management/` | user-management-web | User management UI (admin only) |
| `/api/crawler/*` | crawler-api | Crawler API endpoints |
| `/api/converter/*` | converter-api | Converter API endpoints |
| `/api/todos/*` | todo-api | Todo list API endpoints |
| `/api/user-management/*` | user-management-api | User management API endpoints (admin only) |

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
├── todo-list/
│   ├── backend/               # Todo API (FastAPI)
│   │   ├── app.py            # CRUD operations, auth
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── frontend/             # React app
│   │   ├── src/
│   │   │   ├── App.jsx       # Main component
│   │   │   └── components/   # TodoList, TodoItem, TodoForm, TodoStats
│   │   ├── Dockerfile
│   │   └── package.json
│   └── migrations/           # Database migrations
│       └── 001_create_todos_table.sql
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

# Crawler Configuration
JOB_RETENTION_DAYS=30  # Days to keep jobs before automatic purge (default: 30)

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
User accounts for authentication, session management, and role-based access control.

```sql
CREATE TABLE users (
    id                       SERIAL PRIMARY KEY,
    email                    TEXT NOT NULL UNIQUE,
    first_name               TEXT,
    last_name                TEXT,
    session_validity_minutes INTEGER,
    is_admin                 BOOLEAN DEFAULT FALSE,
    is_super_admin           BOOLEAN DEFAULT FALSE,
    created_at               TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    last_login               TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT email_domain_check CHECK (email LIKE '%@paw-systems.com')
);

CREATE INDEX idx_users_is_admin ON users (is_admin);
CREATE INDEX idx_users_is_super_admin ON users (is_super_admin);
```

**Columns**:
- `id`: Auto-incrementing primary key
- `email`: Unique email address (must be @paw-systems.com domain)
- `first_name`: User's first name (optional)
- `last_name`: User's last name (optional)
- `session_validity_minutes`: Custom session timeout per user
- `is_admin`: Whether user has admin access to User Management app
- `is_super_admin`: Whether user can grant/revoke admin rights (only uwe.ritter@paw-systems.com)
- `created_at`: Account creation timestamp
- `last_login`: Last successful login timestamp

**Constraints**:
- Email must end with `@paw-systems.com`

**Indexes**:
- Performance indexes on `is_admin` and `is_super_admin` for access control checks

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
- `posted`: Posted date as text from source (may be date or time)
- `posted_date`: Parsed timestamp for sorting (shown as "Veröffentlicht" in UI)
- `created_at`: When job was scraped by crawler (shown as "Erfasst am" in UI)
- `processed`: Whether job has been reviewed/processed

**Date Display**:
- Frontend displays both `posted_date` and `created_at` in DD.MM.YYYY format
- "Veröffentlicht" column shows when job was originally posted on job board
- "Erfasst am" column shows when crawler captured the job

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

#### 5. todos
Team todo list items with priorities, categories, and due dates.

```sql
CREATE TABLE todos (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    completed BOOLEAN DEFAULT FALSE,
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    category TEXT,
    due_date TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    created_by TEXT,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    completed_by TEXT,
    assigned_to TEXT
);

CREATE INDEX idx_todos_completed ON todos (completed);
CREATE INDEX idx_todos_priority ON todos (priority);
CREATE INDEX idx_todos_due_date ON todos (due_date);
CREATE INDEX idx_todos_created_at ON todos (created_at DESC);
CREATE INDEX idx_todos_category ON todos (category);
CREATE INDEX idx_todos_assigned_to ON todos (assigned_to);
```

**Columns**:
- `id`: Auto-incrementing primary key
- `title`: Todo title/summary (required)
- `description`: Detailed description (optional)
- `completed`: Whether todo is completed
- `priority`: Priority level (low/medium/high)
- `category`: Custom category/tag for organization
- `due_date`: Optional deadline
- `created_at`: When todo was created
- `updated_at`: Last modification timestamp
- `created_by`: Email of user who created the todo
- `completed_at`: When todo was marked complete
- `completed_by`: Email of user who completed it
- `assigned_to`: Email of user assigned to this todo (links to users.email)

**Display Names**:
- API joins with `users` table twice to construct display names for both assigned and creator
- `assigned_to_name`: Display name for assigned user (first_name + last_name, or email as fallback)
- `created_by_name`: Display name for creator user (first_name + last_name, or email as fallback)
- Frontend displays clickable mailto links for both fields
- Applies to: todo items (with mailto links), assignment dropdown, and filter dropdown

**Categories**:
- Predefined categories: Vertrieb, Support, Meeting, Planung, Admin
- Category field uses dropdown (select) for consistency
- "Keine Kategorie" option for tasks without category

**Indexes**:
- Performance indexes on `completed`, `priority`, `due_date`, `created_at`, `category`, and `assigned_to`
- Enables fast filtering and sorting by assignee

**Triggers**:
- Automatic `updated_at` timestamp update on any modification

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
- **Multi-provider job scraping** - Automated crawling from multiple job boards
- **Selenium-based automation** - Headless browser for JavaScript-heavy sites
- **Job filtering and processing** - Mark jobs as processed, filter by source
- **Date-based filtering** - Filter jobs by scrape date (last 7/14/30 days)
- **Dual date tracking** - "Veröffentlicht" (posted date) and "Erfasst am" (scraped date) columns
- **Consistent date formatting** - All dates displayed in DD.MM.YYYY format
- **Admin job deletion** - Administrators can delete individual jobs with trash icon (non-admins cannot)
- **CSV Export** - Download entire jobs database as CSV file
- **Configuration management** - JSON-based crawler configuration with Simple Mode and Expert Mode
  - **Simple Mode Wizard** - User-friendly interface with:
    - Unified picklist for adding queries/categories (Categories: create new query, Existing Queries: copy from other providers)
    - Visual grouping with icons (📁 Categories, 📋 Existing Queries)
    - Easy query management with delete buttons
    - Keyword category management
  - **Expert Mode** - Direct JSON editing for advanced users
- **Document upload/management** - Store and manage application documents
- **Scheduled crawling** - Automatic crawling every 3 hours (00:07, 03:07, etc.)
- **Automatic purge** - Old jobs deleted nightly (configurable retention period)
- **Database backup** - Daily automated backups at 2:00 AM

### PDF Converter
- **AI-powered PDF analysis** - Uses Claude Sonnet 4.5 for intelligent extraction
- **Automatic table detection** - Recognizes complex table structures
- **German DATEV support** - Specialized for German payroll documents
- **Euro/Cent column merging** - Intelligently merges split monetary columns
- **Excel/CSV export** - Download extracted data in spreadsheet format
- **German formatting** - Comma decimal separators, proper number formatting
- **Drag-and-drop upload** - Easy file upload interface
- **Concurrent processing** - 4 workers for simultaneous conversions
- **Authentication required** - Secure access control

### Team Todo List
- **Shared team todolist** - All authenticated users see and manage the same todos
- **Task assignment** - Assign todos to team members from user database dropdown
- **User-friendly display** - Shows user names (first + last name) instead of email addresses, with email as fallback
- **Mailto links** - Click on assigned or created-by names to open email client
- **Priority levels** - Low, medium, and high priorities with color coding
- **Predefined categories** - Choose from Vertrieb, Support, Meeting, Planung, or Admin
- **Due dates** - Set deadlines with visual indicators for overdue items
- **Rich descriptions** - Add detailed notes and context to each todo
- **User tracking** - Track who created, assigned, and completed each todo (displayed by name with mailto links)
- **Real-time statistics** - Dashboard showing completion rate and priority breakdown
- **Advanced filtering** - Filter by completion status, priority, category, assigned user (by name), or search by title
- **Sort options** - Sort by created date, due date, or priority
- **Responsive design** - Mobile-friendly interface with purple gradient theme
- **Authentication required** - Secure access control with JWT tokens

### User Management (Admin Only)
- **Role-based access control** - Admin and super admin roles with different permissions
- **User CRUD operations** - Create, read, update, and delete users (admins)
- **Admin rights management** - Grant/revoke admin access (super admin only)
- **Super admin protection** - Only uwe.ritter@paw-systems.com can manage admin rights
- **Safety checks** - Prevents deleting or demoting the last administrator
- **User profiles** - First name, last name, email, session validity configuration
- **Activity tracking** - View last login times and user statistics
- **Search and filter** - Find users by email, name, or admin status
- **Visual role indicators** - Color-coded badges for super admin, admin, and regular users
- **Real-time statistics** - Dashboard showing total users, admins, and recent activity
- **Conditional visibility** - User Management card only visible to admin users on landing page
- **Session management** - Configure custom session validity per user
- **German UI** - Full German language interface matching other apps
- **Responsive design** - Mobile-friendly with purple gradient theme

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
9. **Crawler has automated tasks** - Scheduled crawling, backup, and purge
10. **Job retention is configurable** - Set `JOB_RETENTION_DAYS` in `.env`
11. **CSV export downloads all jobs** - No pagination limit on export
12. **Date filter uses created_at** - Not posted date, filters by scrape date
13. **PDF converter uses 4 workers** - Can handle concurrent conversions
14. **Container names matter** - Crawler API calls `paw_selenium_crawler` not `selenium_crawler`
15. **Todo list is shared** - All users see and manage the same todos (not per-user)
16. **Todo API uses regex location** - Nginx location is `~ ^/api/todos(/.*)?$` to preserve full path
17. **Todo route order critical** - `/api/todos/users` endpoint must be defined BEFORE `/api/todos/{todo_id}` in FastAPI
18. **Todo assignees from users table** - Assignment dropdown populated from `users` table, not a separate list
19. **Todo displays user names** - API joins with users table twice to show names for both assigned and creator (email as fallback)
20. **Todo name fields have mailto links** - Both `assigned_to_name` and `created_by_name` are clickable mailto links
21. **Todo categories are predefined** - Uses select dropdown with: Vertrieb, Support, Meeting, Planung, Admin
22. **Todo API returns display names** - All endpoints join users table twice to provide both `assigned_to_name` and `created_by_name` fields
23. **User Management is admin-only** - Card hidden on landing page for non-admin users
24. **Super admin is unique** - Only uwe.ritter@paw-systems.com can grant/revoke admin rights
25. **Admin safety checks** - System prevents deleting or demoting the last administrator
26. **User Management API uses path stripping** - Nginx strips `/api/user-management/` prefix
27. **Auth endpoint includes admin status** - `/api/crawler/auth/check` returns `is_admin` flag
28. **Admin check uses database** - Auth endpoint queries users table for `is_admin` on every check
29. **Crawler delete is admin-only** - DELETE `/api/crawler/jobs/{job_id}` endpoint requires admin status (403 for non-admins)
30. **Delete button visibility** - Trash icon only rendered in frontend when `isAdmin` flag is true
31. **Delete icon matches todo list** - Uses same SVG trash icon styling (transparent background, red on hover)
32. **Crawler config uses unified picklist** - Simple Mode has single dropdown with optgroups: Categories (create new) and Existing Queries (copy)
33. **Config onclick uses data-attributes** - All event handlers use `data-provider` attributes instead of inline strings to prevent escaping issues

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

### Automated Tasks

The crawler API includes a scheduler that runs automated maintenance tasks:

| Time | Task | Description |
|------|------|-------------|
| **00:07, 03:07, 06:07, 09:07, 12:07, 15:07, 18:07, 21:07** | Crawler Job | Scrapes job boards every 3 hours |
| **02:00 AM** | Database Backup | Daily automated backup to `/app/backups` |
| **02:05 AM** | Job Purge | Deletes jobs older than `JOB_RETENTION_DAYS` (default: 30 days) |

**Configuration:**
- Set `JOB_RETENTION_DAYS` in `.env` to change retention period
- Backups are stored in the mounted `/app/backups` volume
- Purge runs 5 minutes after backup to ensure old data is backed up first

**Logs:**
```bash
# View scheduler logs
docker compose logs crawler-api | grep "Scheduler"

# Check purge results
docker compose logs crawler-api | grep "purge"
```

### Manual Tasks

- Monitor SSL certificate expiry (auto-renewed)
- Check application logs for errors
- Update Docker images periodically
- Review and rotate API keys
- Monitor disk space (backups and database)

### Manual Database Backup

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

**Last Updated**: January 2026
**Version**: 1.1
**Maintained by**: PAW Systems Team
