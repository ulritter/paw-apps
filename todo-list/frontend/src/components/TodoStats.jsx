import React from 'react';
import { CheckCircle, Clock, AlertCircle, TrendingUp } from 'lucide-react';

export default function TodoStats({ stats }) {
  const completionRate = stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0;

  return (
    <div className="stats-container">
      <div className="stat-card">
        <div className="stat-icon" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
          <TrendingUp size={24} />
        </div>
        <div className="stat-content">
          <div className="stat-value">{stats.total}</div>
          <div className="stat-label">Gesamt</div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon" style={{ background: 'linear-gradient(135deg, #48bb78 0%, #38a169 100%)' }}>
          <CheckCircle size={24} />
        </div>
        <div className="stat-content">
          <div className="stat-value">{stats.completed}</div>
          <div className="stat-label">Erledigt</div>
          <div className="stat-progress">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${completionRate}%`, background: '#48bb78' }}
              />
            </div>
            <span className="progress-text">{completionRate}%</span>
          </div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon" style={{ background: 'linear-gradient(135deg, #4299e1 0%, #3182ce 100%)' }}>
          <Clock size={24} />
        </div>
        <div className="stat-content">
          <div className="stat-value">{stats.active}</div>
          <div className="stat-label">Aktiv</div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon" style={{ background: 'linear-gradient(135deg, #f56565 0%, #e53e3e 100%)' }}>
          <AlertCircle size={24} />
        </div>
        <div className="stat-content">
          <div className="stat-value">{stats.overdue}</div>
          <div className="stat-label">Überfällig</div>
        </div>
      </div>

      {Object.keys(stats.by_priority).length > 0 && (
        <div className="stat-card priority-breakdown">
          <div className="stat-label" style={{ marginBottom: '0.75rem', fontWeight: '600' }}>Nach Priorität</div>
          <div className="priority-list">
            {stats.by_priority.high && (
              <div className="priority-item">
                <span className="priority-badge priority-high">Hoch</span>
                <span className="priority-count">{stats.by_priority.high}</span>
              </div>
            )}
            {stats.by_priority.medium && (
              <div className="priority-item">
                <span className="priority-badge priority-medium">Mittel</span>
                <span className="priority-count">{stats.by_priority.medium}</span>
              </div>
            )}
            {stats.by_priority.low && (
              <div className="priority-item">
                <span className="priority-badge priority-low">Niedrig</span>
                <span className="priority-count">{stats.by_priority.low}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
