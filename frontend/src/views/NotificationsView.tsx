import React, { useState } from 'react';
import {
  Bell,
  CheckCircle2,
  BookOpen,
  Award,
  Megaphone,
  FileCheck
} from 'lucide-react';
import type { NotificationItem } from '../types';

interface NotificationsViewProps {
  notifications: NotificationItem[];
  onMarkRead: (id: string) => void;
  onMarkAllRead: () => void;
}

export const NotificationsView: React.FC<NotificationsViewProps> = ({
  notifications,
  onMarkRead,
  onMarkAllRead,
}) => {
  const [filter, setFilter] = useState<'ALL' | 'UNREAD' | 'GRADE' | 'ASSIGNMENT' | 'ANNOUNCEMENT'>('ALL');

  const filtered = notifications.filter((n) => {
    if (filter === 'UNREAD') return !n.is_read;
    const typeUpper = (n.notif_type || '').toUpperCase();
    if (filter === 'GRADE') {
      return typeUpper.includes('GRADE') || typeUpper.includes('RESULT');
    }
    if (filter === 'ASSIGNMENT') {
      return typeUpper.includes('ASSIGNMENT') || typeUpper.includes('SUBMISSION');
    }
    if (filter === 'ANNOUNCEMENT') {
      return typeUpper.includes('ANNOUNCEMENT') || typeUpper.includes('COURSE') || typeUpper.includes('ENROLLMENT');
    }
    return true;
  });

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const getNotifIcon = (type: string) => {
    const t = (type || '').toUpperCase();
    if (t.includes('GRADE') || t.includes('RESULT')) {
      return <Award size={18} />;
    }
    if (t.includes('ANNOUNCEMENT')) {
      return <Megaphone size={18} />;
    }
    if (t.includes('SUBMISSION')) {
      return <FileCheck size={18} />;
    }
    return <BookOpen size={18} />;
  };

  const getIconColor = (type: string) => {
    const t = (type || '').toUpperCase();
    if (t.includes('GRADE') || t.includes('RESULT')) {
      return { bg: '#dcfce7', color: '#15803d' };
    }
    if (t.includes('ANNOUNCEMENT')) {
      return { bg: '#fef3c7', color: '#b45309' };
    }
    if (t.includes('SUBMISSION')) {
      return { bg: '#f3e8ff', color: '#7e22ce' };
    }
    return { bg: '#eff6ff', color: '#1e3a8a' };
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div className="card" style={{ padding: '20px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Bell size={18} color="#1e3a8a" />
              <h1 style={{ fontSize: '18px', fontWeight: 700, color: '#0f172a' }}>
                Academic Notification Center
              </h1>
              {unreadCount > 0 && (
                <span className="badge badge-info">{unreadCount} Unread</span>
              )}
            </div>
            <p style={{ fontSize: '13px', color: '#64748b', marginTop: '4px' }}>
              Real-time notices generated from live database triggers, grading events, and course announcements.
            </p>
          </div>

          {unreadCount > 0 && (
            <button className="btn btn-secondary btn-sm" onClick={onMarkAllRead}>
              <CheckCircle2 size={13} color="#15803d" /> Mark All as Read
            </button>
          )}
        </div>

        {/* Filter buttons */}
        <div style={{ display: 'flex', gap: '8px', marginTop: '16px', flexWrap: 'wrap' }}>
          {[
            { id: 'ALL', label: 'All Notices' },
            { id: 'UNREAD', label: `Unread (${unreadCount})` },
            { id: 'GRADE', label: 'Grades & Results' },
            { id: 'ASSIGNMENT', label: 'Assignments' },
            { id: 'ANNOUNCEMENT', label: 'Announcements' },
          ].map((f) => (
            <button
              key={f.id}
              className={`type-tab-btn ${filter === f.id ? 'active' : ''}`}
              style={{ fontSize: '12px', padding: '6px 14px' }}
              onClick={() => setFilter(f.id as any)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Notifications List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {filtered.length === 0 ? (
          <div className="empty-state">
            <Bell className="empty-state-icon" />
            <div className="empty-state-title">No Notifications</div>
            <p className="empty-state-desc">You are all caught up on academic alerts in this view.</p>
          </div>
        ) : (
          filtered.map((n) => {
            const iconStyle = getIconColor(n.notif_type);
            return (
              <div
                key={n.id}
                className={`card ${!n.is_read ? 'notif-unread-card' : ''}`}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '16px 20px',
                  cursor: 'pointer',
                  backgroundColor: !n.is_read ? '#f0f7ff' : '#ffffff',
                  borderColor: !n.is_read ? '#bfdbfe' : '#e2e8f0',
                  transition: 'all 0.15s ease',
                }}
                onClick={() => onMarkRead(n.id)}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
                  <div
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '8px',
                      backgroundColor: iconStyle.bg,
                      color: iconStyle.color,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    {getNotifIcon(n.notif_type)}
                  </div>

                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <h3 style={{ fontSize: '14.5px', fontWeight: 600, color: '#0f172a' }}>{n.title}</h3>
                      {!n.is_read && <span className="notif-dot" />}
                    </div>
                    <p style={{ fontSize: '13px', color: '#475569', marginTop: '2px' }}>{n.message}</p>
                    <span style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px', display: 'inline-block' }}>
                      {new Date(n.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>

                {!n.is_read && (
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      onMarkRead(n.id);
                    }}
                  >
                    Mark Read
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
export default NotificationsView;
