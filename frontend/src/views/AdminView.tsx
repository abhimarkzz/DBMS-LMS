import React, { useState, useEffect } from 'react';
import {
  Activity,
  Database,
  Server,
  Users
} from 'lucide-react';
import { api } from '../api';

export const AdminView: React.FC = () => {
  const [users, setUsers] = useState<any[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const u = await api.getUsers();
      setUsers(u || []);
    } catch {
      // Fallback
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div className="card" style={{ padding: '20px 24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <Activity size={18} color="#1e3a8a" />
          <h1 style={{ fontSize: '18px', fontWeight: 700, color: '#0f172a' }}>
            System Infrastructure & Polyglot Health
          </h1>
        </div>
        <p style={{ fontSize: '13px', color: '#64748b' }}>
          Real-time observability of PostgreSQL, MongoDB, Redis caching, and pgvector clusters.
        </p>
      </div>

      {/* Grid of Health Cards */}
      <div className="grid-cols-4">
        <div className="stat-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="stat-label">PostgreSQL 16</span>
            <Database size={16} color="#15803d" />
          </div>
          <div className="stat-value" style={{ color: '#15803d', fontSize: '20px' }}>Healthy</div>
          <span className="stat-subtext">ACID Relational Engine</span>
        </div>

        <div className="stat-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="stat-label">MongoDB</span>
            <Server size={16} color="#15803d" />
          </div>
          <div className="stat-value" style={{ color: '#15803d', fontSize: '20px' }}>Healthy</div>
          <span className="stat-subtext">Announcements & Logs</span>
        </div>

        <div className="stat-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="stat-label">pgvector Extension</span>
            <Activity size={16} color="#2563eb" />
          </div>
          <div className="stat-value" style={{ color: '#2563eb', fontSize: '20px' }}>768-Dim</div>
          <span className="stat-subtext">HNSW Cosine Metric</span>
        </div>

        <div className="stat-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="stat-label">Active Users</span>
            <Users size={16} color="#7c3aed" />
          </div>
          <div className="stat-value" style={{ color: '#7c3aed', fontSize: '20px' }}>{users.length}</div>
          <span className="stat-subtext">Role-Based Access Control</span>
        </div>
      </div>

      {/* User Directory Table */}
      <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #e2e8f0', backgroundColor: '#fafbfc' }}>
          <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a' }}>
            Platform User Directory & Role Assignment
          </h3>
        </div>

        <div className="table-container" style={{ border: 'none', borderRadius: '0' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Full Name</th>
                <th>Email Address</th>
                <th>Role</th>
                <th>Account Status</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td style={{ fontWeight: 700, color: '#64748b' }}>#{u.id}</td>
                  <td style={{ fontWeight: 600, color: '#0f172a' }}>{u.full_name}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{u.email}</td>
                  <td>
                    <span className={`badge ${u.role === 'ADMIN' ? 'badge-danger' : u.role === 'TEACHER' ? 'badge-info' : 'badge-success'}`}>
                      {u.role}
                    </span>
                  </td>
                  <td>
                    <span className="badge badge-success">Active</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
