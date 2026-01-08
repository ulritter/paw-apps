from fastapi import FastAPI, HTTPException, Cookie, Depends, Query
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

app = FastAPI(title="Todo List API")

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

# Pydantic Models
class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    priority: str = Field(default="medium")
    category: Optional[str] = Field(None, max_length=100)
    due_date: Optional[datetime] = None
    assigned_to: Optional[str] = Field(None, max_length=255)

    @validator('priority')
    def validate_priority(cls, v):
        if v not in ['low', 'medium', 'high']:
            raise ValueError('Priority must be low, medium, or high')
        return v

class TodoUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    priority: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    due_date: Optional[datetime] = None
    assigned_to: Optional[str] = Field(None, max_length=255)

    @validator('priority')
    def validate_priority(cls, v):
        if v is not None and v not in ['low', 'medium', 'high']:
            raise ValueError('Priority must be low, medium, or high')
        return v

class TodoResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    completed: bool
    priority: str
    category: Optional[str]
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    completed_at: Optional[datetime]
    completed_by: Optional[str]
    assigned_to: Optional[str]
    assigned_to_name: Optional[str]

class TodoStats(BaseModel):
    total: int
    completed: int
    active: int
    by_priority: dict
    by_category: dict
    overdue: int

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
        return {"status": "healthy", "service": "todo-api"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

# Get all todos
@app.get("/api/todos", response_model=List[TodoResponse])
async def get_todos(
    completed: Optional[bool] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    email: str = Depends(verify_auth_token)
):
    """Get all todos with optional filters"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        query = """
            SELECT t.*,
                   CASE
                       WHEN u.first_name IS NOT NULL AND u.last_name IS NOT NULL
                       THEN CONCAT(u.first_name, ' ', u.last_name)
                       WHEN u.first_name IS NOT NULL
                       THEN u.first_name
                       WHEN u.last_name IS NOT NULL
                       THEN u.last_name
                       ELSE t.assigned_to
                   END AS assigned_to_name
            FROM todos t
            LEFT JOIN users u ON t.assigned_to = u.email
            WHERE 1=1
        """
        params = []

        if completed is not None:
            query += " AND t.completed = %s"
            params.append(completed)

        if priority:
            query += " AND t.priority = %s"
            params.append(priority)

        if category:
            query += " AND t.category = %s"
            params.append(category)

        if assigned_to:
            query += " AND t.assigned_to = %s"
            params.append(assigned_to)

        if search:
            query += " AND (t.title ILIKE %s OR t.description ILIKE %s)"
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern])

        query += " ORDER BY t.completed ASC, t.priority DESC, t.due_date ASC NULLS LAST, t.created_at DESC"

        cur.execute(query, params)
        todos = cur.fetchall()

        cur.close()
        conn.close()

        return todos
    except Exception as e:
        logger.error(f"Error fetching todos: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch todos: {str(e)}")

# Get all users (must be before /{todo_id} to avoid conflict)
@app.get("/api/todos/users", response_model=List[dict])
async def get_users(
    email: str = Depends(verify_auth_token)
):
    """Get all users from the database for assignment dropdown"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            SELECT id, email, first_name, last_name,
                   CASE
                       WHEN first_name IS NOT NULL AND last_name IS NOT NULL
                       THEN CONCAT(first_name, ' ', last_name)
                       WHEN first_name IS NOT NULL
                       THEN first_name
                       WHEN last_name IS NOT NULL
                       THEN last_name
                       ELSE email
                   END AS display_name
            FROM users
            ORDER BY display_name
        """)
        users = cur.fetchall()

        cur.close()
        conn.close()

        return users
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")

# Get single todo
@app.get("/api/todos/{todo_id}", response_model=TodoResponse)
async def get_todo(
    todo_id: int,
    email: str = Depends(verify_auth_token)
):
    """Get a single todo by ID"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            SELECT t.*,
                   CASE
                       WHEN u.first_name IS NOT NULL AND u.last_name IS NOT NULL
                       THEN CONCAT(u.first_name, ' ', u.last_name)
                       WHEN u.first_name IS NOT NULL
                       THEN u.first_name
                       WHEN u.last_name IS NOT NULL
                       THEN u.last_name
                       ELSE t.assigned_to
                   END AS assigned_to_name
            FROM todos t
            LEFT JOIN users u ON t.assigned_to = u.email
            WHERE t.id = %s
        """, (todo_id,))
        todo = cur.fetchone()

        cur.close()
        conn.close()

        if not todo:
            raise HTTPException(status_code=404, detail="Todo not found")

        return todo
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching todo {todo_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch todo: {str(e)}")

# Create todo
@app.post("/api/todos", response_model=TodoResponse, status_code=201)
async def create_todo(
    todo: TodoCreate,
    email: str = Depends(verify_auth_token)
):
    """Create a new todo"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            INSERT INTO todos (title, description, priority, category, due_date, created_by, assigned_to)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (todo.title, todo.description, todo.priority, todo.category, todo.due_date, email, todo.assigned_to))

        new_todo = cur.fetchone()
        todo_id = new_todo['id']

        # Get the todo with the user name
        cur.execute("""
            SELECT t.*,
                   CASE
                       WHEN u.first_name IS NOT NULL AND u.last_name IS NOT NULL
                       THEN CONCAT(u.first_name, ' ', u.last_name)
                       WHEN u.first_name IS NOT NULL
                       THEN u.first_name
                       WHEN u.last_name IS NOT NULL
                       THEN u.last_name
                       ELSE t.assigned_to
                   END AS assigned_to_name
            FROM todos t
            LEFT JOIN users u ON t.assigned_to = u.email
            WHERE t.id = %s
        """, (todo_id,))
        new_todo_with_name = cur.fetchone()

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"Todo created by {email}: {todo_id}")
        return new_todo_with_name
    except Exception as e:
        logger.error(f"Error creating todo: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create todo: {str(e)}")

# Update todo
@app.put("/api/todos/{todo_id}", response_model=TodoResponse)
async def update_todo(
    todo_id: int,
    todo_update: TodoUpdate,
    email: str = Depends(verify_auth_token)
):
    """Update a todo"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check if todo exists
        cur.execute("SELECT id FROM todos WHERE id = %s", (todo_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Todo not found")

        # Build update query dynamically
        update_fields = []
        params = []

        if todo_update.title is not None:
            update_fields.append("title = %s")
            params.append(todo_update.title)

        if todo_update.description is not None:
            update_fields.append("description = %s")
            params.append(todo_update.description)

        if todo_update.priority is not None:
            update_fields.append("priority = %s")
            params.append(todo_update.priority)

        if todo_update.category is not None:
            update_fields.append("category = %s")
            params.append(todo_update.category)

        if todo_update.due_date is not None:
            update_fields.append("due_date = %s")
            params.append(todo_update.due_date)

        if todo_update.assigned_to is not None:
            update_fields.append("assigned_to = %s")
            params.append(todo_update.assigned_to)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        params.append(todo_id)
        query = f"UPDATE todos SET {', '.join(update_fields)} WHERE id = %s RETURNING *"

        cur.execute(query, params)
        updated_todo = cur.fetchone()

        # Get the todo with the user name
        cur.execute("""
            SELECT t.*,
                   CASE
                       WHEN u.first_name IS NOT NULL AND u.last_name IS NOT NULL
                       THEN CONCAT(u.first_name, ' ', u.last_name)
                       WHEN u.first_name IS NOT NULL
                       THEN u.first_name
                       WHEN u.last_name IS NOT NULL
                       THEN u.last_name
                       ELSE t.assigned_to
                   END AS assigned_to_name
            FROM todos t
            LEFT JOIN users u ON t.assigned_to = u.email
            WHERE t.id = %s
        """, (todo_id,))
        updated_todo_with_name = cur.fetchone()

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"Todo updated by {email}: {todo_id}")
        return updated_todo_with_name
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating todo {todo_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update todo: {str(e)}")

# Toggle complete status
@app.patch("/api/todos/{todo_id}/complete", response_model=TodoResponse)
async def toggle_complete(
    todo_id: int,
    email: str = Depends(verify_auth_token)
):
    """Toggle the completed status of a todo"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Get current status
        cur.execute("SELECT completed FROM todos WHERE id = %s", (todo_id,))
        result = cur.fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Todo not found")

        new_status = not result['completed']

        # Update status
        if new_status:
            cur.execute("""
                UPDATE todos
                SET completed = %s, completed_at = NOW(), completed_by = %s
                WHERE id = %s
                RETURNING *
            """, (new_status, email, todo_id))
        else:
            cur.execute("""
                UPDATE todos
                SET completed = %s, completed_at = NULL, completed_by = NULL
                WHERE id = %s
                RETURNING *
            """, (new_status, todo_id))

        updated_todo = cur.fetchone()

        # Get the todo with the user name
        cur.execute("""
            SELECT t.*,
                   CASE
                       WHEN u.first_name IS NOT NULL AND u.last_name IS NOT NULL
                       THEN CONCAT(u.first_name, ' ', u.last_name)
                       WHEN u.first_name IS NOT NULL
                       THEN u.first_name
                       WHEN u.last_name IS NOT NULL
                       THEN u.last_name
                       ELSE t.assigned_to
                   END AS assigned_to_name
            FROM todos t
            LEFT JOIN users u ON t.assigned_to = u.email
            WHERE t.id = %s
        """, (todo_id,))
        updated_todo_with_name = cur.fetchone()

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"Todo {todo_id} marked as {'completed' if new_status else 'active'} by {email}")
        return updated_todo_with_name
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling todo {todo_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to toggle todo: {str(e)}")

# Delete todo
@app.delete("/api/todos/{todo_id}", status_code=204)
async def delete_todo(
    todo_id: int,
    email: str = Depends(verify_auth_token)
):
    """Delete a todo"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("DELETE FROM todos WHERE id = %s RETURNING id", (todo_id,))
        deleted = cur.fetchone()

        if not deleted:
            raise HTTPException(status_code=404, detail="Todo not found")

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"Todo deleted by {email}: {todo_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting todo {todo_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete todo: {str(e)}")

# Get statistics
@app.get("/api/todos/stats", response_model=TodoStats)
async def get_stats(
    email: str = Depends(verify_auth_token)
):
    """Get todo statistics"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Total and completed counts
        cur.execute("SELECT COUNT(*) as total FROM todos")
        total = cur.fetchone()['total']

        cur.execute("SELECT COUNT(*) as completed FROM todos WHERE completed = true")
        completed = cur.fetchone()['completed']

        # By priority
        cur.execute("""
            SELECT priority, COUNT(*) as count
            FROM todos
            WHERE completed = false
            GROUP BY priority
        """)
        by_priority = {row['priority']: row['count'] for row in cur.fetchall()}

        # By category
        cur.execute("""
            SELECT category, COUNT(*) as count
            FROM todos
            WHERE completed = false AND category IS NOT NULL
            GROUP BY category
        """)
        by_category = {row['category']: row['count'] for row in cur.fetchall()}

        # Overdue count
        cur.execute("""
            SELECT COUNT(*) as overdue
            FROM todos
            WHERE completed = false
            AND due_date < NOW()
        """)
        overdue = cur.fetchone()['overdue']

        cur.close()
        conn.close()

        return {
            "total": total,
            "completed": completed,
            "active": total - completed,
            "by_priority": by_priority,
            "by_category": by_category,
            "overdue": overdue
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
