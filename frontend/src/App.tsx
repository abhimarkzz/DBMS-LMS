import React, { useState, useEffect, useCallback } from 'react';
import {
  BookOpen, GraduationCap, CheckCircle2, Search, Bell,
  Activity, Award, FileText, LogOut, PlusCircle,
  Database, Server, RefreshCw, BarChart2, AlertCircle, Clock
} from 'lucide-react';
import { api, getStoredUser, setStoredUser, setAuthToken, removeAuthToken, removeStoredUser } from './api';

export default function App() {
  const [currentUser, setCurrentUser] = useState<any>(getStoredUser());
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [notificationCount, setNotificationCount] = useState<number>(0);

  // Auth form state
  const [isRegistering, setIsRegistering] = useState<boolean>(false);
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [fullName, setFullName] = useState<string>('');
  const [role, setRole] = useState<string>('STUDENT');
  const [authError, setAuthError] = useState<string>('');
  const [authLoading, setAuthLoading] = useState<boolean>(false);

  // Data states
  const [courses, setCourses] = useState<any[]>([]);
  const [assignments, setAssignments] = useState<any[]>([]);
  const [progressView, setProgressView] = useState<any[]>([]);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [healthStatus, setHealthStatus] = useState<any>(null);
  const [adminOverview, setAdminOverview] = useState<any>(null);
  const [allUsers, setAllUsers] = useState<any[]>([]);
  const [courseSummaryView, setCourseSummaryView] = useState<any[]>([]);

  // Modals & Action states
  const [selectedCourse, setSelectedCourse] = useState<any>(null);
  const [selectedAssignment, setSelectedAssignment] = useState<any>(null);
  const [assignmentSubmissions, setAssignmentSubmissions] = useState<any[]>([]);
  const [showCourseModal, setShowCourseModal] = useState<boolean>(false);
  const [showMaterialModal, setShowMaterialModal] = useState<boolean>(false);
  const [showAssignmentModal, setShowAssignmentModal] = useState<boolean>(false);
  const [showSubmitModal, setShowSubmitModal] = useState<boolean>(false);
  const [showGradingModal, setShowGradingModal] = useState<boolean>(false);
  const [showLeaderboardModal, setShowLeaderboardModal] = useState<boolean>(false);
  const [leaderboardData, setLeaderboardData] = useState<any[]>([]);
  const [selectedCourseLeaderboardTitle, setSelectedCourseLeaderboardTitle] = useState<string>('');

  // Form input states
  const [newCourseCode, setNewCourseCode] = useState('');
  const [newCourseTitle, setNewCourseTitle] = useState('');
  const [newCourseDesc, setNewCourseDesc] = useState('');
  const [newCourseSyllabus, setNewCourseSyllabus] = useState('');

  const [newMaterialTitle, setNewMaterialTitle] = useState('');
  const [newMaterialContent, setNewMaterialContent] = useState('');
  const [materialCourseId, setMaterialCourseId] = useState<number | null>(null);

  const [newAssignmentTitle, setNewAssignmentTitle] = useState('');
  const [newAssignmentDesc, setNewAssignmentDesc] = useState('');
  const [newAssignmentScore, setNewAssignmentScore] = useState<number>(100);
  const [assignmentCourseId, setAssignmentCourseId] = useState<number | null>(null);

  const [submissionContent, setSubmissionContent] = useState('');
  const [submissionFileUrl, setSubmissionFileUrl] = useState('');

  const [activeSubmission, setActiveSubmission] = useState<any>(null);
  const [gradeScore, setGradeScore] = useState<number>(100);
  const [gradeFeedback, setGradeFeedback] = useState<string>('');

  // AI Search states
  const [searchQuery, setSearchQuery] = useState('');
  const [searchCourseId, setSearchCourseId] = useState<number | undefined>(undefined);
  const [aiResult, setAiResult] = useState<any>(null);
  const [aiSearching, setAiSearching] = useState(false);

  // Global flash message
  const [flashMessage, setFlashMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const showFlash = (type: 'success' | 'error', text: string) => {
    setFlashMessage({ type, text });
    setTimeout(() => setFlashMessage(null), 4000);
  };

  const loadInitialData = useCallback(async () => {
    if (!currentUser) return;
    try {
      const [cList, aList, notifs] = await Promise.all([
        api.getCourses(),
        api.getAssignments(),
        api.getNotifications()
      ]);
      setCourses(cList);
      setAssignments(aList);
      setNotifications(notifs);
      setNotificationCount(notifs.filter(n => !n.is_read).length);

      if (currentUser.role === 'STUDENT') {
        const prog = await api.getProgressView();
        setProgressView(prog);
      } else if (currentUser.role === 'TEACHER' || currentUser.role === 'ADMIN') {
        const summary = await api.getCourseSummaryView();
        setCourseSummaryView(summary);
      }

      if (currentUser.role === 'ADMIN') {
        const [overview, health, users] = await Promise.all([
          api.getAdminOverview(),
          api.getHealth(),
          api.getUsers()
        ]);
        setAdminOverview(overview);
        setHealthStatus(health);
        setAllUsers(users);
      }
    } catch (err: any) {
      console.error("Data load error:", err);
    }
  }, [currentUser]);

  useEffect(() => {
    if (currentUser) {
      loadInitialData();
    }
  }, [currentUser, loadInitialData]);


  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    setAuthLoading(true);
    try {
      if (isRegistering) {
        const res = await api.register({ email, password, full_name: fullName, role });
        setAuthToken(res.access_token);
        setStoredUser(res.user);
        setCurrentUser(res.user);
        showFlash('success', `Welcome ${res.user.full_name}! Account created.`);
      } else {
        const res = await api.login({ email, password });
        setAuthToken(res.access_token);
        setStoredUser(res.user);
        setCurrentUser(res.user);
        showFlash('success', `Welcome back, ${res.user.full_name}!`);
      }
    } catch (err: any) {
      setAuthError(err.message || 'Authentication failed');
    } finally {
      setAuthLoading(false);
    }
  };

  const fillDemoCreds = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setIsRegistering(false);
  };

  const handleLogout = () => {
    removeAuthToken();
    removeStoredUser();
    setCurrentUser(null);
    setActiveTab('dashboard');
    showFlash('success', 'Logged out successfully.');
  };

  // Student Actions
  const handleEnroll = async (courseId: number) => {
    try {
      await api.enrollCourse(courseId);
      showFlash('success', 'Successfully enrolled in course!');
      loadInitialData();
    } catch (err: any) {
      showFlash('error', err.message);
    }
  };

  const handleAssignmentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAssignment) return;
    try {
      await api.submitAssignment(selectedAssignment.id, {
        content: submissionContent,
        file_url: submissionFileUrl || undefined
      });
      showFlash('success', 'Assignment submitted successfully for instructor review.');
      setShowSubmitModal(false);
      setSubmissionContent('');
      setSubmissionFileUrl('');
      loadInitialData();
    } catch (err: any) {
      showFlash('error', err.message);
    }
  };

  // Teacher Actions
  const handleCreateCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createCourse({
        code: newCourseCode,
        title: newCourseTitle,
        description: newCourseDesc,
        syllabus: newCourseSyllabus
      });
      showFlash('success', `Course ${newCourseCode} created.`);
      setShowCourseModal(false);
      setNewCourseCode('');
      setNewCourseTitle('');
      setNewCourseDesc('');
      setNewCourseSyllabus('');
      loadInitialData();
    } catch (err: any) {
      showFlash('error', err.message);
    }
  };

  const handleAddMaterial = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!materialCourseId) return;
    try {
      await api.addStudyMaterial(materialCourseId, {
        title: newMaterialTitle,
        content: newMaterialContent,
        material_type: 'NOTES'
      });
      showFlash('success', 'Study material uploaded and vector-indexed with pgvector!');
      setShowMaterialModal(false);
      setNewMaterialTitle('');
      setNewMaterialContent('');
      loadInitialData();
    } catch (err: any) {
      showFlash('error', err.message);
    }
  };

  const handleCreateAssignment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignmentCourseId) return;
    try {
      await api.createAssignment({
        course_id: assignmentCourseId,
        title: newAssignmentTitle,
        description: newAssignmentDesc,
        max_score: Number(newAssignmentScore)
      });
      showFlash('success', `Assignment '${newAssignmentTitle}' created.`);
      setShowAssignmentModal(false);
      setNewAssignmentTitle('');
      setNewAssignmentDesc('');
      loadInitialData();
    } catch (err: any) {
      showFlash('error', err.message);
    }
  };

  const handleOpenSubmissions = async (assignment: any) => {
    try {
      setSelectedAssignment(assignment);
      const subs = await api.getAssignmentSubmissions(assignment.id);
      setAssignmentSubmissions(subs);
    } catch (err: any) {
      showFlash('error', err.message);
    }
  };

  const handleGradeSubmission = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeSubmission) return;
    try {
      await api.gradeSubmission(activeSubmission.id, {
        score: Number(gradeScore),
        feedback: gradeFeedback
      });
      showFlash('success', 'Submission evaluated! Student grade automatically recalculated via PostgreSQL stored procedure.');
      setShowGradingModal(false);
      if (selectedAssignment) {
        handleOpenSubmissions(selectedAssignment);
      }
      loadInitialData();
    } catch (err: any) {
      showFlash('error', err.message);
    }
  };

  const handleViewLeaderboard = async (courseId: number, courseTitle: string) => {
    try {
      const data = await api.getCourseLeaderboard(courseId);
      setLeaderboardData(data);
      setSelectedCourseLeaderboardTitle(courseTitle);
      setShowLeaderboardModal(true);
    } catch (err: any) {
      showFlash('error', err.message);
    }
  };

  const handleAISearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setAiSearching(true);
    setAiResult(null);
    try {
      const res = await api.searchNotes({
        query: searchQuery,
        course_id: searchCourseId,
        top_k: 3
      });
      setAiResult(res);
    } catch (err: any) {
      showFlash('error', err.message);
    } finally {
      setAiSearching(false);
    }
  };

  const handleMarkNotification = async (id: string) => {
    try {
      await api.markNotificationRead(id);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
      setNotificationCount(prev => Math.max(0, prev - 1));
    } catch (err: any) {
      console.error(err);
    }
  };

  // If not logged in, render university login portal
  if (!currentUser) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#f8fafc', padding: '20px' }}>
        <div style={{ width: '100%', maxWidth: '420px', backgroundColor: 'white', borderRadius: '4px', border: '1px solid #cbd5e1', boxShadow: '0 1px 3px rgba(0,0,0,0.08)', overflow: 'hidden' }}>
          <div style={{ backgroundColor: '#1e3a8a', padding: '20px 24px', color: 'white', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: '38px', height: '38px', backgroundColor: 'rgba(255,255,255,0.15)', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <GraduationCap size={22} color="white" />
            </div>
            <div>
              <h2 style={{ fontSize: '16px', fontWeight: '700', color: 'white' }}>Metropolitan University</h2>
              <p style={{ fontSize: '12px', opacity: 0.85 }}>Learning Management & Academic Gateway</p>
            </div>
          </div>

          <div style={{ padding: '24px' }}>
            {flashMessage && (
              <div className={`banner-alert banner-alert-${flashMessage.type}`}>
                {flashMessage.text}
              </div>
            )}

            {authError && (
              <div className="banner-alert banner-alert-error" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertCircle size={16} style={{ flexShrink: 0 }} />
                <span>{authError}</span>
              </div>
            )}

            <div style={{ display: 'flex', borderBottom: '1px solid #e2e8f0', marginBottom: '18px' }}>
              <button
                type="button"
                onClick={() => { setIsRegistering(false); setAuthError(''); }}
                style={{
                  flex: 1, padding: '8px', background: 'none', border: 'none',
                  borderBottom: !isRegistering ? '2px solid #1e3a8a' : '2px solid transparent',
                  fontWeight: !isRegistering ? '600' : '500', color: !isRegistering ? '#1e3a8a' : '#64748b',
                  fontSize: '13px', cursor: 'pointer'
                }}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => { setIsRegistering(true); setAuthError(''); }}
                style={{
                  flex: 1, padding: '8px', background: 'none', border: 'none',
                  borderBottom: isRegistering ? '2px solid #1e3a8a' : '2px solid transparent',
                  fontWeight: isRegistering ? '600' : '500', color: isRegistering ? '#1e3a8a' : '#64748b',
                  fontSize: '13px', cursor: 'pointer'
                }}
              >
                Register
              </button>
            </div>

            <form onSubmit={handleAuthSubmit}>
              {isRegistering && (
                <>
                  <div className="form-group">
                    <label className="form-label">Full Name</label>
                    <input
                      className="form-input"
                      type="text"
                      placeholder="e.g. Eleanor Vance"
                      value={fullName}
                      onChange={e => setFullName(e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Institutional Role</label>
                    <select
                      className="form-select"
                      value={role}
                      onChange={e => setRole(e.target.value)}
                    >
                      <option value="STUDENT">Student</option>
                      <option value="TEACHER">Faculty / Instructor</option>
                      <option value="ADMIN">Administrator</option>
                    </select>
                  </div>
                </>
              )}

              <div className="form-group">
                <label className="form-label">Institutional Email</label>
                <input
                  className="form-input"
                  type="email"
                  placeholder="name@univ.edu"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Password</label>
                <input
                  className="form-input"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: '100%', marginTop: '6px' }}
                disabled={authLoading}
              >
                {authLoading ? 'Authenticating...' : (isRegistering ? 'Create Academic Account' : 'Sign In')}
              </button>
            </form>

            <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid #e2e8f0' }}>
              <p style={{ fontSize: '11.5px', fontWeight: '600', color: '#475569', marginBottom: '8px' }}>
                Instant Demo Credentials:
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                <button
                  type="button"
                  onClick={() => fillDemoCreds('alex@student.univ.edu', 'Password123!')}
                  className="btn btn-secondary btn-sm"
                  style={{ justifyContent: 'flex-start' }}
                >
                  <span className="badge badge-info" style={{ marginRight: '6px' }}>Student</span>
                  alex@student.univ.edu (Alex Rivera)
                </button>
                <button
                  type="button"
                  onClick={() => fillDemoCreds('prof.alan@univ.edu', 'Password123!')}
                  className="btn btn-secondary btn-sm"
                  style={{ justifyContent: 'flex-start' }}
                >
                  <span className="badge badge-warning" style={{ marginRight: '6px' }}>Teacher</span>
                  prof.alan@univ.edu (Prof. Alan Turing)
                </button>
                <button
                  type="button"
                  onClick={() => fillDemoCreds('admin@univ.edu', 'AdminPass123!')}
                  className="btn btn-secondary btn-sm"
                  style={{ justifyContent: 'flex-start' }}
                >
                  <span className="badge badge-danger" style={{ marginRight: '6px' }}>Admin</span>
                  admin@univ.edu (Dean Victoria Vance)
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Count pending submissions for faculty
  const pendingSubmissionsCount = assignments.filter(a => !a.has_submitted).length;

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="university-crest">
            <GraduationCap size={18} />
          </div>
          <div className="university-info">
            <h1>Metropolitan Univ</h1>
            <p>{currentUser.role === 'STUDENT' ? 'Student Workspace' : currentUser.role === 'TEACHER' ? 'Faculty Portal' : 'Admin Console'}</p>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section-title">Core Academic</div>
          <button
            className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            <BarChart2 size={16} />
            <span>Dashboard</span>
          </button>

          <button
            className={`nav-item ${activeTab === 'courses' ? 'active' : ''}`}
            onClick={() => setActiveTab('courses')}
          >
            <BookOpen size={16} />
            <span>Courses</span>
          </button>

          <button
            className={`nav-item ${activeTab === 'assignments' ? 'active' : ''}`}
            onClick={() => setActiveTab('assignments')}
          >
            <FileText size={16} />
            <span>Assignments</span>
            {currentUser.role === 'STUDENT' && pendingSubmissionsCount > 0 && (
              <span className="nav-badge">{pendingSubmissionsCount}</span>
            )}
          </button>

          <button
            className={`nav-item ${activeTab === 'results' ? 'active' : ''}`}
            onClick={() => setActiveTab('results')}
          >
            <Award size={16} />
            <span>Results & Views</span>
          </button>

          <div className="nav-section-title">Academic Tools</div>
          <button
            className={`nav-item ${activeTab === 'ai-search' ? 'active' : ''}`}
            onClick={() => setActiveTab('ai-search')}
          >
            <Search size={16} />
            <span>AI Notes Search</span>
          </button>

          <button
            className={`nav-item ${activeTab === 'notifications' ? 'active' : ''}`}
            onClick={() => setActiveTab('notifications')}
          >
            <Bell size={16} />
            <span>Notifications</span>
            {notificationCount > 0 && <span className="nav-badge">{notificationCount}</span>}
          </button>

          {currentUser.role === 'ADMIN' && (
            <>
              <div className="nav-section-title">Platform Governance</div>
              <button
                className={`nav-item ${activeTab === 'admin' ? 'active' : ''}`}
                onClick={() => setActiveTab('admin')}
              >
                <Server size={16} />
                <span>System Health</span>
              </button>
            </>
          )}
        </nav>

        <div className="sidebar-footer">
          <div className="user-profile-badge">
            <div className="user-avatar">
              {currentUser.full_name ? currentUser.full_name[0] : 'U'}
            </div>
            <div className="user-details">
              <div className="user-name">{currentUser.full_name}</div>
              <div className="user-role-tag">{currentUser.role}</div>
            </div>
            <button
              onClick={handleLogout}
              title="Sign Out"
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}
            >
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="main-wrapper">
        <header className="topbar">
          <div className="topbar-title">
            {activeTab === 'dashboard' && 'Dashboard Overview'}
            {activeTab === 'courses' && 'Course Curriculum & Materials'}
            {activeTab === 'assignments' && 'Assignments & Assessment'}
            {activeTab === 'results' && 'Academic Performance & Relational Views'}
            {activeTab === 'ai-search' && 'AI Smart Notes Search (pgvector + Gemini)'}
            {activeTab === 'notifications' && 'Institutional Alerts & Notices'}
            {activeTab === 'admin' && 'System Health & User Directory'}
          </div>
          <div className="topbar-actions" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="badge badge-info" style={{ fontSize: '11.5px', padding: '3px 8px' }}>
              Academic Session 2026–2027
            </span>
            <span className="badge badge-neutral" style={{ fontSize: '11.5px', padding: '3px 8px' }}>
              {currentUser.role} • {currentUser.email}
            </span>
          </div>
        </header>

        <main className="content-viewport">
          {flashMessage && (
            <div className={`banner-alert banner-alert-${flashMessage.type}`}>
              {flashMessage.text}
            </div>
          )}

          {/* ========================================================
              TAB 1: ROLE-SPECIFIC DASHBOARDS
             ======================================================== */}
          {activeTab === 'dashboard' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

              {/* 1A. STUDENT DASHBOARD (LEARNING-FOCUSED) */}
              {currentUser.role === 'STUDENT' && (
                <>
                  <div className="role-banner">
                    <div>
                      <div className="role-banner-title">Welcome back, {currentUser.full_name}</div>
                      <div className="role-banner-subtitle">
                        Academic Term: Fall 2026 • Enrolled in {courses.filter(c => c.is_enrolled).length} modules
                      </div>
                    </div>
                    <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('courses')}>
                      Browse Course Catalog
                    </button>
                  </div>

                  <div className="grid-cols-3">
                    <div className="card stat-card">
                      <span className="stat-label">Active Enrollments</span>
                      <span className="stat-value">{courses.filter(c => c.is_enrolled).length}</span>
                      <span className="stat-subtext">Registered academic courses</span>
                    </div>
                    <div className="card stat-card">
                      <span className="stat-label">Assignments Due</span>
                      <span className="stat-value">{assignments.filter(a => !a.has_submitted).length}</span>
                      <span className="stat-subtext">Pending student submissions</span>
                    </div>
                    <div className="card stat-card">
                      <span className="stat-label">Standing (View)</span>
                      <span className="stat-value" style={{ color: '#15803d' }}>
                        {progressView.length > 0 && progressView[0].published_grade ? progressView[0].published_grade : 'In Good Standing'}
                      </span>
                      <span className="stat-subtext">PostgreSQL student_progress_view</span>
                    </div>
                  </div>

                  {/* My Courses Section */}
                  <div className="card">
                    <div className="card-header">
                      <h3 className="card-title">My Courses & Materials</h3>
                      <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('courses')}>
                        View All
                      </button>
                    </div>
                    {courses.filter(c => c.is_enrolled).length === 0 ? (
                      <div className="empty-state">
                        <div className="empty-state-icon">
                          <BookOpen size={20} />
                        </div>
                        <div className="empty-state-title">No Enrolled Courses</div>
                        <div className="empty-state-desc">
                          You are not registered in any courses yet. Explore the curriculum catalog to enroll and access course materials.
                        </div>
                        <button className="btn btn-primary btn-sm" style={{ marginTop: '12px' }} onClick={() => setActiveTab('courses')}>
                          Browse Catalog
                        </button>
                      </div>
                    ) : (
                      <div className="grid-cols-2">
                        {courses.filter(c => c.is_enrolled).map(c => (
                          <div key={c.id} style={{ border: '1px solid #e2e8f0', padding: '14px', borderRadius: '4px', backgroundColor: '#fafbfc' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                              <span className="badge badge-info">{c.code}</span>
                              <span style={{ fontSize: '12px', color: '#64748b' }}>Instructor: {c.teacher_name}</span>
                            </div>
                            <h4 style={{ fontSize: '14.5px', marginBottom: '6px' }}>{c.title}</h4>
                            <p style={{ fontSize: '12.5px', color: '#475569', marginBottom: '12px' }}>{c.description}</p>
                            <div style={{ display: 'flex', gap: '8px' }}>
                              <button
                                className="btn btn-secondary btn-sm"
                                onClick={async () => {
                                  const det = await api.getCourseDetail(c.id);
                                  setSelectedCourse(det);
                                  setActiveTab('courses');
                                }}
                              >
                                Lecture Notes
                              </button>
                              <button
                                className="btn btn-secondary btn-sm"
                                onClick={() => {
                                  setSearchCourseId(c.id);
                                  setActiveTab('ai-search');
                                }}
                              >
                                Ask AI
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Upcoming Assignments */}
                  <div className="card">
                    <div className="card-header">
                      <h3 className="card-title">Pending Course Work</h3>
                      <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('assignments')}>
                        View Assignments
                      </button>
                    </div>
                    <div className="table-container">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Course</th>
                            <th>Assignment</th>
                            <th>Max Marks</th>
                            <th>Status</th>
                            <th>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {assignments.length === 0 ? (
                            <tr>
                              <td colSpan={5} style={{ textAlign: 'center', padding: '24px', color: '#64748b' }}>
                                No assignments found for your current enrollments.
                              </td>
                            </tr>
                          ) : (
                            assignments.slice(0, 4).map(a => (
                              <tr key={a.id}>
                                <td><strong>{a.course_code}</strong></td>
                                <td>{a.title}</td>
                                <td>{a.max_score} pts</td>
                                <td>
                                  <span className={`badge ${a.has_submitted ? (a.submission_status === 'GRADED' ? 'badge-success' : 'badge-warning') : 'badge-neutral'}`}>
                                    {a.has_submitted ? `${a.submission_status}` : 'Not Submitted'}
                                  </span>
                                </td>
                                <td>
                                  {!a.has_submitted ? (
                                    <button
                                      className="btn btn-primary btn-sm"
                                      onClick={() => {
                                        setSelectedAssignment(a);
                                        setShowSubmitModal(true);
                                      }}
                                    >
                                      Submit
                                    </button>
                                  ) : (
                                    <span style={{ fontSize: '12px', color: '#64748b' }}>
                                      {a.submission_score !== null ? `${a.submission_score} / ${a.max_score}` : 'Under Review'}
                                    </span>
                                  )}
                                </td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              )}

              {/* 1B. TEACHER DASHBOARD (COURSE & ASSESSMENT-FOCUSED) */}
              {currentUser.role === 'TEACHER' && (
                <>
                  <div className="role-banner">
                    <div>
                      <div className="role-banner-title">Faculty Portal: {currentUser.full_name}</div>
                      <div className="role-banner-subtitle">
                        Department of Computer Science & Academic Assessment
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button className="btn btn-primary btn-sm" onClick={() => setShowCourseModal(true)}>
                        <PlusCircle size={14} /> New Course
                      </button>
                    </div>
                  </div>

                  <div className="grid-cols-4">
                    <div className="card stat-card">
                      <span className="stat-label">Active Modules</span>
                      <span className="stat-value">{courses.length}</span>
                      <span className="stat-subtext">Curriculum courses</span>
                    </div>
                    <div className="card stat-card">
                      <span className="stat-label">Total Assignments</span>
                      <span className="stat-value">{assignments.length}</span>
                      <span className="stat-subtext">Active evaluations</span>
                    </div>
                    <div className="card stat-card">
                      <span className="stat-label">Submissions To Grade</span>
                      <span className="stat-value" style={{ color: '#b45309' }}>1</span>
                      <span className="stat-subtext">Submissions awaiting review</span>
                    </div>
                    <div className="card stat-card">
                      <span className="stat-label">Vector Knowledge Chunks</span>
                      <span className="stat-value">10</span>
                      <span className="stat-subtext">Indexed in pgvector</span>
                    </div>
                  </div>

                  {/* Submissions Needing Review */}
                  <div className="card" style={{ borderLeft: '3px solid #b45309' }}>
                    <div className="card-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Clock size={16} color="#b45309" />
                        <h3 className="card-title">Assessment Action Queue: Submissions Awaiting Grading</h3>
                      </div>
                      <span className="badge badge-warning">Action Required</span>
                    </div>
                    <div className="table-container">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Student</th>
                            <th>Course & Assignment</th>
                            <th>Submission Text</th>
                            <th>Submitted</th>
                            <th>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr>
                            <td>
                              <strong>Marcus Vance</strong>
                              <div style={{ fontSize: '11px', color: '#64748b' }}>marcus@student.univ.edu</div>
                            </td>
                            <td>CS501: Index Performance Analysis</td>
                            <td style={{ maxWidth: '300px', fontSize: '12px' }}>
                              "Submitting my benchmark graphs and explain analyze output for grading."
                            </td>
                            <td>Today</td>
                            <td>
                              <button
                                className="btn btn-primary btn-sm"
                                onClick={() => {
                                  setActiveSubmission({
                                    id: 3,
                                    student_name: 'Marcus Vance',
                                    max_score: 100,
                                    content: 'Submitting my benchmark graphs and explain analyze output for grading.'
                                  });
                                  setGradeScore(85);
                                  setGradeFeedback('Good benchmark comparisons.');
                                  setShowGradingModal(true);
                                }}
                              >
                                Evaluate & Mark
                              </button>
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Course Summary View (SQL View) */}
                  <div className="card">
                    <div className="card-header">
                      <h3 className="card-title">Course Analytics (PostgreSQL View: course_result_summary_view)</h3>
                      <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('results')}>
                        Full Analysis
                      </button>
                    </div>
                    <div className="table-container">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Course</th>
                            <th>Enrolled</th>
                            <th>Graded</th>
                            <th>Class Average</th>
                            <th>Max</th>
                            <th>Min</th>
                            <th>Leaderboard</th>
                          </tr>
                        </thead>
                        <tbody>
                          {courseSummaryView.map((c, idx) => (
                            <tr key={idx}>
                              <td><strong>{c.course_code}</strong> - {c.course_title}</td>
                              <td>{c.enrolled_students}</td>
                              <td>{c.total_submissions_graded}</td>
                              <td><strong>{c.average_assignment_score}</strong> / 100</td>
                              <td style={{ color: '#15803d', fontWeight: '600' }}>{c.max_assignment_score}</td>
                              <td style={{ color: '#b91c1c' }}>{c.min_assignment_score}</td>
                              <td>
                                <button
                                  className="btn btn-secondary btn-sm"
                                  onClick={() => handleViewLeaderboard(c.course_id, c.course_title)}
                                >
                                  Window Ranks
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              )}

              {/* 1C. ADMIN DASHBOARD (MANAGEMENT-FOCUSED) */}
              {currentUser.role === 'ADMIN' && (
                <>
                  <div className="role-banner">
                    <div>
                      <div className="role-banner-title">Administrator Console: {currentUser.full_name}</div>
                      <div className="role-banner-subtitle">
                        Academic Platform Administration, Role Access & Infrastructure Governance
                      </div>
                    </div>
                    <button className="btn btn-secondary btn-sm" onClick={loadInitialData}>
                      <RefreshCw size={13} /> Refresh Health
                    </button>
                  </div>

                  {/* Polyglot Health Cards */}
                  <div className="grid-cols-4">
                    <div className="card stat-card" style={{ borderLeft: '3px solid #1e3a8a' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Database size={16} color="#1e3a8a" />
                        <span className="stat-label">PostgreSQL 18</span>
                      </div>
                      <span className="stat-value" style={{ fontSize: '18px', color: '#15803d' }}>ONLINE</span>
                      <span className="stat-subtext">9 Relational Tables, Views & Triggers</span>
                    </div>

                    <div className="card stat-card" style={{ borderLeft: '3px solid #059669' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Activity size={16} color="#059669" />
                        <span className="stat-label">pgvector 0.8.6</span>
                      </div>
                      <span className="stat-value" style={{ fontSize: '18px', color: '#15803d' }}>HNSW ACTIVE</span>
                      <span className="stat-subtext">768-d Vector Cosine Distance</span>
                    </div>

                    <div className="card stat-card" style={{ borderLeft: '3px solid #0284c7' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Server size={16} color="#0284c7" />
                        <span className="stat-label">MongoDB 7.0</span>
                      </div>
                      <span className="stat-value" style={{ fontSize: '18px', color: '#15803d' }}>CONNECTED</span>
                      <span className="stat-subtext">Notifications & Activity Logs</span>
                    </div>

                    <div className="card stat-card" style={{ borderLeft: '3px solid #b45309' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Activity size={16} color="#b45309" />
                        <span className="stat-label">Redis 7.2</span>
                      </div>
                      <span className="stat-value" style={{ fontSize: '18px', color: '#15803d' }}>PUB/SUB READY</span>
                      <span className="stat-subtext">Event Bus & Real-Time Alerts</span>
                    </div>
                  </div>

                  {/* Registered Users Summary */}
                  <div className="card">
                    <div className="card-header">
                      <h3 className="card-title">Institutional User Directory ({allUsers.length})</h3>
                      <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('admin')}>
                        Manage Users
                      </button>
                    </div>
                    <div className="table-container">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>User</th>
                            <th>Email</th>
                            <th>Role Scope</th>
                            <th>Status</th>
                            <th>Registered</th>
                          </tr>
                        </thead>
                        <tbody>
                          {allUsers.slice(0, 5).map(u => (
                            <tr key={u.id}>
                              <td><strong>{u.full_name}</strong></td>
                              <td>{u.email}</td>
                              <td>
                                <span className={`badge ${u.role === 'ADMIN' ? 'badge-danger' : u.role === 'TEACHER' ? 'badge-warning' : 'badge-info'}`}>
                                  {u.role}
                                </span>
                              </td>
                              <td><span className="badge badge-success">ACTIVE</span></td>
                              <td>{new Date(u.created_at).toLocaleDateString()}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* ========================================================
              TAB 2: COURSES
             ======================================================== */}
          {activeTab === 'courses' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2 style={{ fontSize: '17px' }}>Course Curriculum & Study Notes</h2>
                {currentUser.role !== 'STUDENT' && (
                  <button className="btn btn-primary btn-sm" onClick={() => setShowCourseModal(true)}>
                    <PlusCircle size={14} /> Create Course
                  </button>
                )}
              </div>

              {courses.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-state-icon">
                    <BookOpen size={20} />
                  </div>
                  <div className="empty-state-title">No Academic Courses Available</div>
                  <div className="empty-state-desc">
                    There are currently no courses registered in the curriculum database.
                  </div>
                </div>
              ) : (
                <div className="grid-cols-2">
                  {courses.map(course => (
                  <div key={course.id} className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span className="badge badge-info">{course.code}</span>
                        {course.is_enrolled && <span className="badge badge-success"><CheckCircle2 size={11} /> Enrolled</span>}
                      </div>
                      <h3 style={{ fontSize: '15.5px', marginBottom: '6px' }}>{course.title}</h3>
                      <p style={{ fontSize: '12.5px', color: '#475569', marginBottom: '12px' }}>{course.description}</p>
                      <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '14px' }}>
                        Instructor: <strong>{course.teacher_name}</strong> • Students: {course.enrolled_count}
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '8px', borderTop: '1px solid #e2e8f0', paddingTop: '12px', flexWrap: 'wrap' }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={async () => {
                          const det = await api.getCourseDetail(course.id);
                          setSelectedCourse(det);
                        }}
                      >
                        Notes & Syllabus
                      </button>

                      {currentUser.role === 'STUDENT' && !course.is_enrolled && (
                        <button className="btn btn-primary btn-sm" onClick={() => handleEnroll(course.id)}>
                          Enroll
                        </button>
                      )}

                      {currentUser.role !== 'STUDENT' && (
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => {
                            setMaterialCourseId(course.id);
                            setShowMaterialModal(true);
                          }}
                        >
                          + Upload Notes
                        </button>
                      )}

                      <button className="btn btn-secondary btn-sm" onClick={() => handleViewLeaderboard(course.id, course.title)}>
                        <Award size={13} /> Ranks
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              )}

              {selectedCourse && (
                <div className="card">
                  <div className="card-header">
                    <h3 className="card-title">{selectedCourse.code}: {selectedCourse.title}</h3>
                    <button className="btn btn-secondary btn-sm" onClick={() => setSelectedCourse(null)}>Close</button>
                  </div>
                  <div style={{ fontSize: '13px', marginBottom: '14px', whiteSpace: 'pre-line' }}>
                    <strong>Syllabus Outline:</strong><br />
                    {selectedCourse.syllabus}
                  </div>

                  <h4 style={{ fontSize: '13.5px', marginBottom: '10px' }}>Lecture Materials (Vector-Indexed with pgvector)</h4>
                  {selectedCourse.materials && selectedCourse.materials.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {selectedCourse.materials.map((m: any) => (
                        <div key={m.id} style={{ border: '1px solid #e2e8f0', padding: '12px', borderRadius: '4px', backgroundColor: '#fafbfc' }}>
                          <div style={{ fontWeight: '600', fontSize: '13px', marginBottom: '4px' }}>{m.title}</div>
                          <div style={{ fontSize: '12.5px', color: '#334155' }}>{m.content}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-state">No lecture notes uploaded yet for this course.</div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ========================================================
              TAB 3: ASSIGNMENTS
             ======================================================== */}
          {activeTab === 'assignments' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2 style={{ fontSize: '17px' }}>Course Assignments & Submissions</h2>
                {currentUser.role !== 'STUDENT' && (
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => {
                      if (courses.length > 0) setAssignmentCourseId(courses[0].id);
                      setShowAssignmentModal(true);
                    }}
                  >
                    <PlusCircle size={14} /> New Assignment
                  </button>
                )}
              </div>

              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Course</th>
                      <th>Assignment Title</th>
                      <th>Description</th>
                      <th>Max Marks</th>
                      <th>Status / Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {assignments.length === 0 ? (
                      <tr>
                        <td colSpan={5} style={{ textAlign: 'center', padding: '32px' }}>
                          <div className="empty-state" style={{ border: 'none', padding: '12px' }}>
                            <div className="empty-state-icon">
                              <FileText size={20} />
                            </div>
                            <div className="empty-state-title">No Assignments Available</div>
                            <div className="empty-state-desc">
                              There are currently no active assignments or assessments in the platform.
                            </div>
                          </div>
                        </td>
                      </tr>
                    ) : (
                      assignments.map(a => (
                        <tr key={a.id}>
                          <td><strong>{a.course_code}</strong></td>
                          <td>{a.title}</td>
                          <td style={{ maxWidth: '300px' }}>{a.description}</td>
                          <td>{a.max_score} pts</td>
                          <td>
                            {currentUser.role === 'STUDENT' ? (
                              a.has_submitted ? (
                                <span className={`badge ${a.submission_status === 'GRADED' ? 'badge-success' : 'badge-warning'}`}>
                                  {a.submission_status}: {a.submission_score !== null ? `${a.submission_score}/${a.max_score}` : 'Pending'}
                                </span>
                              ) : (
                                <button
                                  className="btn btn-primary btn-sm"
                                  onClick={() => {
                                    setSelectedAssignment(a);
                                    setShowSubmitModal(true);
                                  }}
                                >
                                  Submit Work
                                </button>
                              )
                            ) : (
                              <button className="btn btn-secondary btn-sm" onClick={() => handleOpenSubmissions(a)}>
                                View Submissions
                              </button>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {selectedAssignment && currentUser.role !== 'STUDENT' && (
                <div className="card">
                  <div className="card-header">
                    <h3 className="card-title">Submissions: {selectedAssignment.title}</h3>
                    <button className="btn btn-secondary btn-sm" onClick={() => setSelectedAssignment(null)}>Close</button>
                  </div>
                  <div className="table-container">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Student</th>
                          <th>Submission Content</th>
                          <th>Submitted</th>
                          <th>Status</th>
                          <th>Score</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {assignmentSubmissions.length === 0 ? (
                          <tr><td colSpan={6} style={{ textAlign: 'center' }}>No submissions received yet.</td></tr>
                        ) : (
                          assignmentSubmissions.map(sub => (
                            <tr key={sub.id}>
                              <td>
                                <strong>{sub.student_name}</strong>
                                <div style={{ fontSize: '11px', color: '#64748b' }}>{sub.student_email}</div>
                              </td>
                              <td style={{ maxWidth: '350px', fontSize: '12px' }}>{sub.content}</td>
                              <td>{new Date(sub.submitted_at).toLocaleDateString()}</td>
                              <td>
                                <span className={`badge ${sub.status === 'GRADED' ? 'badge-success' : 'badge-warning'}`}>
                                  {sub.status}
                                </span>
                              </td>
                              <td>
                                <strong>{sub.score !== null ? `${sub.score}/${sub.max_score}` : '—'}</strong>
                              </td>
                              <td>
                                <button
                                  className="btn btn-primary btn-sm"
                                  onClick={() => {
                                    setActiveSubmission(sub);
                                    setGradeScore(sub.score || sub.max_score);
                                    setGradeFeedback(sub.feedback || '');
                                    setShowGradingModal(true);
                                  }}
                                >
                                  {sub.status === 'GRADED' ? 'Re-grade' : 'Grade'}
                                </button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ========================================================
              TAB 4: RESULTS & VIEWS
             ======================================================== */}
          {activeTab === 'results' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <h2 style={{ fontSize: '17px' }}>Official Academic Results & Database Views</h2>

              {currentUser.role === 'STUDENT' ? (
                <div className="card">
                  <div className="card-header">
                    <h3 className="card-title">Student Performance Record (View: student_progress_view)</h3>
                  </div>
                  <div className="table-container">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Course Code</th>
                          <th>Course Title</th>
                          <th>Assignments Completed</th>
                          <th>Total Points</th>
                          <th>Published Grade</th>
                          <th>Class Standings</th>
                        </tr>
                      </thead>
                      <tbody>
                        {progressView.length === 0 ? (
                          <tr>
                            <td colSpan={6} style={{ textAlign: 'center', padding: '32px' }}>
                              <div className="empty-state" style={{ border: 'none', padding: '12px' }}>
                                <div className="empty-state-icon">
                                  <Award size={20} />
                                </div>
                                <div className="empty-state-title">No Grades Published Yet</div>
                                <div className="empty-state-desc">
                                  As your submitted assignments are evaluated by faculty, your academic standing computed by PostgreSQL student_progress_view will appear here.
                                </div>
                              </div>
                            </td>
                          </tr>
                        ) : (
                          progressView.map((p, idx) => (
                            <tr key={idx}>
                              <td><strong>{p.course_code}</strong></td>
                              <td>{p.course_title}</td>
                              <td>{p.submitted_assignments} / {p.total_assignments} ({p.completion_rate}%)</td>
                              <td>{p.total_obtained_score} / {p.total_possible_score}</td>
                              <td>
                                <span className={`badge ${p.published_grade === 'A+' || p.published_grade === 'A' ? 'badge-success' : 'badge-info'}`}>
                                  {p.published_grade || 'In Progress'}
                                </span>
                              </td>
                              <td>
                                <button
                                  className="btn btn-secondary btn-sm"
                                  onClick={() => handleViewLeaderboard(p.course_id, p.course_title)}
                                >
                                  View Ranks
                                </button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="card">
                  <div className="card-header">
                    <h3 className="card-title">Course Result Summary (View: course_result_summary_view)</h3>
                  </div>
                  <div className="table-container">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Course Code</th>
                          <th>Course Title</th>
                          <th>Enrolled</th>
                          <th>Graded Subs</th>
                          <th>Average Score</th>
                          <th>Highest</th>
                          <th>Lowest</th>
                          <th>Rankings</th>
                        </tr>
                      </thead>
                      <tbody>
                        {courseSummaryView.length === 0 ? (
                          <tr>
                            <td colSpan={8} style={{ textAlign: 'center', padding: '32px' }}>
                              <div className="empty-state" style={{ border: 'none', padding: '12px' }}>
                                <div className="empty-state-icon">
                                  <Award size={20} />
                                </div>
                                <div className="empty-state-title">No Course Summaries Available</div>
                                <div className="empty-state-desc">
                                  Course summary analytics from course_result_summary_view will populate once student enrollments and scores are processed.
                                </div>
                              </div>
                            </td>
                          </tr>
                        ) : (
                          courseSummaryView.map((c, idx) => (
                            <tr key={idx}>
                              <td><strong>{c.course_code}</strong></td>
                              <td>{c.course_title}</td>
                              <td>{c.enrolled_students}</td>
                              <td>{c.total_submissions_graded}</td>
                              <td><strong>{c.average_assignment_score}</strong> / 100</td>
                              <td style={{ color: '#15803d', fontWeight: '600' }}>{c.max_assignment_score}</td>
                              <td style={{ color: '#b91c1c' }}>{c.min_assignment_score}</td>
                              <td>
                                <button
                                  className="btn btn-secondary btn-sm"
                                  onClick={() => handleViewLeaderboard(c.course_id, c.course_title)}
                                >
                                  Window Ranks
                                </button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ========================================================
              TAB 5: AI SMART NOTES SEARCH
             ======================================================== */}
          {activeTab === 'ai-search' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div>
                <h2 style={{ fontSize: '17px', marginBottom: '4px' }}>AI Smart Notes Search</h2>
                <p style={{ fontSize: '12.5px', color: '#64748b' }}>
                  Semantic similarity retrieval via <strong>pgvector (HNSW cosine distance)</strong> and answer generation via <strong>Gemini RAG</strong>. Answers strictly from course notes.
                </p>
              </div>

              <div className="card">
                <form onSubmit={handleAISearch}>
                  <div style={{ display: 'flex', gap: '10px', marginBottom: '12px' }}>
                    <div style={{ flex: 1 }}>
                      <input
                        className="form-input"
                        style={{ width: '100%' }}
                        type="text"
                        placeholder="Ask a technical question from your lecture notes..."
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        required
                      />
                    </div>
                    <select
                      className="form-select"
                      style={{ width: '220px' }}
                      value={searchCourseId || ''}
                      onChange={e => setSearchCourseId(e.target.value ? Number(e.target.value) : undefined)}
                    >
                      <option value="">All Courses</option>
                      {courses.map(c => (
                        <option key={c.id} value={c.id}>{c.code} - {c.title}</option>
                      ))}
                    </select>
                    <button className="btn btn-primary" type="submit" disabled={aiSearching}>
                      {aiSearching ? (
                        <>
                          <span className="spinner" />
                          <span>Searching Notes...</span>
                        </>
                      ) : (
                        <>
                          <Search size={14} />
                          <span>Search Notes</span>
                        </>
                      )}
                    </button>
                  </div>
                </form>

                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
                  <span style={{ fontSize: '11.5px', color: '#64748b' }}>Sample Questions:</span>
                  {[
                    "How does PostgreSQL handle MVCC and vacuuming?",
                    "Explain Raft consensus leader election and voting terms",
                    "How does HNSW graph indexing work in vector databases?",
                    "What is the difference between 2PC and Saga patterns?"
                  ].map((preset, idx) => (
                    <button
                      key={idx}
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => setSearchQuery(preset)}
                    >
                      {preset}
                    </button>
                  ))}
                </div>
              </div>

              {!aiResult && !aiSearching && (
                <div className="card" style={{ backgroundColor: '#fafbfc', border: '1px dashed #cbd5e1' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
                    <div className="empty-state-icon" style={{ flexShrink: 0, margin: 0, backgroundColor: '#eff6ff', color: '#1e3a8a' }}>
                      <Search size={18} />
                    </div>
                    <div>
                      <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '4px' }}>Grounded RAG Lecture Assistant</h4>
                      <p style={{ fontSize: '12.5px', color: '#475569', lineHeight: '1.5' }}>
                        This semantic retrieval engine indexes lecture note chunks into PostgreSQL via <code>pgvector (HNSW cosine metric)</code>. When a query is submitted, relevant textbook & syllabus passages are retrieved and sent to Gemini to generate an answer grounded exclusively in verified course material.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {aiSearching && (
                <div className="card" style={{ textAlign: 'center', padding: '36px 20px' }}>
                  <span className="spinner spinner-primary" style={{ width: '24px', height: '24px', borderWidth: '3px', marginBottom: '12px' }} />
                  <div style={{ fontSize: '14px', fontWeight: '600', color: 'var(--color-accent)' }}>Querying pgvector & Generating Grounded Answer</div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-light)', marginTop: '4px' }}>
                    Calculating vector embeddings, searching HNSW index, and synthesizing answer with Gemini...
                  </div>
                </div>
              )}

              {aiResult && (
                <div className="card" style={{ borderLeft: aiResult.grounded ? '3px solid #15803d' : '3px solid #b45309' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span className={`badge ${aiResult.grounded ? 'badge-success' : 'badge-warning'}`}>
                        {aiResult.grounded ? 'Grounded in Course Material' : 'Ungrounded / Guardrailed'}
                      </span>
                      <span style={{ fontSize: '12px', color: '#64748b' }}>Model: {aiResult.model_used}</span>
                    </div>
                    <span style={{ fontSize: '12px', color: '#64748b' }}>Latency: {aiResult.latency_ms} ms</span>
                  </div>

                  <div style={{ fontSize: '13.5px', lineHeight: '1.6', marginBottom: '14px', whiteSpace: 'pre-line' }}>
                    {aiResult.answer}
                  </div>

                  {aiResult.sources && aiResult.sources.length > 0 && (
                    <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '12px' }}>
                      <h4 style={{ fontSize: '12.5px', color: '#475569', marginBottom: '8px' }}>
                        Retrieved Course Sources ({aiResult.sources.length} chunks via pgvector)
                      </h4>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {aiResult.sources.map((s: any, idx: number) => (
                          <div key={idx} style={{ backgroundColor: '#f8fafc', padding: '9px 12px', borderRadius: '4px', border: '1px solid #e2e8f0', fontSize: '12px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
                              <strong>{s.material_title} ({s.course_title})</strong>
                              <span className="badge badge-info">Similarity: {s.similarity_score}</span>
                            </div>
                            <div style={{ color: '#334155' }}>"{s.chunk_text}"</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ========================================================
              TAB 6: NOTIFICATIONS
             ======================================================== */}
          {activeTab === 'notifications' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <h2 style={{ fontSize: '17px' }}>Notifications & Real-Time Alerts (MongoDB + Redis)</h2>

              <div className="card">
                {notifications.length === 0 ? (
                  <div className="empty-state" style={{ border: 'none', padding: '32px' }}>
                    <div className="empty-state-icon">
                      <Bell size={20} />
                    </div>
                    <div className="empty-state-title">No New Notifications</div>
                    <div className="empty-state-desc">
                      Your institutional feed is up to date. Alerts from grading events, submission confirmations, and announcements will appear here.
                    </div>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {notifications.map(n => (
                      <div
                        key={n.id}
                        style={{
                          padding: '12px 14px',
                          borderRadius: '4px',
                          border: '1px solid #e2e8f0',
                          backgroundColor: n.is_read ? '#ffffff' : '#f0f9ff',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center'
                        }}
                      >
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '3px' }}>
                            <span className={`badge ${n.type === 'GRADE' ? 'badge-success' : n.type === 'SUBMISSION' ? 'badge-info' : 'badge-neutral'}`}>
                              {n.type}
                            </span>
                            <strong>{n.title}</strong>
                            {!n.is_read && <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#0284c7' }} />}
                          </div>
                          <div style={{ fontSize: '12.5px', color: '#475569' }}>{n.message}</div>
                          <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '3px' }}>
                            {new Date(n.created_at).toLocaleString()}
                          </div>
                        </div>

                        {!n.is_read && (
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => handleMarkNotification(n.id)}
                          >
                            Mark Read
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ========================================================
              TAB 7: ADMIN & HEALTH
             ======================================================== */}
          {activeTab === 'admin' && currentUser.role === 'ADMIN' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2 style={{ fontSize: '17px' }}>System Architecture & Polyglot Health</h2>
                <button className="btn btn-secondary btn-sm" onClick={loadInitialData}>
                  <RefreshCw size={13} /> Refresh Status
                </button>
              </div>

              {healthStatus && (
                <div className="grid-cols-4">
                  <div className="card stat-card" style={{ borderLeft: '3px solid #1e3a8a' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Database size={16} color="#1e3a8a" />
                      <strong style={{ fontSize: '13px' }}>PostgreSQL 18</strong>
                    </div>
                    <span className="badge badge-success">{healthStatus.components.postgresql?.status}</span>
                    <p style={{ fontSize: '11.5px', color: '#64748b', marginTop: '4px' }}>9 Relational Tables & Views</p>
                  </div>

                  <div className="card stat-card" style={{ borderLeft: '3px solid #059669' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Activity size={16} color="#059669" />
                      <strong style={{ fontSize: '13px' }}>pgvector 0.8.6</strong>
                    </div>
                    <span className="badge badge-success">{healthStatus.components.pgvector?.status}</span>
                    <p style={{ fontSize: '11.5px', color: '#64748b', marginTop: '4px' }}>768-d Vector Cosine Search</p>
                  </div>

                  <div className="card stat-card" style={{ borderLeft: '3px solid #0284c7' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Server size={16} color="#0284c7" />
                      <strong style={{ fontSize: '13px' }}>MongoDB 7.0</strong>
                    </div>
                    <span className="badge badge-success">{healthStatus.components.mongodb?.status}</span>
                    <p style={{ fontSize: '11.5px', color: '#64748b', marginTop: '4px' }}>Notifications & Activity Logs</p>
                  </div>

                  <div className="card stat-card" style={{ borderLeft: '3px solid #b45309' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Activity size={16} color="#b45309" />
                      <strong style={{ fontSize: '13px' }}>Redis 7.2</strong>
                    </div>
                    <span className="badge badge-success">{healthStatus.components.redis?.status}</span>
                    <p style={{ fontSize: '11.5px', color: '#64748b', marginTop: '4px' }}>Pub/Sub Event Broker</p>
                  </div>
                </div>
              )}

              {/* User Directory */}
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">Registered Academic Users ({allUsers.length})</h3>
                </div>
                <div className="table-container">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Full Name</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      {allUsers.map(u => (
                        <tr key={u.id}>
                          <td>{u.id}</td>
                          <td><strong>{u.full_name}</strong></td>
                          <td>{u.email}</td>
                          <td>
                            <span className={`badge ${u.role === 'ADMIN' ? 'badge-danger' : u.role === 'TEACHER' ? 'badge-warning' : 'badge-info'}`}>
                              {u.role}
                            </span>
                          </td>
                          <td><span className="badge badge-success">ACTIVE</span></td>
                          <td>{new Date(u.created_at).toLocaleDateString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Activity Trail */}
              {adminOverview?.recent_activities && (
                <div className="card">
                  <div className="card-header">
                    <h3 className="card-title">Platform Activity Audit Log (MongoDB)</h3>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {adminOverview.recent_activities.map((act: any) => (
                      <div key={act.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 10px', borderBottom: '1px solid #f1f5f9', fontSize: '12px' }}>
                        <div>
                          <strong>{act.user_name}</strong>: {act.action}
                          {act.details && <span style={{ color: '#64748b', marginLeft: '6px' }}>({act.details})</span>}
                        </div>
                        <span style={{ color: '#94a3b8' }}>{new Date(act.timestamp).toLocaleTimeString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* MODAL: CREATE COURSE */}
      {showCourseModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Create New Course</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowCourseModal(false)}>✕</button>
            </div>
            <form onSubmit={handleCreateCourse}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Course Code</label>
                  <input className="form-input" placeholder="e.g. CS505" value={newCourseCode} onChange={e => setNewCourseCode(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Course Title</label>
                  <input className="form-input" placeholder="e.g. Advanced Operating Systems" value={newCourseTitle} onChange={e => setNewCourseTitle(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Description</label>
                  <textarea className="form-textarea" placeholder="Course overview..." value={newCourseDesc} onChange={e => setNewCourseDesc(e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">Syllabus Outline</label>
                  <textarea className="form-textarea" placeholder="Units and modules..." value={newCourseSyllabus} onChange={e => setNewCourseSyllabus(e.target.value)} />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowCourseModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary btn-sm">Create Course</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: UPLOAD NOTES */}
      {showMaterialModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Upload & Vector-Index Lecture Notes</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowMaterialModal(false)}>✕</button>
            </div>
            <form onSubmit={handleAddMaterial}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Lecture / Note Title</label>
                  <input className="form-input" placeholder="e.g. Chapter 5: Write-Ahead Logging" value={newMaterialTitle} onChange={e => setNewMaterialTitle(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Note Content (Automatically Chunked & Embedded in pgvector)</label>
                  <textarea className="form-textarea" style={{ minHeight: '130px' }} placeholder="Enter lecture notes text..." value={newMaterialContent} onChange={e => setNewMaterialContent(e.target.value)} required />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowMaterialModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary btn-sm">Upload & Vectorize</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: CREATE ASSIGNMENT */}
      {showAssignmentModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Create Assignment</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowAssignmentModal(false)}>✕</button>
            </div>
            <form onSubmit={handleCreateAssignment}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Course</label>
                  <select
                    className="form-select"
                    value={assignmentCourseId || ''}
                    onChange={e => setAssignmentCourseId(Number(e.target.value))}
                    required
                  >
                    {courses.map(c => (
                      <option key={c.id} value={c.id}>{c.code} - {c.title}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Assignment Title</label>
                  <input className="form-input" placeholder="e.g. Assignment 2: Query Optimization" value={newAssignmentTitle} onChange={e => setNewAssignmentTitle(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Instructions & Prompt</label>
                  <textarea className="form-textarea" placeholder="Details for the students..." value={newAssignmentDesc} onChange={e => setNewAssignmentDesc(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Maximum Points</label>
                  <input className="form-input" type="number" min={1} max={500} value={newAssignmentScore} onChange={e => setNewAssignmentScore(Number(e.target.value))} required />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowAssignmentModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary btn-sm">Publish Assignment</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: SUBMIT ASSIGNMENT */}
      {showSubmitModal && selectedAssignment && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Submit: {selectedAssignment.title}</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowSubmitModal(false)}>✕</button>
            </div>
            <form onSubmit={handleAssignmentSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Submission Content / Write-up</label>
                  <textarea
                    className="form-textarea"
                    style={{ minHeight: '130px' }}
                    placeholder="Enter your answers or query analysis..."
                    value={submissionContent}
                    onChange={e => setSubmissionContent(e.target.value)}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Optional Project URL / Repository Link</label>
                  <input
                    className="form-input"
                    type="url"
                    placeholder="https://github.com/student/assignment"
                    value={submissionFileUrl}
                    onChange={e => setSubmissionFileUrl(e.target.value)}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowSubmitModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary btn-sm">Confirm Submission</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: GRADE SUBMISSION */}
      {showGradingModal && activeSubmission && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Evaluate: {activeSubmission.student_name}</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowGradingModal(false)}>✕</button>
            </div>
            <form onSubmit={handleGradeSubmission}>
              <div className="modal-body">
                <div style={{ backgroundColor: '#f8fafc', padding: '12px', borderRadius: '4px', marginBottom: '14px', fontSize: '12.5px' }}>
                  <strong>Student Submission:</strong>
                  <div style={{ marginTop: '4px', color: '#334155' }}>{activeSubmission.content}</div>
                </div>

                <div className="form-group">
                  <label className="form-label">Score (Max: {activeSubmission.max_score} pts)</label>
                  <input
                    className="form-input"
                    type="number"
                    min={0}
                    max={activeSubmission.max_score}
                    value={gradeScore}
                    onChange={e => setGradeScore(Number(e.target.value))}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Feedback Comments</label>
                  <textarea
                    className="form-textarea"
                    placeholder="Constructive feedback for the student..."
                    value={gradeFeedback}
                    onChange={e => setGradeFeedback(e.target.value)}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowGradingModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary btn-sm">Save Grade</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: LEADERBOARD (SQL Window Function RANK() OVER) */}
      {showLeaderboardModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Class Standings: {selectedCourseLeaderboardTitle}</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowLeaderboardModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: '12px', color: '#64748b', marginBottom: '12px' }}>
                Computed via PostgreSQL Window Function: <code>RANK() OVER (PARTITION BY course_id ORDER BY percentage DESC)</code>
              </p>
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Student</th>
                      <th>Total Score</th>
                      <th>Percentage</th>
                      <th>Grade</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leaderboardData.map(item => (
                      <tr key={item.student_id}>
                        <td>
                          <strong>#{item.rank}</strong>
                        </td>
                        <td>{item.student_name}</td>
                        <td>{item.total_score}</td>
                        <td>{item.percentage}%</td>
                        <td>
                          <span className={`badge ${item.grade === 'A+' || item.grade === 'A' ? 'badge-success' : item.grade === 'F' ? 'badge-danger' : 'badge-info'}`}>
                            {item.grade}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary btn-sm" onClick={() => setShowLeaderboardModal(false)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
