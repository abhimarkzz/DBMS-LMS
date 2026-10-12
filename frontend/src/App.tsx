import React, { useState, useEffect } from 'react';
import {
  getAuthToken,
  setAuthToken,
  removeAuthToken,
  getStoredUser,
  setStoredUser,
  removeStoredUser,
  api
} from './api';
import type { User, Course, Result, Assignment, StudyMaterial, NotificationItem } from './types';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { AuthGateway } from './components/AuthGateway';
import { DashboardView } from './views/DashboardView';
import { CourseCatalogView } from './views/CourseCatalogView';
import { CourseDetailView } from './views/CourseDetailView';
import { AISearchView } from './views/AISearchView';
import { AssignmentsView } from './views/AssignmentsView';
import { ResultsView } from './views/ResultsView';
import { NotificationsView } from './views/NotificationsView';
import { StudyMaterialsView } from './views/StudyMaterialsView';
import { AdminView } from './views/AdminView';
import { ProfileModal } from './components/ProfileModal';

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User | null>(getStoredUser());
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [activeAssignmentToOpen, setActiveAssignmentToOpen] = useState<Assignment | null>(null);
  const [aiSearchCourseId, setAiSearchCourseId] = useState<number | undefined>(undefined);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState<boolean>(false);
  const [profileModalTab, setProfileModalTab] = useState<'profile' | 'password'>('profile');

  // App Data
  const [courses, setCourses] = useState<Course[]>([]);
  const [materials, setMaterials] = useState<StudyMaterial[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [results, setResults] = useState<Result[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadNotifCount, setUnreadNotifCount] = useState<number>(0);

  // Auth & Request States
  const [authLoading, setAuthLoading] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    const token = getAuthToken();
    if (token) {
      api.getMe()
        .then((user) => {
          setCurrentUser(user);
          setStoredUser(user);
          loadAppData();
        })
        .catch(() => {
          handleLogout();
        });
    }
  }, []);

  const loadAppData = async () => {
    try {
      const [cList, aList, rList, nList] = await Promise.all([
        api.getCourses(true).catch(() => []),
        api.getAssignments().catch(() => []),
        api.getMyResults().catch(() => []),
        api.getNotifications({ limit: 20 }).catch(() => []),
      ]);

      setCourses(cList || []);
      setAssignments(aList || []);
      setResults(rList || []);
      setNotifications(nList || []);

      const unread = (nList || []).filter((n: any) => !n.is_read).length;
      setUnreadNotifCount(unread);

      // Fetch materials for all courses
      if (cList && cList.length > 0) {
        const matPromises = cList.map((c: Course) =>
          api.getCourseMaterials(c.id).catch(() => [])
        );
        const matResults = await Promise.all(matPromises);
        setMaterials(matResults.flat());
      }
    } catch (err) {
      console.warn('Error loading app data:', err);
    }
  };

  const handleLogin = async (credentials: { email: string; password: string }) => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const res = await api.login(credentials);
      setAuthToken(res.access_token);
      setCurrentUser(res.user);
      setStoredUser(res.user);
      await loadAppData();
      setActiveTab('dashboard');
    } catch (err: any) {
      setAuthError(err.message || 'Login failed. Please verify credentials.');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleRegister = async (data: { email: string; password: string; full_name: string; role: string }) => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      await api.register(data);
      // Auto-login upon registration
      await handleLogin({ email: data.email, password: data.password });
    } catch (err: any) {
      setAuthError(err.message || 'Registration failed.');
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    removeAuthToken();
    removeStoredUser();
    setCurrentUser(null);
    setActiveTab('dashboard');
    setSelectedCourse(null);
  };

  const handleMarkNotificationRead = async (id: string) => {
    try {
      await api.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadNotifCount((prev) => Math.max(0, prev - 1));
    } catch (e) {
      console.warn('Failed to mark read', e);
    }
  };

  const handleMarkAllNotificationsRead = async () => {
    try {
      await api.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadNotifCount(0);
    } catch (e) {
      console.warn('Failed to mark all read', e);
    }
  };

  const handleSelectCourse = (course: Course) => {
    setSelectedCourse(course);
    setActiveTab('course-detail');
  };

  const handleOpenAssignment = (assignment: Assignment) => {
    setActiveAssignmentToOpen(assignment);
    setActiveTab('assignments');
  };

  const handleOpenAISearchForCourse = (courseId: number) => {
    setAiSearchCourseId(courseId);
    setActiveTab('ai-search');
  };

  // If unauthenticated, render the split-screen University Gateway
  if (!currentUser) {
    return (
      <AuthGateway
        onLogin={handleLogin}
        onRegister={handleRegister}
        loading={authLoading}
        error={authError}
      />
    );
  }

  return (
    <div className="app-container">
      {/* 1. Left Modern Sidebar */}
      <Sidebar
        currentTab={activeTab}
        onSelectTab={(tab) => {
          setActiveTab(tab);
          if (tab !== 'course-detail') {
            setSelectedCourse(null);
          }
        }}
        user={currentUser}
        unreadCount={unreadNotifCount}
        onOpenProfile={(tab = 'profile') => {
          setProfileModalTab(tab);
          setIsProfileModalOpen(true);
        }}
      />

      {/* 2. Main Workspace Layout */}
      <div className="main-wrapper">
        <Navbar
          user={currentUser}
          onLogout={handleLogout}
          onNavigate={(tab) => setActiveTab(tab)}
          notifications={notifications}
          unreadCount={unreadNotifCount}
          onMarkNotificationRead={handleMarkNotificationRead}
          onMarkAllNotificationsRead={handleMarkAllNotificationsRead}
          onOpenProfile={(tab = 'profile') => {
            setProfileModalTab(tab);
            setIsProfileModalOpen(true);
          }}
        />

        <main className="content-viewport">
          {/* Active View Router */}
          {activeTab === 'dashboard' && (
            <DashboardView
              user={currentUser}
              courses={courses}
              results={results}
              assignments={assignments}
              onNavigate={(tab, param) => {
                if (tab === 'assignments' && param) {
                  handleOpenAssignment(param);
                } else {
                  setActiveTab(tab);
                }
              }}
              onSelectCourse={handleSelectCourse}
            />
          )}

          {activeTab === 'courses' && (
            <CourseCatalogView
              courses={courses}
              onSelectCourse={handleSelectCourse}
              onEnroll={async (courseId) => {
                await api.enrollCourse(courseId);
                await loadAppData();
              }}
            />
          )}

          {activeTab === 'course-detail' && selectedCourse && (
            <CourseDetailView
              course={selectedCourse}
              materials={materials}
              assignments={assignments}
              onBack={() => setActiveTab('courses')}
              onOpenAssignment={handleOpenAssignment}
              onOpenAISearchForCourse={handleOpenAISearchForCourse}
            />
          )}

          {activeTab === 'ai-search' && (
            <AISearchView
              courses={courses}
              initialCourseId={aiSearchCourseId}
            />
          )}

          {activeTab === 'materials' && (
            <StudyMaterialsView
              materials={materials}
              courses={courses}
              onOpenAISearchForCourse={handleOpenAISearchForCourse}
            />
          )}

          {activeTab === 'assignments' && (
            <AssignmentsView
              assignments={assignments}
              courses={courses}
              activeAssignmentToOpen={activeAssignmentToOpen}
              onRefresh={loadAppData}
            />
          )}

          {activeTab === 'results' && (
            <ResultsView results={results} />
          )}

          {activeTab === 'notifications' && (
            <NotificationsView
              notifications={notifications}
              onMarkRead={handleMarkNotificationRead}
              onMarkAllRead={handleMarkAllNotificationsRead}
            />
          )}

          {(activeTab === 'admin' || activeTab === 'users') && (
            <AdminView />
          )}
        </main>
      </div>

      <ProfileModal
        user={currentUser}
        courses={courses}
        initialTab={profileModalTab}
        isOpen={isProfileModalOpen}
        onClose={() => setIsProfileModalOpen(false)}
        onLogout={handleLogout}
      />
    </div>
  );
};

export default App;
