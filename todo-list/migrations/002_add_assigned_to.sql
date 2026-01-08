-- Migration: Add assigned_to field for task assignment
-- Date: 2026-01-08
-- Description: Adds assigned_to field to track who is responsible for each todo

-- Add assigned_to column
ALTER TABLE todos ADD COLUMN IF NOT EXISTS assigned_to TEXT;

-- Add index for filtering by assignee
CREATE INDEX IF NOT EXISTS idx_todos_assigned_to ON todos (assigned_to);

-- Add comment
COMMENT ON COLUMN todos.assigned_to IS 'Email of user assigned to this todo';
