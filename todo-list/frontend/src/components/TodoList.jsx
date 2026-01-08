import React from 'react';
import TodoItem from './TodoItem';

export default function TodoList({ todos, onToggle, onEdit, onDelete }) {
  if (todos.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">✓</div>
        <h3>Keine Aufgaben gefunden</h3>
        <p>Erstellen Sie eine neue Aufgabe, um loszulegen!</p>
      </div>
    );
  }

  // Group todos by completion status
  const activeTodos = todos.filter(todo => !todo.completed);
  const completedTodos = todos.filter(todo => todo.completed);

  return (
    <div className="todo-list">
      {activeTodos.length > 0 && (
        <div className="todo-section">
          <h2 className="section-title">
            Aktive Aufgaben ({activeTodos.length})
          </h2>
          {activeTodos.map(todo => (
            <TodoItem
              key={todo.id}
              todo={todo}
              onToggle={onToggle}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}

      {completedTodos.length > 0 && (
        <div className="todo-section">
          <h2 className="section-title">
            Erledigt ({completedTodos.length})
          </h2>
          {completedTodos.map(todo => (
            <TodoItem
              key={todo.id}
              todo={todo}
              onToggle={onToggle}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}
