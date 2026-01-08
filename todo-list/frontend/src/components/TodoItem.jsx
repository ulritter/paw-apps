import React from 'react';
import { Calendar, User, Edit2, Trash2 } from 'lucide-react';

export default function TodoItem({ todo, onToggle, onEdit, onDelete }) {
  const formatDate = (dateString) => {
    if (!dateString) return null;
    const date = new Date(dateString);
    return date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
  };

  const isOverdue = () => {
    if (!todo.due_date || todo.completed) return false;
    return new Date(todo.due_date) < new Date();
  };

  const getPriorityColor = () => {
    switch (todo.priority) {
      case 'high': return '#f56565';
      case 'medium': return '#ed8936';
      case 'low': return '#48bb78';
      default: return '#a0aec0';
    }
  };

  const getPriorityLabel = () => {
    switch (todo.priority) {
      case 'high': return 'Hoch';
      case 'medium': return 'Mittel';
      case 'low': return 'Niedrig';
      default: return 'Keine';
    }
  };

  return (
    <div className={`todo-item ${todo.completed ? 'completed' : ''} ${isOverdue() ? 'overdue' : ''}`}>
      <div className="todo-checkbox">
        <input
          type="checkbox"
          checked={todo.completed}
          onChange={() => onToggle(todo.id)}
          className="checkbox"
        />
      </div>

      <div className="todo-content">
        <div className="todo-header">
          <h3 className="todo-title">{todo.title}</h3>
          <div className="todo-actions">
            <button
              onClick={() => onEdit(todo)}
              className="btn-icon"
              title="Bearbeiten"
            >
              <Edit2 size={16} />
            </button>
            <button
              onClick={() => onDelete(todo.id)}
              className="btn-icon btn-delete"
              title="Löschen"
            >
              <Trash2 size={16} />
            </button>
          </div>
        </div>

        {todo.description && (
          <p className="todo-description">{todo.description}</p>
        )}

        <div className="todo-meta">
          <span
            className="priority-badge"
            style={{ backgroundColor: getPriorityColor() }}
          >
            {getPriorityLabel()}
          </span>

          {todo.category && (
            <span className="category-badge">
              {todo.category}
            </span>
          )}

          {todo.due_date && (
            <span className={`due-date ${isOverdue() ? 'overdue' : ''}`}>
              <Calendar size={14} />
              {formatDate(todo.due_date)}
              {isOverdue() && ' (Überfällig)'}
            </span>
          )}

          {todo.assigned_to && (
            <span className="assigned-to">
              <User size={14} />
              Zugewiesen: {todo.assigned_to_name || todo.assigned_to}
            </span>
          )}

          {todo.created_by && (
            <span className="created-by">
              <User size={14} />
              Erstellt: {todo.created_by}
            </span>
          )}
        </div>

        {todo.completed && todo.completed_at && (
          <div className="completion-info">
            Erledigt am {formatDate(todo.completed_at)}
            {todo.completed_by && ` von ${todo.completed_by}`}
          </div>
        )}
      </div>
    </div>
  );
}
