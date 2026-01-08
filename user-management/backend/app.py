from fastapi import FastAPI, HTTPException, Cookie, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from jose import JWTError, jwt
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="User Management API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key")
ALGORITHM = "HS256"
DATABASE_URL = os.getenv("DATABASE_URL")
SUPER_ADMIN_EMAIL = "uwe.ritter@paw-systems.com"

# Pydantic Models
class UserCreate(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    first_name: Optional[str] = Field(None, max_length=255)
    last_name: Optional[str] = Field(None, max_length=255)
    session_validity_minutes: Optional[int] = Field(None, gt=0)
    is_admin: bool = False

    @validator('email')
    def validate_email(cls, v):
        if not v.endswith('@paw-systems.com'):
            raise ValueError('Email must be a @paw-systems.com address')
        return v.lower()

class UserUpdate(BaseModel):
    email: Optional[str] = Field(None, min_length=1, max_length=255)
    first_name: Optional[str] = Field(None, max_length=255)
    last_name: Optional[str] = Field(None, max_length=255)
    session_validity_minutes: Optional[int] = Field(None, gt=0)

    @validator('email')
    def validate_email(cls, v):
        if v is not None:
            if not v.endswith('@paw-systems.com'):
                raise ValueError('Email must be a @paw-systems.com address')
            return v.lower()
        return v

class UserResponse(BaseModel):
    id: int
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    session_validity_minutes: Optional[int]
    is_admin: bool
    is_super_admin: bool
    created_at: datetime
    last_login: Optional[datetime]

class UserStats(BaseModel):
    total_users: int
    admin_users: int
    regular_users: int
    recent_logins: int

# Database connection
def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

# Authentication verification
async def verify_auth_token(auth_token: str | None = Cookie(None)):
    """Dependency to verify authentication token"""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

# Admin verification
async def verify_admin(email: str = Depends(verify_auth_token)):
    """Dependency to verify user is an admin"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT is_admin FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if not user or not user['is_admin']:
            raise HTTPException(status_code=403, detail="Admin access required")

        return email
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying admin: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify admin status")

# Super admin verification
async def verify_super_admin(email: str = Depends(verify_auth_token)):
    """Dependency to verify user is a super admin"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT is_super_admin FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if not user or not user['is_super_admin']:
            raise HTTPException(status_code=403, detail="Super admin access required")

        return email
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying super admin: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify super admin status")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return {"status": "healthy", "service": "user-management-api"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

# Check if current user is admin
@app.get("/check-admin")
async def check_admin(email: str = Depends(verify_auth_token)):
    """Check if current user has admin access"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT is_admin, is_super_admin FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if not user:
            return {"is_admin": False, "is_super_admin": False}

        return {
            "is_admin": user['is_admin'],
            "is_super_admin": user['is_super_admin']
        }
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        raise HTTPException(status_code=500, detail="Failed to check admin status")

# Get all users (admin only)
@app.get("/users", response_model=List[UserResponse])
async def get_users(
    admin_email: str = Depends(verify_admin)
):
    """Get all users (admin only)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            SELECT id, email, first_name, last_name, session_validity_minutes,
                   is_admin, is_super_admin, created_at, last_login
            FROM users
            ORDER BY is_super_admin DESC, is_admin DESC, email ASC
        """)
        users = cur.fetchall()

        cur.close()
        conn.close()

        return users
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")

# Get single user (admin only)
@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    admin_email: str = Depends(verify_admin)
):
    """Get a single user by ID (admin only)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            SELECT id, email, first_name, last_name, session_validity_minutes,
                   is_admin, is_super_admin, created_at, last_login
            FROM users
            WHERE id = %s
        """, (user_id,))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user: {str(e)}")

# Create user (admin only)
@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    user: UserCreate,
    admin_email: str = Depends(verify_admin)
):
    """Create a new user (admin only)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check if email already exists
        cur.execute("SELECT id FROM users WHERE email = %s", (user.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Email already exists")

        # Only super admin can create admin users
        if user.is_admin:
            cur.execute("SELECT is_super_admin FROM users WHERE email = %s", (admin_email,))
            admin_user = cur.fetchone()
            if not admin_user or not admin_user['is_super_admin']:
                raise HTTPException(status_code=403, detail="Only super admin can create admin users")

        cur.execute("""
            INSERT INTO users (email, first_name, last_name, session_validity_minutes, is_admin)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, email, first_name, last_name, session_validity_minutes,
                      is_admin, is_super_admin, created_at, last_login
        """, (user.email, user.first_name, user.last_name, user.session_validity_minutes, user.is_admin))

        new_user = cur.fetchone()

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"User created by {admin_email}: {new_user['email']}")
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

# Update user (admin only)
@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    admin_email: str = Depends(verify_admin)
):
    """Update a user (admin only)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check if user exists
        cur.execute("SELECT id, email FROM users WHERE id = %s", (user_id,))
        existing_user = cur.fetchone()
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check if new email already exists (if email is being updated)
        if user_update.email and user_update.email != existing_user['email']:
            cur.execute("SELECT id FROM users WHERE email = %s", (user_update.email,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Email already exists")

        # Build update query dynamically
        update_fields = []
        params = []

        if user_update.email is not None:
            update_fields.append("email = %s")
            params.append(user_update.email)

        if user_update.first_name is not None:
            update_fields.append("first_name = %s")
            params.append(user_update.first_name)

        if user_update.last_name is not None:
            update_fields.append("last_name = %s")
            params.append(user_update.last_name)

        if user_update.session_validity_minutes is not None:
            update_fields.append("session_validity_minutes = %s")
            params.append(user_update.session_validity_minutes)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        params.append(user_id)
        query = f"""
            UPDATE users
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING id, email, first_name, last_name, session_validity_minutes,
                      is_admin, is_super_admin, created_at, last_login
        """

        cur.execute(query, params)
        updated_user = cur.fetchone()

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"User updated by {admin_email}: {user_id}")
        return updated_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")

# Toggle admin status (super admin only)
@app.patch("/users/{user_id}/admin", response_model=UserResponse)
async def toggle_admin(
    user_id: int,
    super_admin_email: str = Depends(verify_super_admin)
):
    """Toggle admin status of a user (super admin only)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Get current user
        cur.execute("SELECT id, email, is_admin, is_super_admin FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Prevent modifying super admin status
        if user['is_super_admin']:
            raise HTTPException(status_code=403, detail="Cannot modify super admin status")

        new_admin_status = not user['is_admin']

        # If demoting from admin, check if they're the last admin
        if user['is_admin'] and not new_admin_status:
            cur.execute("SELECT COUNT(*) as count FROM users WHERE is_admin = TRUE")
            admin_count = cur.fetchone()['count']
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot remove the last administrator")

        # Update admin status
        cur.execute("""
            UPDATE users
            SET is_admin = %s
            WHERE id = %s
            RETURNING id, email, first_name, last_name, session_validity_minutes,
                      is_admin, is_super_admin, created_at, last_login
        """, (new_admin_status, user_id))

        updated_user = cur.fetchone()

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"User {user_id} admin status toggled to {new_admin_status} by {super_admin_email}")
        return updated_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling admin status for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to toggle admin status: {str(e)}")

# Delete user (admin only)
@app.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    admin_email: str = Depends(verify_admin)
):
    """Delete a user (admin only)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check if user exists and get their status
        cur.execute("SELECT id, email, is_admin, is_super_admin FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Prevent deleting super admin
        if user['is_super_admin']:
            raise HTTPException(status_code=403, detail="Cannot delete super admin")

        # If deleting an admin, check if they're the last admin
        if user['is_admin']:
            cur.execute("SELECT COUNT(*) as count FROM users WHERE is_admin = TRUE")
            admin_count = cur.fetchone()['count']
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot delete the last administrator")

        cur.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))
        deleted = cur.fetchone()

        if not deleted:
            raise HTTPException(status_code=404, detail="User not found")

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"User deleted by {admin_email}: {user_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")

# Get statistics (admin only)
@app.get("/stats", response_model=UserStats)
async def get_stats(
    admin_email: str = Depends(verify_admin)
):
    """Get user statistics (admin only)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Total users
        cur.execute("SELECT COUNT(*) as total FROM users")
        total = cur.fetchone()['total']

        # Admin users
        cur.execute("SELECT COUNT(*) as admins FROM users WHERE is_admin = TRUE")
        admins = cur.fetchone()['admins']

        # Recent logins (last 7 days)
        cur.execute("""
            SELECT COUNT(*) as recent
            FROM users
            WHERE last_login > NOW() - INTERVAL '7 days'
        """)
        recent = cur.fetchone()['recent']

        cur.close()
        conn.close()

        return {
            "total_users": total,
            "admin_users": admins,
            "regular_users": total - admins,
            "recent_logins": recent
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
