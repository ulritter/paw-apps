import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';

export default function TodoForm({ todo, users = [], onSave, onCancel }) {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    priority: 'medium',
    category: '',
    due_date: '',
    assigned_to: ''
  });

  useEffect(() => {
    if (todo) {
      setFormData({
        title: todo.title || '',
        description: todo.description || '',
        priority: todo.priority || 'medium',
        category: todo.category || '',
        due_date: todo.due_date ? todo.due_date.split('T')[0] : '',
        assigned_to: todo.assigned_to || ''
      });
    }
  }, [todo]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const dataToSave = {
      ...formData,
      due_date: formData.due_date ? new Date(formData.due_date).toISOString() : null,
      category: formData.category || null,
      assigned_to: formData.assigned_to || null
    };
    onSave(dataToSave);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{todo ? 'Aufgabe bearbeiten' : 'Neue Aufgabe'}</h2>
          <button onClick={onCancel} className="btn-icon">
            <X size={24} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="todo-form">
          <div className="form-group">
            <label htmlFor="title" className="form-label">
              Titel <span className="required">*</span>
            </label>
            <input
              type="text"
              id="title"
              name="title"
              value={formData.title}
              onChange={handleChange}
              className="form-input"
              placeholder="z.B. Code Review durchführen"
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="description" className="form-label">
              Beschreibung
            </label>
            <textarea
              id="description"
              name="description"
              value={formData.description}
              onChange={handleChange}
              className="form-textarea"
              placeholder="Zusätzliche Details zur Aufgabe..."
              rows={4}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="priority" className="form-label">
                Priorität
              </label>
              <select
                id="priority"
                name="priority"
                value={formData.priority}
                onChange={handleChange}
                className="form-select"
              >
                <option value="low">Niedrig</option>
                <option value="medium">Mittel</option>
                <option value="high">Hoch</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="category" className="form-label">
                Kategorie
              </label>
              <input
                type="text"
                id="category"
                name="category"
                value={formData.category}
                onChange={handleChange}
                className="form-input"
                placeholder="z.B. Entwicklung, Design"
                list="categories"
              />
              <datalist id="categories">
                <option value="Entwicklung" />
                <option value="Design" />
                <option value="Testing" />
                <option value="Dokumentation" />
                <option value="Meeting" />
                <option value="Review" />
              </datalist>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="assigned_to" className="form-label">
              Zugewiesen an
            </label>
            <select
              id="assigned_to"
              name="assigned_to"
              value={formData.assigned_to}
              onChange={handleChange}
              className="form-select"
            >
              <option value="">Nicht zugewiesen</option>
              {users.map(user => (
                <option key={user.id} value={user.email}>{user.email}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="due_date" className="form-label">
              Fälligkeitsdatum
            </label>
            <input
              type="date"
              id="due_date"
              name="due_date"
              value={formData.due_date}
              onChange={handleChange}
              className="form-input"
              min={new Date().toISOString().split('T')[0]}
            />
          </div>

          <div className="form-actions">
            <button type="button" onClick={onCancel} className="btn-secondary">
              Abbrechen
            </button>
            <button type="submit" className="btn-primary">
              {todo ? 'Aktualisieren' : 'Erstellen'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
