import React from 'react';
import { Edit2, Trash2, Shield, Crown } from 'lucide-react';

export default function UserItem({ user, currentUserEmail, isSuperAdmin, onEdit, onDelete, onToggleAdmin }) {
  const formatDate = (dateString) => {
    if (!dateString) return 'Nie';
    const date = new Date(dateString);
    return date.toLocaleString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getFullName = () => {
    if (user.first_name && user.last_name) {
      return `${user.first_name} ${user.last_name}`;
    } else if (user.first_name) {
      return user.first_name;
    } else if (user.last_name) {
      return user.last_name;
    }
    return '-';
  };

  return (
    <tr className={user.is_super_admin ? 'super-admin-row' : ''}>
      <td>
        <div className="user-email-cell">
          {user.email}
          {user.is_super_admin && (
            <span className="super-admin-badge" title="Super Administrator">
              <Crown size={14} />
            </span>
          )}
        </div>
      </td>
      <td>{getFullName()}</td>
      <td className="text-center">
        {user.is_super_admin ? (
          <span className="admin-badge super-admin">
            <Crown size={14} /> Super Admin
          </span>
        ) : user.is_admin ? (
          <span className="admin-badge admin">
            <Shield size={14} /> Admin
          </span>
        ) : (
          <span className="admin-badge user">Benutzer</span>
        )}
      </td>
      <td className="text-center">{user.session_validity_minutes || '-'}</td>
      <td>{formatDate(user.last_login)}</td>
      <td>{formatDate(user.created_at)}</td>
      <td className="actions-cell">
        <button
          onClick={() => onEdit(user)}
          className="btn-icon"
          title="Bearbeiten"
        >
          <Edit2 size={16} />
        </button>

        {!user.is_super_admin && isSuperAdmin && (
          <button
            onClick={() => onToggleAdmin(user)}
            className="btn-icon btn-admin"
            title={user.is_admin ? "Admin-Rechte entziehen" : "Admin-Rechte gewähren"}
          >
            <Shield size={16} />
          </button>
        )}

        {!user.is_super_admin && user.email !== currentUserEmail && (
          <button
            onClick={() => onDelete(user.id)}
            className="btn-icon btn-delete"
            title="Löschen"
          >
            <Trash2 size={16} />
          </button>
        )}
      </td>
    </tr>
  );
}
