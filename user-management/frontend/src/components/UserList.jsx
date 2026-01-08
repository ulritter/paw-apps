import React from 'react';
import UserItem from './UserItem';

export default function UserList({ users, currentUserEmail, isSuperAdmin, onEdit, onDelete, onToggleAdmin }) {
  if (!users || users.length === 0) {
    return (
      <div className="empty-state">
        <p>Keine Benutzer gefunden</p>
      </div>
    );
  }

  return (
    <div className="table-container">
      <table className="user-table">
        <thead>
          <tr>
            <th>E-Mail</th>
            <th>Name</th>
            <th className="text-center">Rolle</th>
            <th className="text-center">Session (Min)</th>
            <th>Letzter Login</th>
            <th>Erstellt am</th>
            <th className="text-center">Aktionen</th>
          </tr>
        </thead>
        <tbody>
          {users.map(user => (
            <UserItem
              key={user.id}
              user={user}
              currentUserEmail={currentUserEmail}
              isSuperAdmin={isSuperAdmin}
              onEdit={onEdit}
              onDelete={onDelete}
              onToggleAdmin={onToggleAdmin}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
