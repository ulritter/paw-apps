import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';

export default function UserForm({ user, isSuperAdmin, onSave, onCancel }) {
  const [formData, setFormData] = useState({
    email: '',
    first_name: '',
    last_name: '',
    session_validity_minutes: '',
    is_admin: false
  });

  useEffect(() => {
    if (user) {
      setFormData({
        email: user.email || '',
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        session_validity_minutes: user.session_validity_minutes || '',
        is_admin: user.is_admin || false
      });
    }
  }, [user]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const dataToSave = {
      ...formData,
      session_validity_minutes: formData.session_validity_minutes ? parseInt(formData.session_validity_minutes) : null,
      first_name: formData.first_name || null,
      last_name: formData.last_name || null
    };
    onSave(dataToSave);
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{user ? 'Benutzer bearbeiten' : 'Neuer Benutzer'}</h2>
          <button onClick={onCancel} className="btn-icon">
            <X size={24} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="user-form">
          <div className="form-group">
            <label htmlFor="email" className="form-label">
              E-Mail <span className="required">*</span>
            </label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              className="form-input"
              placeholder="benutzer@paw-systems.com"
              required
              autoFocus
              disabled={!!user}
            />
            {!!user && (
              <small className="form-hint">E-Mail kann nach Erstellung nicht geändert werden</small>
            )}
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="first_name" className="form-label">
                Vorname
              </label>
              <input
                type="text"
                id="first_name"
                name="first_name"
                value={formData.first_name}
                onChange={handleChange}
                className="form-input"
                placeholder="Max"
              />
            </div>

            <div className="form-group">
              <label htmlFor="last_name" className="form-label">
                Nachname
              </label>
              <input
                type="text"
                id="last_name"
                name="last_name"
                value={formData.last_name}
                onChange={handleChange}
                className="form-input"
                placeholder="Mustermann"
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="session_validity_minutes" className="form-label">
              Session-Gültigkeit (Minuten)
            </label>
            <input
              type="number"
              id="session_validity_minutes"
              name="session_validity_minutes"
              value={formData.session_validity_minutes}
              onChange={handleChange}
              className="form-input"
              placeholder="z.B. 60"
              min="1"
            />
            <small className="form-hint">
              Leer lassen für Standard-Gültigkeit
            </small>
          </div>

          {isSuperAdmin && !user && (
            <div className="form-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  name="is_admin"
                  checked={formData.is_admin}
                  onChange={handleChange}
                  className="form-checkbox"
                />
                <span>Als Administrator erstellen</span>
              </label>
              <small className="form-hint">
                Nur Super-Administratoren können Admin-Rechte vergeben
              </small>
            </div>
          )}

          <div className="form-actions">
            <button type="button" onClick={onCancel} className="btn-secondary">
              Abbrechen
            </button>
            <button type="submit" className="btn-primary">
              {user ? 'Aktualisieren' : 'Erstellen'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
