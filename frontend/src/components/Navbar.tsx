import React, { useState } from 'react';
import {
  Bell,
  User as UserIcon,
  LogOut,
  ChevronDown,
  Shield,
  GraduationCap,
  BookOpen,
  ExternalLink,
  KeyRound
} from 'lucide-react';
import type { User, NotificationItem } from '../types';

interface NavbarProps {
  user: User;
  onLogout: () => void;
  onNavigate: (tab: string) => void;
  notifications: NotificationItem[];
  unreadCount: number;
  onMarkNotificationRead: (id: string) => void;
  onMarkAllNotificationsRead: () => void;
  onOpenProfile: (tab?: 'profile' | 'password') => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  onLogout,
  onNavigate,
  notifications,
  unreadCount,
  onMarkNotificationRead,
  onMarkAllNotificationsRead,
  onOpenProfile,
}) => {
  const [showNotifDropdown, setShowNotifDropdown] = useState(false);
  const [showProfileDropdown, setShowProfileDropdown] = useState(false);

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'ADMIN':
        return { label: 'Administrator', bg: '#fef2f2', color: '#b91c1c', icon: Shield };
      case 'TEACHER':
        return { label: 'Faculty', bg: '#eff6ff', color: '#1d4ed8', icon: BookOpen };
      default:
        return { label: 'Student', bg: '#f0fdf4', color: '#15803d', icon: GraduationCap };
    }
  };

  const roleInfo = getRoleBadge(user.role);
  const RoleIcon = roleInfo.icon;

  return (
    <header className="topbar">
      {/* Left Spacer */}
      <div style={{ display: 'flex', alignItems: 'center' }} />

      {/* Right Controls: Notifications, Profile */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>

        {/* Notification Bell */}
        <div className="notification-bell-container">
          <button
            className="notification-bell-btn"
            onClick={() => setShowNotifDropdown(!showNotifDropdown)}
            title="Notifications"
          >
            <Bell size={18} />
            {unreadCount > 0 && (
              <span className="notif-count-badge">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {showNotifDropdown && (
            <div className="notif-dropdown-menu">
              <div className="notif-dropdown-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Bell size={15} color="#1e3a8a" />
                  <span style={{ fontWeight: 700, fontSize: '13.5px', color: '#0f172a' }}>
                    Notifications
                  </span>
                  {unreadCount > 0 && (
                    <span className="badge badge-info" style={{ fontSize: '10.5px' }}>
                      {unreadCount} unread
                    </span>
                  )}
                </div>
                {unreadCount > 0 && (
                  <button
                    onClick={onMarkAllNotificationsRead}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#2563eb',
                      fontSize: '11.5px',
                      cursor: 'pointer',
                      fontWeight: 600,
                    }}
                  >
                    Mark all read
                  </button>
                )}
              </div>

              <div className="notif-dropdown-body">
                {notifications.length === 0 ? (
                  <div style={{ padding: '24px 16px', textAlign: 'center', color: '#64748b', fontSize: '12.5px' }}>
                    No notifications yet.
                  </div>
                ) : (
                  notifications.slice(0, 5).map((n) => (
                    <div
                      key={n.id}
                      className={`notif-item ${!n.is_read ? 'unread' : ''}`}
                      onClick={() => onMarkNotificationRead(n.id)}
                    >
                      <div className="notif-content">
                        <div className="notif-header">
                          <span className="notif-title">{n.title}</span>
                          {!n.is_read && <span className="notif-dot" />}
                        </div>
                        <p className="notif-msg">{n.message}</p>
                        <div className="notif-footer">
                          <span>{new Date(n.created_at).toLocaleDateString()}</span>
                          <span style={{ textTransform: 'capitalize', color: '#64748b' }}>
                            {n.notif_type.toLowerCase()}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="notif-dropdown-footer">
                <button
                  className="btn btn-secondary btn-sm"
                  style={{ width: '100%', justifyContent: 'center' }}
                  onClick={() => {
                    setShowNotifDropdown(false);
                    onNavigate('notifications');
                  }}
                >
                  View All Notifications <ExternalLink size={12} />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* User Profile Pill & Dropdown */}
        <div className="user-menu-container">
          <button
            className="user-menu-btn"
            onClick={() => setShowProfileDropdown(!showProfileDropdown)}
          >
            <div className="user-menu-avatar">
              {user.full_name?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="user-menu-text">
              <span className="user-menu-name">
                {user.full_name}
                <ChevronDown size={13} color="#64748b" />
              </span>
              <span className="user-menu-email">{user.email}</span>
            </div>
          </button>

          {showProfileDropdown && (
            <div className="user-dropdown-menu">
              <div className="user-dropdown-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <RoleIcon size={14} color={roleInfo.color} />
                  <span
                    style={{
                      backgroundColor: roleInfo.bg,
                      color: roleInfo.color,
                      padding: '2px 8px',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontWeight: 700,
                    }}
                  >
                    {roleInfo.label}
                  </span>
                </div>
                <div style={{ fontSize: '13px', fontWeight: 600, marginTop: '6px', color: '#0f172a' }}>
                  {user.full_name}
                </div>
                <div style={{ fontSize: '11px', color: '#64748b' }}>{user.email}</div>
              </div>

              <button
                className="user-dropdown-item"
                onClick={() => {
                  setShowProfileDropdown(false);
                  onOpenProfile('profile');
                }}
              >
                <UserIcon size={15} />
                <span>My Profile</span>
              </button>

              <button
                className="user-dropdown-item"
                onClick={() => {
                  setShowProfileDropdown(false);
                  onOpenProfile('password');
                }}
              >
                <KeyRound size={15} />
                <span>Change Password</span>
              </button>

              <div className="user-dropdown-divider" />

              <button
                className="user-dropdown-item danger"
                onClick={() => {
                  setShowProfileDropdown(false);
                  onLogout();
                }}
              >
                <LogOut size={15} />
                <span>Sign Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
export default Navbar;
