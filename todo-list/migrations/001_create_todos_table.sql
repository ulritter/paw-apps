-- Migration: Create todos table for team todolist
-- Date: 2026-01-08
-- Description: Creates the todos table with support for priorities, categories, and due dates

CREATE TABLE IF NOT EXISTS todos (
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
    completed_by TEXT
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_todos_completed ON todos (completed);
CREATE INDEX IF NOT EXISTS idx_todos_priority ON todos (priority);
CREATE INDEX IF NOT EXISTS idx_todos_due_date ON todos (due_date DESC);
CREATE INDEX IF NOT EXISTS idx_todos_created_at ON todos (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_todos_category ON todos (category);

-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_todos_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_todos_updated_at
    BEFORE UPDATE ON todos
    FOR EACH ROW
    EXECUTE FUNCTION update_todos_updated_at();

COMMENT ON TABLE todos IS 'Shared team todolist for PAW Systems';
COMMENT ON COLUMN todos.priority IS 'Priority level: low, medium, high';
COMMENT ON COLUMN todos.category IS 'Optional category for organizing todos';
COMMENT ON COLUMN todos.created_by IS 'Email of user who created the todo';
COMMENT ON COLUMN todos.completed_by IS 'Email of user who completed the todo';
