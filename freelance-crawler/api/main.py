from fastapi import FastAPI, Query, BackgroundTasks, HTTPException, Cookie, Response, Depends, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr, validator
import psycopg2
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta
from jose import JWTError, jwt
import secrets
import string
import aiosmtplib
from email.message import EmailMessage
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import threading
from typing import Optional

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crawler lock to prevent concurrent runs
crawler_lock = threading.Lock()
crawler_status = {
    "is_running": False,
    "started_at": None,
    "started_by": None,  # 'user' or 'scheduler'
    "progress": 0
}

app = FastAPI(title="Freelance Job API")

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize scheduler
scheduler = BackgroundScheduler()

# Scheduled crawler function
def scheduled_crawler_job():
    """Run the crawler automatically on schedule"""
    # Try to acquire lock (non-blocking)
    if not crawler_lock.acquire(blocking=False):
        logger.warning("Scheduled crawler job skipped - crawler is already running")
        return

    try:
        crawler_status["is_running"] = True
        crawler_status["started_at"] = datetime.utcnow().isoformat()
        crawler_status["started_by"] = "scheduler"
        crawler_status["progress"] = 0

        logger.info("Starting scheduled crawler job...")
        # Run crawler using docker exec (use existing container)
        result = subprocess.run(
            ['docker', 'exec', 'selenium_crawler', 'python', '/app/run_crawlers.py'],
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        if result.returncode == 0:
            logger.info("Scheduled crawler job completed successfully")
        else:
            logger.error(f"Scheduled crawler job failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        logger.error("Scheduled crawler job timed out after 1 hour")
    except Exception as e:
        logger.error(f"Scheduled crawler job error: {str(e)}")
    finally:
        crawler_status["is_running"] = False
        crawler_status["started_at"] = None
        crawler_status["started_by"] = None
        crawler_status["progress"] = 0
        crawler_lock.release()
        logger.info("Crawler lock released")

def scheduled_backup_job():
    """Run database backup automatically on schedule"""
    try:
        logger.info("Starting scheduled database backup...")

        # Run backup script
        result = subprocess.run(
            ['/app/backup_database.sh'],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
            cwd='/app'
        )

        if result.returncode == 0:
            logger.info("Scheduled database backup completed successfully")
            # Log the backup file name from output
            for line in result.stdout.split('\n'):
                if 'Backup file:' in line:
                    logger.info(line.strip())
        else:
            logger.error(f"Scheduled database backup failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        logger.error("Scheduled database backup timed out after 10 minutes")
    except Exception as e:
        logger.error(f"Scheduled database backup error: {str(e)}")

@app.on_event("startup")
def start_scheduler():
    """Start the background scheduler on application startup"""
    # Schedule crawler to run every 3 hours starting at midnight (00:00, 03:00, 06:00, etc.)
    scheduler.add_job(
        scheduled_crawler_job,
        CronTrigger(hour='0,3,6,9,12,15,18,21', minute=7),
        id='crawler_job',
        name='Run crawler every 3 hours',
        replace_existing=True
    )

    # Schedule database backup to run daily at 2:00 AM
    scheduler.add_job(
        scheduled_backup_job,
        CronTrigger(hour=2, minute=0),
        id='backup_job',
        name='Daily database backup at 2:00 AM',
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler started - Crawler will run every 3 hours")
    logger.info("Scheduler started - Database backup will run daily at 2:00 AM")

@app.on_event("shutdown")
def shutdown_scheduler():
    """Shutdown the scheduler on application shutdown"""
    scheduler.shutdown()
    logger.info("Scheduler shutdown")

# Authentication Configuration
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
AUTH_CODE_EXPIRY_MINUTES = 10

# API Key Configuration (optional additional security layer)
API_KEY = os.getenv("API_KEY", None)
if API_KEY:
    logger.info("✅ API Key authentication enabled")
else:
    logger.warning("⚠️  API Key authentication disabled - set API_KEY in .env for additional security")

# Email Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

# Pydantic Models
class EmailRequest(BaseModel):
    email: EmailStr
    
    @validator('email')
    def email_must_be_paw_systems(cls, v):
        if not v.endswith('@paw-systems.com'):
            raise ValueError('Email must be from paw-systems.com domain')
        return v

class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str

class AuthResponse(BaseModel):
    authenticated: bool
    email: str | None = None
    expires_at: str | None = None

def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def generate_auth_code() -> str:
    """Generate an 8-character alphanumeric auth code"""
    chars = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(8))

def create_access_token(data: dict, expires_delta: timedelta) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def send_auth_email(email: str, code: str):
    """Send authentication code via email"""
    if not SMTP_USER or not SMTP_PASSWORD:
        print("⚠️  Email not configured. Auth code:", code)
        return
    
    message = EmailMessage()
    message["From"] = SMTP_FROM
    message["To"] = email
    message["Subject"] = "Your Freelance Crawler Login Code"
    message.set_content(f"""
Hello,

Your authentication code is: {code}

This code will expire in {AUTH_CODE_EXPIRY_MINUTES} minutes.

If you didn't request this code, please ignore this email.

Best regards,
Freelance Crawler System
    """)
    
    try:
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=True,
        )
        print(f"✅ Auth email sent to {email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send authentication email")

def get_session_validity_minutes() -> int:
    """Get global session validity setting"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = 'session_validity_minutes'")
        result = cur.fetchone()
        cur.close()
        conn.close()
        return int(result[0]) if result else 60
    except:
        return 60

async def verify_auth_token(auth_token: str | None = Cookie(None)):
    """Dependency to verify authentication token"""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication")

async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Dependency to verify API key for programmatic access"""
    if not API_KEY:
        # API key authentication is disabled
        return None
    
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide X-API-Key header."
        )
    
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    return x_api_key

async def verify_auth_or_api_key(
    auth_token: str | None = Cookie(None),
    x_api_key: Optional[str] = Header(None)
):
    """Dependency to verify either JWT token OR API key"""
    # Try JWT authentication first
    if auth_token:
        try:
            payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            if email:
                return {"type": "jwt", "identity": email}
        except JWTError:
            pass
    
    # Try API key authentication
    if API_KEY and x_api_key:
        if x_api_key == API_KEY:
            return {"type": "api_key", "identity": "api_client"}
        else:
            raise HTTPException(status_code=403, detail="Invalid API key")
    
    # If API key is required but not provided
    if API_KEY and not x_api_key and not auth_token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide auth_token cookie or X-API-Key header."
        )
    
    # No authentication method succeeded
    raise HTTPException(status_code=401, detail="Not authenticated")

# Authentication Endpoints

@app.post("/auth/send-code")
async def send_code(request: EmailRequest):
    """Send authentication code to user's email"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT id FROM users WHERE email = %s", (request.email,))
        user = cur.fetchone()
        
        if not user:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="User not found. Please contact administrator.")
        
        user_id = user[0]
        
        # Generate auth code
        code = generate_auth_code()
        expires_at = datetime.utcnow() + timedelta(minutes=AUTH_CODE_EXPIRY_MINUTES)
        
        # Store auth code
        cur.execute(
            "INSERT INTO auth_codes (user_id, code, expires_at) VALUES (%s, %s, %s)",
            (user_id, code, expires_at)
        )
        conn.commit()
        cur.close()
        conn.close()
        
        # Send email
        await send_auth_email(request.email, code)
        
        return {"message": "Authentication code sent to your email", "expires_in_minutes": AUTH_CODE_EXPIRY_MINUTES}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error sending auth code: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/verify-code")
async def verify_code(request: VerifyCodeRequest, response: Response):
    """Verify authentication code and create session"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get user
        cur.execute("SELECT id, session_validity_minutes FROM users WHERE email = %s", (request.email,))
        user = cur.fetchone()
        
        if not user:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id, user_validity_minutes = user
        
        # Verify auth code
        cur.execute(
            """
            SELECT id, expires_at FROM auth_codes 
            WHERE user_id = %s AND code = %s AND used = FALSE 
            ORDER BY created_at DESC LIMIT 1
            """,
            (user_id, request.code)
        )
        auth_code = cur.fetchone()
        
        if not auth_code:
            cur.close()
            conn.close()
            raise HTTPException(status_code=401, detail="Invalid or expired authentication code")
        
        code_id, expires_at = auth_code
        
        # Check if code is expired
        if datetime.utcnow() > expires_at:
            cur.close()
            conn.close()
            raise HTTPException(status_code=401, detail="Authentication code has expired")
        
        # Mark code as used
        cur.execute("UPDATE auth_codes SET used = TRUE WHERE id = %s", (code_id,))
        
        # Update last login
        cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        # Get session validity (user-specific or global)
        validity_minutes = user_validity_minutes if user_validity_minutes else get_session_validity_minutes()
        
        # Create JWT token
        access_token_expires = timedelta(minutes=validity_minutes)
        access_token = create_access_token(
            data={"sub": request.email},
            expires_delta=access_token_expires
        )
        
        # Set cookie
        expires_at = datetime.utcnow() + access_token_expires
        # Use secure cookies in production (HTTPS), allow HTTP in development
        is_production = os.getenv("ENV", "development") == "production"
        response.set_cookie(
            key="auth_token",
            value=access_token,
            httponly=True,
            max_age=validity_minutes * 60,
            samesite="lax",
            secure=is_production,  # True for HTTPS in production, False for HTTP in dev
            path="/"  # Make cookie available across all paths
        )
        
        return {
            "message": "Authentication successful",
            "email": request.email,
            "expires_at": expires_at.isoformat(),
            "validity_minutes": validity_minutes
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error verifying code: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/check")
async def check_auth(response: Response, auth_token: str | None = Cookie(None)):
    """Check if user is authenticated"""
    # Prevent caching of auth check
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    if not auth_token:
        return {"authenticated": False}
    
    try:
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        exp = payload.get("exp")
        
        if email and exp:
            expires_at = datetime.utcfromtimestamp(exp)
            return {
                "authenticated": True,
                "email": email,
                "expires_at": expires_at.isoformat()
            }
    except JWTError:
        pass
    
    return {"authenticated": False}

@app.post("/auth/logout")
async def logout(response: Response):
    """Logout user by clearing auth cookie"""
    response.delete_cookie(key="auth_token")
    return {"message": "Logged out successfully"}

@app.get("/jobs")
def get_jobs(source: str | None = None, limit: int = Query(50, ge=1, le=500)):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if source:
            cur.execute("""
                SELECT id, source, title, link, company, location, posted, posted_date, created_at, processed
                FROM jobs
                WHERE source = %s
                ORDER BY posted_date DESC NULLS LAST, created_at DESC
                LIMIT %s;
            """, (source, limit))
        else:
            cur.execute("""
                SELECT id, source, title, link, company, location, posted, posted_date, created_at, processed
                FROM jobs
                ORDER BY posted_date DESC NULLS LAST, created_at DESC
                LIMIT %s;
            """, (limit,))

        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [
            {
                "id": r[0],
                "source": r[1],
                "title": r[2],
                "link": r[3],
                "company": r[4],
                "location": r[5],
                "posted": r[6],
                "posted_date": r[7].isoformat() if r[7] else None,
                "created_at": r[8].isoformat() if r[8] else None,
                "processed": r[9] if len(r) > 9 else False
            }
            for r in rows
        ]
    except Exception as e:
        # If table doesn't exist yet, return empty list instead of error
        print(f"Warning: Could not fetch jobs: {e}")
        return []

@app.get("/jobs/stats")
def get_job_stats():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT source, COUNT(*) as count
        FROM jobs
        GROUP BY source
        ORDER BY source;
    """)
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    return [
        {"source": r[0], "count": r[1]}
        for r in rows
    ]

@app.patch("/jobs/{job_id}/processed")
def update_job_processed(job_id: int, processed: bool):
    """Update the processed status of a job"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE jobs 
            SET processed = %s 
            WHERE id = %s
            RETURNING id;
        """, (processed, job_id))
        
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        if result:
            return {"status": "success", "id": result[0], "processed": processed}
        else:
            return {"status": "error", "error": "Job not found"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

import json
import re

# Global progress state
crawler_progress = {
    "total": 0,
    "completed": 0,
    "current": "",
    "running": False,
    "logs": []
}

def run_crawler():
    """Run crawler in the crawler container via docker exec"""
    import time
    global crawler_progress
    
    # Try to acquire lock (non-blocking)
    if not crawler_lock.acquire(blocking=False):
        logger.warning("Manual crawler trigger skipped - crawler is already running")
        crawler_progress["logs"].append("⚠️ Crawler läuft bereits")
        return
    
    try:
        # Update global status
        crawler_status["is_running"] = True
        crawler_status["started_at"] = datetime.utcnow().isoformat()
        crawler_status["started_by"] = "user"
        
        start_time = time.time()
        print(f"🚀 Starting crawler execution at {time.strftime('%H:%M:%S')}")
        
        # Reset progress
        crawler_progress = {
            "total": 3,  # freelancermap, solcom, hays
            "completed": 0,
            "current": "Starting...",
            "running": True,
            "logs": []
        }
        # Execute crawler in the crawler container
        print("📡 Executing: docker exec selenium_crawler python /app/run_crawlers.py")
        
        # Run with real-time output streaming
        process = subprocess.Popen(
            ["docker", "exec", "selenium_crawler", "python", "/app/run_crawlers.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        output_lines = []
        
        # Stream output and track progress
        for line in process.stdout:
            output_lines.append(line)
            print(line, end='')  # Print to API logs
            
            # Parse log line to update progress
            if "Starting freelancermap crawler" in line:
                crawler_progress["current"] = "FreelancerMap"
                # Don't add log here - wait for query-specific message
            elif "freelancermap crawler finished successfully" in line:
                crawler_progress["completed"] = 1
                crawler_progress["logs"].append("FreelancerMap abgeschlossen")
            elif "Starting solcom crawler" in line:
                crawler_progress["current"] = "Solcom"
                # Don't add log here - wait for query-specific message
            elif "solcom crawler finished successfully" in line:
                crawler_progress["completed"] = 2
                crawler_progress["logs"].append("Solcom abgeschlossen")
            elif "Starting hays crawler" in line:
                crawler_progress["current"] = "Hays"
                # Don't add log here - wait for query-specific message
            elif "hays crawler finished successfully" in line:
                crawler_progress["completed"] = 3
                crawler_progress["logs"].append("Hays abgeschlossen")
            
            # Capture query information
            elif "Searching for:" in line:
                # Extract query from log line like: "🔍 Searching for: salesforce"
                import re
                match = re.search(r'Searching for: (.+)$', line)
                if match:
                    query = match.group(1).strip()
                    current_crawler = crawler_progress.get("current", "Crawler")
                    crawler_progress["logs"].append(f'{current_crawler} Crawler mit Abfrage nach "{query}"')
            
            # Keep only last 5 log messages
            if len(crawler_progress["logs"]) > 5:
                crawler_progress["logs"] = crawler_progress["logs"][-5:]
        
        process.wait(timeout=600)
        
        duration = time.time() - start_time
        print(f"✅ Crawler finished in {duration:.1f}s with return code: {process.returncode}")
        
        # Mark as complete
        crawler_progress["running"] = False
        crawler_progress["completed"] = crawler_progress["total"]
        crawler_progress["current"] = "Abgeschlossen"
        crawler_progress["logs"].append("Alle Crawler abgeschlossen!")
            
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"⏱️  Crawler execution timed out after {duration:.1f}s (10 minute limit)")
        crawler_progress["running"] = False
        crawler_progress["logs"].append("Timeout nach 10 Minuten")
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ Error running crawler after {duration:.1f}s: {e}")
        import traceback
        traceback.print_exc()
        crawler_progress["running"] = False
        crawler_progress["logs"].append(f"Fehler: {str(e)}")
    finally:
        crawler_status["is_running"] = False
        crawler_status["started_at"] = None
        crawler_status["started_by"] = None
        crawler_status["progress"] = 0
        crawler_lock.release()
        logger.info("Crawler lock released")

@app.get("/crawler/status")
def get_crawler_status():
    """Get current crawler status (for lock checking)"""
    return crawler_status

@app.get("/crawler/progress")
def get_crawler_progress():
    """Get current crawler progress"""
    return crawler_progress

@app.post("/crawler/run")
def trigger_crawler(background_tasks: BackgroundTasks):
    """Trigger crawler manually - will fail if already running"""
    if crawler_status["is_running"]:
        return {
            "status": "error",
            "message": f"Crawler is already running (started by {crawler_status['started_by']} at {crawler_status['started_at']})"
        }
    
    background_tasks.add_task(run_crawler)
    return {"status": "started", "message": "Crawler run started in background"}

# Configuration Management Endpoints

@app.get("/config")
def get_config():
    """Get current active configuration"""
    try:
        config_path = "/app/config/search_config.json"
        with open(config_path, 'r') as f:
            config = json.load(f)
        return {"config": config, "active_version": "current"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/config/versions")
def list_config_versions():
    """List all configuration versions"""
    try:
        versions_dir = "/app/config/versions"
        os.makedirs(versions_dir, exist_ok=True)
        
        versions = []
        for filename in sorted(os.listdir(versions_dir), reverse=True):
            if filename.endswith('.json'):
                filepath = os.path.join(versions_dir, filename)
                stat = os.stat(filepath)
                
                # Extract timestamp from filename (format: search_config_YYYYMMDD_HHMMSS.json)
                timestamp_str = filename.replace('search_config_', '').replace('.json', '')
                
                # Check if this version is active
                active_link = "/app/config/search_config.json"
                is_active = False
                try:
                    if os.path.islink(active_link):
                        is_active = os.readlink(active_link) == filepath
                    else:
                        # If not a symlink, check if content matches
                        with open(active_link, 'r') as f1, open(filepath, 'r') as f2:
                            is_active = f1.read() == f2.read()
                except:
                    pass
                
                versions.append({
                    "filename": filename,
                    "timestamp": timestamp_str,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "is_active": is_active
                })
        
        return {"versions": versions}
    except Exception as e:
        return {"error": str(e), "versions": []}

@app.post("/config/save")
def save_config_version(config: dict):
    """Save a new configuration version"""
    try:
        import datetime
        
        # Create versions directory
        versions_dir = "/app/config/versions"
        os.makedirs(versions_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"search_config_{timestamp}.json"
        filepath = os.path.join(versions_dir, filename)
        
        # Save the new version
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)
        
        return {
            "status": "success",
            "message": f"Configuration saved as version {timestamp}",
            "filename": filename,
            "timestamp": timestamp
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/config/activate/{filename}")
def activate_config_version(filename: str):
    """Activate a specific configuration version"""
    try:
        versions_dir = "/app/config/versions"
        source_path = os.path.join(versions_dir, filename)
        target_path = "/app/config/search_config.json"
        
        # Verify source exists
        if not os.path.exists(source_path):
            return {"status": "error", "error": "Version not found"}
        
        # Read the version content
        with open(source_path, 'r') as f:
            config = json.load(f)
        
        # Write to active config
        with open(target_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return {
            "status": "success",
            "message": f"Configuration {filename} is now active",
            "filename": filename
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/config/version/{filename}")
def get_config_version(filename: str):
    """Get a specific configuration version"""
    try:
        versions_dir = "/app/config/versions"
        filepath = os.path.join(versions_dir, filename)
        
        if not os.path.exists(filepath):
            return {"error": "Version not found"}
        
        with open(filepath, 'r') as f:
            config = json.load(f)
        
        return {"config": config, "filename": filename}
    except Exception as e:
        return {"error": str(e)}

@app.get("/config/export")
def export_config():
    """Export current configuration as downloadable JSON"""
    try:
        config_path = "/app/config/search_config.json"
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        from fastapi.responses import JSONResponse
        import datetime
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"search_config_{timestamp}.json"
        
        return JSONResponse(
            content=config,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        return {"error": str(e)}

@app.post("/config/import")
def import_config(config: dict):
    """Import and validate configuration from uploaded file"""
    try:
        # Validate configuration structure
        validation_errors = validate_config_structure(config)
        
        if validation_errors:
            return {
                "status": "error",
                "error": "Invalid configuration structure",
                "details": validation_errors
            }
        
        # If valid, save as new version
        import datetime
        versions_dir = "/app/config/versions"
        os.makedirs(versions_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"search_config_{timestamp}.json"
        filepath = os.path.join(versions_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)
        
        return {
            "status": "success",
            "message": f"Configuration imported and saved as version {timestamp}",
            "filename": filename,
            "timestamp": timestamp
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

def validate_config_structure(config: dict) -> list:
    """Validate configuration structure and return list of errors"""
    errors = []
    
    # Check if config is a dictionary
    if not isinstance(config, dict):
        errors.append("Configuration must be a JSON object")
        return errors
    
    # Check for required top-level keys
    required_keys = ["keywords"]
    for key in required_keys:
        if key not in config:
            errors.append(f"Missing required key: '{key}'")
    
    # Validate keywords structure
    if "keywords" in config:
        if not isinstance(config["keywords"], dict):
            errors.append("'keywords' must be an object")
        else:
            for keyword_key, keyword_list in config["keywords"].items():
                if not isinstance(keyword_list, list):
                    errors.append(f"'keywords.{keyword_key}' must be an array")
    
    # Validate crawler configurations
    crawler_names = ["freelancermap", "solcom", "hays"]
    for crawler_name in crawler_names:
        if crawler_name in config:
            crawler_config = config[crawler_name]
            
            if not isinstance(crawler_config, dict):
                errors.append(f"'{crawler_name}' must be an object")
                continue
            
            # Check required crawler fields
            required_crawler_fields = ["base_url", "search_path", "queries"]
            for field in required_crawler_fields:
                if field not in crawler_config:
                    errors.append(f"'{crawler_name}.{field}' is required")
            
            # Validate queries structure
            if "queries" in crawler_config:
                if not isinstance(crawler_config["queries"], list):
                    errors.append(f"'{crawler_name}.queries' must be an array")
                else:
                    for idx, query in enumerate(crawler_config["queries"]):
                        if not isinstance(query, dict):
                            errors.append(f"'{crawler_name}.queries[{idx}]' must be an object")
                        else:
                            if "query" not in query:
                                errors.append(f"'{crawler_name}.queries[{idx}].query' is required")
                            if "keywords" not in query:
                                errors.append(f"'{crawler_name}.queries[{idx}].keywords' is required")
    
    return errors

# Debug Endpoints

@app.get("/debug/status")
def get_debug_status():
    """Get debug mode status"""
    debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    debug_dir = Path('/debug_artifacts')
    
    return {
        "debug_mode": debug_mode,
        "debug_dir": str(debug_dir),
        "debug_dir_exists": debug_dir.exists(),
        "artifact_count": len(list(debug_dir.glob('*'))) if debug_dir.exists() else 0
    }

@app.get("/debug/artifacts")
def list_debug_artifacts():
    """List all debug artifacts (screenshots and HTML dumps)"""
    debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    if not debug_mode:
        return {"error": "Debug mode is not enabled. Set DEBUG_MODE=true in .env"}
    
    debug_dir = Path('/debug_artifacts')
    if not debug_dir.exists():
        return {"artifacts": []}
    
    artifacts = []
    for file in sorted(debug_dir.glob('*'), key=lambda x: x.stat().st_mtime, reverse=True):
        if file.is_file():
            artifacts.append({
                "name": file.name,
                "size": file.stat().st_size,
                "modified": file.stat().st_mtime,
                "type": "screenshot" if file.suffix == '.png' else "html",
                "download_url": f"/debug/artifacts/{file.name}"
            })
    
    return {"artifacts": artifacts, "count": len(artifacts)}

@app.get("/debug/artifacts/{filename}")
def download_debug_artifact(filename: str):
    """Download a specific debug artifact"""
    debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    if not debug_mode:
        return {"error": "Debug mode is not enabled. Set DEBUG_MODE=true in .env"}
    
    debug_dir = Path('/debug_artifacts')
    file_path = debug_dir / filename
    
    # Security: ensure the file is within debug_dir
    if not file_path.resolve().is_relative_to(debug_dir.resolve()):
        return {"error": "Invalid file path"}
    
    if not file_path.exists():
        return {"error": "File not found"}
    
    media_type = "image/png" if file_path.suffix == '.png' else "text/html"
    return FileResponse(file_path, media_type=media_type, filename=filename)

@app.delete("/debug/artifacts")
def clear_debug_artifacts():
    """Clear all debug artifacts"""
    debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    if not debug_mode:
        return {"error": "Debug mode is not enabled. Set DEBUG_MODE=true in .env"}
    
    debug_dir = Path('/debug_artifacts')
    if not debug_dir.exists():
        return {"message": "No artifacts to clear", "deleted": 0}
    
    deleted = 0
    for file in debug_dir.glob('*'):
        if file.is_file():
            file.unlink()
            deleted += 1
    
    return {"message": f"Cleared {deleted} debug artifacts", "deleted": deleted}

# Document Management Endpoints

DOCUMENTS_DIR = Path('/app/documents')

@app.on_event("startup")
async def create_documents_dir():
    """Create documents directory on startup"""
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Documents directory ready: {DOCUMENTS_DIR}")

@app.get("/documents")
async def list_documents(auth: dict = Depends(verify_auth_or_api_key)):
    """List all documents"""
    try:
        if not DOCUMENTS_DIR.exists():
            return {"documents": [], "count": 0}
        
        documents = []
        for file in sorted(DOCUMENTS_DIR.glob('*'), key=lambda x: x.stat().st_mtime, reverse=True):
            if file.is_file():
                stat = file.stat()
                documents.append({
                    "name": file.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "modified_iso": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "download_url": f"/api/documents/{file.name}"
                })
        
        return {"documents": documents, "count": len(documents)}
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    auth: dict = Depends(verify_auth_or_api_key)
):
    """Upload a document"""
    try:
        # Security: validate filename
        if not file.filename or '..' in file.filename or '/' in file.filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Ensure documents directory exists
        DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        
        file_path = DOCUMENTS_DIR / file.filename
        
        # Save file
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"Document uploaded: {file.filename} ({len(content)} bytes)")
        
        return {
            "status": "success",
            "message": f"File '{file.filename}' uploaded successfully",
            "filename": file.filename,
            "size": len(content)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents/{filename}")
async def download_document(
    filename: str,
    auth: dict = Depends(verify_auth_or_api_key)
):
    """Download a specific document"""
    try:
        file_path = DOCUMENTS_DIR / filename
        
        # Security: ensure the file is within documents directory
        if not file_path.resolve().is_relative_to(DOCUMENTS_DIR.resolve()):
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Determine media type based on extension
        media_types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
        }
        media_type = media_types.get(file_path.suffix.lower(), 'application/octet-stream')
        
        return FileResponse(file_path, media_type=media_type, filename=filename)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{filename}")
async def delete_document(
    filename: str,
    auth: dict = Depends(verify_auth_or_api_key)
):
    """Delete a specific document"""
    try:
        file_path = DOCUMENTS_DIR / filename
        
        # Security: ensure the file is within documents directory
        if not file_path.resolve().is_relative_to(DOCUMENTS_DIR.resolve()):
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path.unlink()
        logger.info(f"Document deleted: {filename}")
        
        return {
            "status": "success",
            "message": f"File '{filename}' deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
