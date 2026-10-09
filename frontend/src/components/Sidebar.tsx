import React from 'react';
import {
  LayoutDashboard,
  GraduationCap,
  Sparkles,
  FileText,
  CheckSquare,
  Award,
  Bell,
  Users,
  Activity,
  Compass,
  User as UserIcon
} from 'lucide-react';
import type { User } from '../types';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  user: User;
  unreadCount: number;
  onOpenProfile: (tab?: 'profile' | 'password') => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  user,
  unreadCount,
  onOpenProfile,
}) => {
  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-header">
        <div className="institution-brand">
          <div className="institution-crest">
            <GraduationCap size={18} color="#ffffff" />
          </div>
          <div className="institution-meta">
            <span className="institution-name">Apex Academic</span>
            <span className="institution-department">LMS Enterprise</span>
          </div>
        </div>
      </div>

      {/* Navigation Grouping per Role */}
      <div className="sidebar-nav">
        {/* STUDENT NAVIGATION */}
        {user.role === 'STUDENT' && (
          <>
            <div className="nav-group-label">Academic Portal</div>
            <button
              className={`nav-item ${currentTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => onSelectTab('dashboard')}
            >
              <LayoutDashboard size={16} />
              <span>Dashboard</span>
            </button>

            <button
              className={`nav-item ${currentTab === 'courses' ? 'active' : ''}`}
              onClick={() => onSelectTab('courses')}
            >
              <Compass size={16} />
              <span>Course Catalog</span>
            </button>

            <button
              className={`nav-item ${currentTab === 'materials' ? 'active' : ''}`}
              onClick={() => onSelectTab('materials')}
            >
              <FileText size={16} />
              <span>Study Materials</span>
            </button>

            <div className="nav-group-label">Evaluations & AI</div>
            <button
              className={`nav-item ${currentTab === 'assignments' ? 'active' : ''}`}
              onClick={() => onSelectTab('assignments')}
            >
              <CheckSquare size={16} />
              <span>Assignments & Quizzes</span>
            </button>

            <button
              className={`nav-item ${currentTab === 'results' ? 'active' : ''}`}
              onClick={() => onSelectTab('results')}
            >
              <Award size={16} />
              <span>Results & Gradebook</span>
            </button>

            <button
              className={`nav-item ${currentTab === 'ai-search' ? 'active' : ''}`}
              onClick={() => onSelectTab('ai-search')}
            >
              <Sparkles size={16} color={currentTab === 'ai-search' ? '#1e3a8a' : '#2563eb'} />
              <span>AI Smart Search</span>
            </button>

            <div className="nav-group-label">Personal & Alerts</div>
            <button
              className={`nav-item ${currentTab === 'notifications' ? 'active' : ''}`}
              onClick={() => onSelectTab('notifications')}
            >
              <Bell size={16} />
              <span>Notifications</span>
              {unreadCount > 0 && (
                <span className="nav-badge">{unreadCount > 9 ? '9+' : unreadCount}</span>
              )}
            </button>

            <button
              className="nav-item"
              onClick={() => onOpenProfile('profile')}
            >
              <UserIcon size={16} />
              <span>My Profile</span>
            </button>
          </>
        )}

        {/* TEACHER NAVIGATION */}
        {user.role === 'TEACHER' && (
          <>
            <div className="nav-group-label">Faculty Workspace</div>
            <button
              className={`nav-item ${currentTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => onSelectTab('dashboard')}
            >
              <LayoutDashboard size={16} />
              <span>Dashboard</span>
            </button>

            <button
              className={`nav-item ${currentTab === 'courses' ? 'active' : ''}`}
              onClick={() => onSelectTab('courses')}
            >
              <Compass size={16} />
              <span>Course Management</span>
            </button>

            <button
              className={`nav-item ${currentTab === 'materials' ? 'active' : ''}`}
              onClick={() => onSelectTab('materials')}
            >
              <FileText size={16} />
              <span>Study Materials</span>
            </button>

            <div className="nav-group-label">Curriculum Assessment</div>
            <button
              className={`nav-item ${currentTab === 'assignments' ? 'active' : ''}`}
              onClick={() => onSelectTab('assignments')}
            >
              <CheckSquare size={16} />
              <span>Assignments & Assessment</span>
            </button>

            <button
              className={`nav-item ${currentTab === 'results' ? 'active' : ''}`}
              onClick={() => onSelectTab('results')}
            >
              <Award size={16} />
              <span>Gradebook / Results</span>
            </button>

            <button
              className={`nav-item ${currentTab === 'ai-search' ? 'active' : ''}`}
              onClick={() => onSelectTab('ai-search')}
            >
              <Sparkles size={16} color={currentTab === 'ai-search' ? '#1e3a8a' : '#2563eb'} />
              <span>AI Search</span>
            </button>

            <div className="nav-group-label">Communication & Account</div>
            <button
              className={`nav-item ${currentTab === 'notifications' ? 'active' : ''}`}
              onClick={() => onSelectTab('notifications')}
            >
              <Bell size={16} />
              <span>Notifications</span>
              {unreadCount > 0 && (
                <span className="nav-badge">{unreadCount > 9 ? '9+' : unreadCount}</span>
              )}
            </button>

            <button
              className="nav-item"
              onClick={() => onOpenProfile('profile')}
            >
              <UserIcon size={16} />
              <span>Faculty Profile</span>
            </button>
          </>
        )}

        {/* ADMIN NAVIGATION */}
        {user.role === 'ADMIN' && (
          <>
            <div className="nav-group-label">Administration</div>
            <button
              className={`nav-item ${currentTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => onSelectTab('dashboard')}
            >
              <LayoutDashboard size={16} />
              <span>Dashboard</span>
            </button>

            <button
              className={`nav-item ${currentTab === 'users' ? 'active' : ''}`}
              onClick={() => onSelectTab('users')}
            >
              <Users size={16} />
              <span>Users</span>
            </button>

            <button
              className={`nav-item ${currentTab === 'courses' ? 'active' : ''}`}
              onClick={() => onSelectTab('courses')}
            >
              <Compass size={16} />
              <span>Course Management</span>
            </button>

            <button
              className={`nav-item ${currentTab === 'results' ? 'active' : ''}`}
              onClick={() => onSelectTab('results')}
            >
              <Award size={16} />
              <span>Academic Reports</span>
            </button>

            <button
              className={`nav-item ${currentTab === 'admin' ? 'active' : ''}`}
              onClick={() => onSelectTab('admin')}
            >
              <Activity size={16} />
              <span>System Health / Activity</span>
            </button>

            <button
              className={`nav-item ${currentTab === 'notifications' ? 'active' : ''}`}
              onClick={() => onSelectTab('notifications')}
            >
              <Bell size={16} />
              <span>Notifications</span>
              {unreadCount > 0 && (
                <span className="nav-badge">{unreadCount > 9 ? '9+' : unreadCount}</span>
              )}
            </button>

            <button
              className="nav-item"
              onClick={() => onOpenProfile('profile')}
            >
              <UserIcon size={16} />
              <span>Admin Profile</span>
            </button>
          </>
        )}
      </div>

      {/* Sidebar Footer with Session Information */}
      <div className="sidebar-footer">
        <div className="session-status-badge">
          <span className="session-status-dot" />
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '11px', fontWeight: 600, color: '#0f172a' }}>
              Spring 2026 Session
            </span>
            <span style={{ fontSize: '10px', color: '#64748b' }}>PostgreSQL & Redis Active</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
export default Sidebar;
