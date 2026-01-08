import React from 'react';
import { Users, Shield, UserCheck, Activity } from 'lucide-react';

export default function UserStats({ stats }) {
  if (!stats) return null;

  return (
    <div className="stats-grid">
      <div className="stat-card">
        <div className="stat-icon" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
          <Users size={24} color="white" />
        </div>
        <div className="stat-content">
          <div className="stat-value">{stats.total_users}</div>
          <div className="stat-label">Benutzer gesamt</div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon" style={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' }}>
          <Shield size={24} color="white" />
        </div>
        <div className="stat-content">
          <div className="stat-value">{stats.admin_users}</div>
          <div className="stat-label">Administratoren</div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon" style={{ background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' }}>
          <UserCheck size={24} color="white" />
        </div>
        <div className="stat-content">
          <div className="stat-value">{stats.regular_users}</div>
          <div className="stat-label">Normale Benutzer</div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon" style={{ background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)' }}>
          <Activity size={24} color="white" />
        </div>
        <div className="stat-content">
          <div className="stat-value">{stats.recent_logins}</div>
          <div className="stat-label">Aktive (7 Tage)</div>
        </div>
      </div>
    </div>
  );
}
