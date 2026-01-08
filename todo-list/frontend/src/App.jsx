import React, { useState, useEffect } from 'react';
import { Loader } from 'lucide-react';
import TodoList from './components/TodoList';
import TodoForm from './components/TodoForm';
import TodoStats from './components/TodoStats';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || '/api/todos';

export default function App() {
  const [todos, setTodos] = useState([]);
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [userEmail, setUserEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingTodo, setEditingTodo] = useState(null);
  const [filters, setFilters] = useState({
    completed: null,
    priority: null,
    category: null,
    assigned_to: null,
    search: ''
  });

  // Check authentication on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await fetch('/api/crawler/auth/check', {
          credentials: 'include'
        });
        const data = await response.json();

        if (!data.authenticated) {
          window.location.href = '/login.html';
          return;
        }

        setIsAuthenticated(true);
        setUserEmail(data.email || '');
        setIsCheckingAuth(false);
      } catch (error) {
        console.error('Auth check failed:', error);
        window.location.href = '/login.html';
      }
    };

    checkAuth();
  }, []);

  // Load todos and stats
  useEffect(() => {
    if (isAuthenticated) {
      loadTodos();
      loadStats();
      loadUsers();
    }
  }, [isAuthenticated, filters]);

  const loadTodos = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (filters.completed !== null) params.append('completed', filters.completed);
      if (filters.priority) params.append('priority', filters.priority);
      if (filters.category) params.append('category', filters.category);
      if (filters.assigned_to) params.append('assigned_to', filters.assigned_to);
      if (filters.search) params.append('search', filters.search);

      const response = await fetch(`${API_URL}?${params}`, {
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Failed to load todos');
      const data = await response.json();
      setTodos(data);
    } catch (err) {
      console.error('Error loading todos:', err);
      setError('Failed to load todos');
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const response = await fetch(`${API_URL}/stats`, {
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Failed to load stats');
      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error('Error loading stats:', err);
    }
  };

  const loadUsers = async () => {
    try {
      const response = await fetch(`${API_URL}/users`, {
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Failed to load users');
      const data = await response.json();
      setUsers(data);
    } catch (err) {
      console.error('Error loading users:', err);
    }
  };

  const createTodo = async (todoData) => {
    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(todoData)
      });
      if (!response.ok) throw new Error('Failed to create todo');
      await loadTodos();
      await loadStats();
      setShowForm(false);
    } catch (err) {
      console.error('Error creating todo:', err);
      setError('Failed to create todo');
    }
  };

  const updateTodo = async (id, todoData) => {
    try {
      const response = await fetch(`${API_URL}/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(todoData)
      });
      if (!response.ok) throw new Error('Failed to update todo');
      await loadTodos();
      await loadStats();
      setShowForm(false);
      setEditingTodo(null);
    } catch (err) {
      console.error('Error updating todo:', err);
      setError('Failed to update todo');
    }
  };

  const toggleComplete = async (id) => {
    try {
      const response = await fetch(`${API_URL}/${id}/complete`, {
        method: 'PATCH',
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Failed to toggle todo');
      await loadTodos();
      await loadStats();
    } catch (err) {
      console.error('Error toggling todo:', err);
      setError('Failed to toggle todo');
    }
  };

  const deleteTodo = async (id) => {
    if (!window.confirm('Möchten Sie diese Aufgabe wirklich löschen?')) return;
    try {
      const response = await fetch(`${API_URL}/${id}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Failed to delete todo');
      await loadTodos();
      await loadStats();
    } catch (err) {
      console.error('Error deleting todo:', err);
      setError('Failed to delete todo');
    }
  };

  const handleEdit = (todo) => {
    setEditingTodo(todo);
    setShowForm(true);
  };

  const handleLogout = async () => {
    try {
      await fetch('/api/crawler/auth/logout', {
        method: 'POST',
        credentials: 'include'
      });
      window.location.href = '/login.html';
    } catch (error) {
      console.error('Logout failed:', error);
      window.location.href = '/login.html';
    }
  };

  const handleHome = () => {
    window.location.href = window.location.protocol + '//' + window.location.host + '/';
  };

  if (isCheckingAuth) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
        <Loader className="animate-spin" size={48} color="white" />
      </div>
    );
  }

  return (
    <div className="app">
      <div className="container">
        {/* Header */}
        <div className="header">
          <button onClick={handleHome} className="home-btn">
            ← Home
          </button>
          <div className="header-content">
            <img src="/pws-logo.png" alt="PAW Systems" className="logo" />
            <h1>✓ Team Todo List</h1>
          </div>
          <div className="user-info">
            <span className="user-email">{userEmail}</span>
            <button onClick={handleLogout} className="logout-btn">Abmelden</button>
          </div>
        </div>

        {/* Stats Dashboard */}
        {stats && <TodoStats stats={stats} />}

        {/* Filters and Actions */}
        <div className="actions-bar">
          <button onClick={() => setShowForm(true)} className="btn-primary">
            ➕ Neue Aufgabe
          </button>

          <div className="filters">
            <select
              value={filters.completed === null ? '' : filters.completed}
              onChange={(e) => setFilters({...filters, completed: e.target.value === '' ? null : e.target.value === 'true'})}
              className="filter-select"
            >
              <option value="">Alle Aufgaben</option>
              <option value="false">Aktiv</option>
              <option value="true">Erledigt</option>
            </select>

            <select
              value={filters.priority || ''}
              onChange={(e) => setFilters({...filters, priority: e.target.value || null})}
              className="filter-select"
            >
              <option value="">Alle Prioritäten</option>
              <option value="high">Hoch</option>
              <option value="medium">Mittel</option>
              <option value="low">Niedrig</option>
            </select>

            <select
              value={filters.assigned_to || ''}
              onChange={(e) => setFilters({...filters, assigned_to: e.target.value || null})}
              className="filter-select"
            >
              <option value="">Alle Bearbeiter</option>
              {users.map(user => (
                <option key={user.id} value={user.email}>{user.email}</option>
              ))}
            </select>

            <input
              type="text"
              placeholder="🔍 Suchen..."
              value={filters.search}
              onChange={(e) => setFilters({...filters, search: e.target.value})}
              className="search-input"
            />
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="error-message">
            {error}
            <button onClick={() => setError(null)} className="error-close">×</button>
          </div>
        )}

        {/* Todo List */}
        {loading ? (
          <div className="loading">
            <Loader className="animate-spin" size={48} />
            <p>Lade Aufgaben...</p>
          </div>
        ) : (
          <TodoList
            todos={todos}
            onToggle={toggleComplete}
            onEdit={handleEdit}
            onDelete={deleteTodo}
          />
        )}

        {/* Todo Form Modal */}
        {showForm && (
          <TodoForm
            todo={editingTodo}
            users={users}
            onSave={editingTodo ? (data) => updateTodo(editingTodo.id, data) : createTodo}
            onCancel={() => {
              setShowForm(false);
              setEditingTodo(null);
            }}
          />
        )}
      </div>
    </div>
  );
}
