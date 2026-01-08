import React, { useState, useEffect } from 'react';
import { Loader } from 'lucide-react';
import UserList from './components/UserList';
import UserForm from './components/UserForm';
import UserStats from './components/UserStats';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || '/api/user-management';

export default function App() {
  const [users, setUsers] = useState([]);
  const [stats, setStats] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [isSuperAdmin, setIsSuperAdmin] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [userEmail, setUserEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterAdmin, setFilterAdmin] = useState('all');

  // Check authentication on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // First check if user is authenticated
        const authResponse = await fetch('/api/crawler/auth/check', {
          credentials: 'include'
        });
        const authData = await authResponse.json();

        if (!authData.authenticated) {
          window.location.href = '/login.html';
          return;
        }

        setUserEmail(authData.email || '');
        setIsAuthenticated(true);

        // Then check if user is admin
        const adminResponse = await fetch(`${API_URL}/check-admin`, {
          credentials: 'include'
        });

        if (!adminResponse.ok) {
          // User is not admin, redirect to landing page
          window.location.href = '/';
          return;
        }

        const adminData = await adminResponse.json();

        if (!adminData.is_admin) {
          // User is not admin, redirect to landing page
          window.location.href = '/';
          return;
        }

        setIsAdmin(adminData.is_admin);
        setIsSuperAdmin(adminData.is_super_admin);
        setIsCheckingAuth(false);
      } catch (error) {
        console.error('Auth check failed:', error);
        window.location.href = '/login.html';
      }
    };

    checkAuth();
  }, []);

  // Load users and stats
  useEffect(() => {
    if (isAuthenticated && isAdmin) {
      loadUsers();
      loadStats();
    }
  }, [isAuthenticated, isAdmin]);

  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/users`, {
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Failed to load users');
      const data = await response.json();
      setUsers(data);
    } catch (err) {
      console.error('Error loading users:', err);
      setError('Fehler beim Laden der Benutzer');
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

  const createUser = async (userData) => {
    try {
      const response = await fetch(`${API_URL}/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(userData)
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create user');
      }
      await loadUsers();
      await loadStats();
      setShowForm(false);
    } catch (err) {
      console.error('Error creating user:', err);
      setError(err.message);
    }
  };

  const updateUser = async (id, userData) => {
    try {
      // Remove email and is_admin from update data
      const { email, is_admin, ...updateData } = userData;

      const response = await fetch(`${API_URL}/users/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(updateData)
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update user');
      }
      await loadUsers();
      await loadStats();
      setShowForm(false);
      setEditingUser(null);
    } catch (err) {
      console.error('Error updating user:', err);
      setError(err.message);
    }
  };

  const deleteUser = async (id) => {
    if (!window.confirm('Möchten Sie diesen Benutzer wirklich löschen?')) return;
    try {
      const response = await fetch(`${API_URL}/users/${id}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete user');
      }
      await loadUsers();
      await loadStats();
    } catch (err) {
      console.error('Error deleting user:', err);
      setError(err.message);
    }
  };

  const toggleAdmin = async (user) => {
    const action = user.is_admin ? 'entziehen' : 'gewähren';
    if (!window.confirm(`Möchten Sie ${user.email} wirklich Admin-Rechte ${action}?`)) return;

    try {
      const response = await fetch(`${API_URL}/users/${user.id}/admin`, {
        method: 'PATCH',
        credentials: 'include'
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to toggle admin status');
      }
      await loadUsers();
      await loadStats();
    } catch (err) {
      console.error('Error toggling admin:', err);
      setError(err.message);
    }
  };

  const handleEdit = (user) => {
    setEditingUser(user);
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

  // Filter users based on search and admin filter
  const filteredUsers = users.filter(user => {
    const matchesSearch = user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (user.first_name && user.first_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
                         (user.last_name && user.last_name.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesAdminFilter = filterAdmin === 'all' ||
                              (filterAdmin === 'admin' && user.is_admin) ||
                              (filterAdmin === 'user' && !user.is_admin);

    return matchesSearch && matchesAdminFilter;
  });

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
            <h1>👥 Benutzerverwaltung</h1>
          </div>
          <div className="user-info">
            <span className="user-email">{userEmail}</span>
            <button onClick={handleLogout} className="logout-btn">Abmelden</button>
          </div>
        </div>

        {/* Stats Dashboard */}
        {stats && <UserStats stats={stats} />}

        {/* Filters and Actions */}
        <div className="actions-bar">
          <button onClick={() => setShowForm(true)} className="btn-primary">
            ➕ Neuer Benutzer
          </button>

          <div className="filters">
            <select
              value={filterAdmin}
              onChange={(e) => setFilterAdmin(e.target.value)}
              className="filter-select"
            >
              <option value="all">Alle Rollen</option>
              <option value="admin">Nur Administratoren</option>
              <option value="user">Nur Benutzer</option>
            </select>

            <input
              type="text"
              placeholder="🔍 Suchen..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
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

        {/* User List */}
        {loading ? (
          <div className="loading">
            <Loader className="animate-spin" size={48} />
            <p>Lade Benutzer...</p>
          </div>
        ) : (
          <UserList
            users={filteredUsers}
            currentUserEmail={userEmail}
            isSuperAdmin={isSuperAdmin}
            onEdit={handleEdit}
            onDelete={deleteUser}
            onToggleAdmin={toggleAdmin}
          />
        )}

        {/* User Form Modal */}
        {showForm && (
          <UserForm
            user={editingUser}
            isSuperAdmin={isSuperAdmin}
            onSave={editingUser ? (data) => updateUser(editingUser.id, data) : createUser}
            onCancel={() => {
              setShowForm(false);
              setEditingUser(null);
            }}
          />
        )}
      </div>
    </div>
  );
}
