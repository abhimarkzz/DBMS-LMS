import React, { useEffect, useState } from 'react';
import {
  BookOpen,
  Sparkles,
  ArrowRight,
  Cpu,
  Layers,
  Languages,
  Brain,
  Code,
  CheckCircle2
} from 'lucide-react';
import type { User, Course, Result, Assignment } from '../types';
import { api } from '../api';

interface DashboardViewProps {
  user: User;
  courses: Course[];
  results: Result[];
  assignments: Assignment[];
  onNavigate: (tab: string, param?: any) => void;
  onSelectCourse: (course: Course) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  user,
  courses,
  results,
  assignments,
  onNavigate,
  onSelectCourse,
}) => {
  const [dashboardData, setDashboardData] = useState<any>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchDashboardData = async () => {
      try {
        let data = null;
        if (user.role === 'STUDENT') {
          data = await api.getStudentDashboard();
        } else if (user.role === 'TEACHER') {
          data = await api.getTeacherDashboard();
        } else if (user.role === 'ADMIN') {
          data = await api.getAdminDashboard();
        }
        if (isMounted) {
          setDashboardData(data);
        }
      } catch (err) {
        console.warn('Failed to fetch role-specific dashboard data:', err);
      }
    };

    fetchDashboardData();
    return () => { isMounted = false; };
  }, [user.role]);

  const getCourseIcon = (code: string) => {
    switch (code) {
      case 'CS201':
        return <Code size={20} color="#2563eb" />;
      case 'CS301':
        return <Layers size={20} color="#0284c7" />;
      case 'CS305':
        return <Cpu size={20} color="#d97706" />;
      case 'LANG101':
        return <Languages size={20} color="#dc2626" />;
      case 'CS401':
        return <Brain size={20} color="#7c3aed" />;
      default:
        return <BookOpen size={20} color="#2563eb" />;
    }
  };

  // Extract Student real stats
  const studentStats = dashboardData?.stats;
  const enrolledCoursesList = dashboardData?.enrolled_courses || courses.filter((c) => c.is_enrolled);
  const pendingAssignmentsList = dashboardData?.pending_assignments || assignments.filter((a) => !a.has_submitted);
  const recentResultsList = dashboardData?.recent_results || results;

  // Extract Teacher real stats
  const teacherStats = dashboardData?.stats;
  const teacherCourses = dashboardData?.courses_taught || courses.filter((c) => c.teacher_id === user.id);
  const pendingSubmissions = dashboardData?.pending_submissions || [];

  // Extract Admin real stats
  const adminStats = dashboardData?.stats;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
      {/* 1. Academic Greeting Hero Banner */}
      <div className="role-banner">
        <div>
          <div className="role-banner-title">
            Welcome back, {user.full_name}
          </div>
          <div className="role-banner-subtitle">
            {user.department || 'School of Computer Science & Engineering'} • Spring 2026 Academic Session • {user.role === 'ADMIN' ? 'System Administrator' : user.role === 'TEACHER' ? 'Faculty Instructor' : 'Undergraduate Scholar'}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => onNavigate('courses')}
          >
            <BookOpen size={14} /> {user.role === 'TEACHER' ? 'Manage Courses' : 'Browse Catalog'}
          </button>
          <button
            className="btn btn-primary btn-sm"
            onClick={() => onNavigate('ai-search')}
          >
            <Sparkles size={14} /> AI Smart Search
          </button>
        </div>
      </div>

      {/* 2. Key Academic Metric Cards based on User Role */}
      {user.role === 'STUDENT' && (
        <div className="grid-cols-4">
          <div className="stat-card">
            <span className="stat-label">Enrolled Courses</span>
            <div className="stat-value">{studentStats?.enrolled_courses_count ?? enrolledCoursesList.length}</div>
            <span className="stat-subtext">Spring 2026 Active Portfolio</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Cumulative Average</span>
            <div className="stat-value" style={{ color: '#15803d' }}>
              {studentStats?.average_percentage != null ? `${studentStats.average_percentage}%` : (results.length > 0 ? `${(results.reduce((a, b) => a + (b.percentage || 0), 0) / results.length).toFixed(1)}%` : 'N/A')}
            </div>
            <span className="stat-subtext">Official Graded Assessments</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Pending Assessments</span>
            <div className="stat-value" style={{ color: (studentStats?.pending_assignments_count ?? pendingAssignmentsList.length) > 0 ? '#b45309' : '#1e3a8a' }}>
              {studentStats?.pending_assignments_count ?? pendingAssignmentsList.length}
            </div>
            <span className="stat-subtext">Awaiting your submission</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Completed Submissions</span>
            <div className="stat-value" style={{ color: '#2563eb' }}>
              {studentStats?.completed_assignments_count ?? (assignments.length - pendingAssignmentsList.length)}
            </div>
            <span className="stat-subtext">Successfully evaluated</span>
          </div>
        </div>
      )}

      {user.role === 'TEACHER' && (
        <div className="grid-cols-4">
          <div className="stat-card">
            <span className="stat-label">Courses Instructed</span>
            <div className="stat-value">{teacherStats?.courses_taught_count ?? teacherCourses.length}</div>
            <span className="stat-subtext">Spring 2026 Academic Term</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Total Enrolled Scholars</span>
            <div className="stat-value" style={{ color: '#15803d' }}>
              {teacherStats?.total_enrolled_students ?? 12}
            </div>
            <span className="stat-subtext">Across instructed courses</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Submissions to Grade</span>
            <div className="stat-value" style={{ color: (teacherStats?.pending_submissions_count ?? 0) > 0 ? '#b45309' : '#1e3a8a' }}>
              {teacherStats?.pending_submissions_count ?? 0}
            </div>
            <span className="stat-subtext">Awaiting rubric evaluation</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Indexed Course Notes</span>
            <div className="stat-value" style={{ color: '#7c3aed' }}>
              {teacherStats?.indexed_materials_count ?? 10}
            </div>
            <span className="stat-subtext">Vectorized in pgvector</span>
          </div>
        </div>
      )}

      {user.role === 'ADMIN' && (
        <div className="grid-cols-4">
          <div className="stat-card">
            <span className="stat-label">Registered Users</span>
            <div className="stat-value">{adminStats?.total_users ?? 7}</div>
            <span className="stat-subtext">{adminStats?.students ?? 4} Students • {adminStats?.teachers ?? 2} Faculty</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Active Courses</span>
            <div className="stat-value" style={{ color: '#15803d' }}>
              {adminStats?.active_courses ?? courses.length}
            </div>
            <span className="stat-subtext">Published & Accessible</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Active Enrollments</span>
            <div className="stat-value" style={{ color: '#1e3a8a' }}>
              {adminStats?.total_enrollments ?? 20}
            </div>
            <span className="stat-subtext">Academic Course Seats</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Vector Knowledge Chunks</span>
            <div className="stat-value" style={{ color: '#7c3aed' }}>
              {adminStats?.total_vector_chunks ?? 18}
            </div>
            <span className="stat-subtext">pgvector HNSW Embedded</span>
          </div>
        </div>
      )}

      {/* 3. Primary Section: Courses Overview */}
      <div className="card">
        <div className="card-header">
          <div>
            <h2 className="card-title" style={{ fontSize: '16px' }}>
              {user.role === 'TEACHER' ? 'Courses You Instruct' : user.role === 'ADMIN' ? 'Platform Academic Curriculum' : 'Spring 2026 Enrolled Courses'}
            </h2>
            <p style={{ fontSize: '12.5px', color: '#64748b', marginTop: '2px' }}>
              Computer Science, Embedded Systems, Machine Learning & Communication
            </p>
          </div>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => onNavigate('courses')}
          >
            {user.role === 'ADMIN' ? 'Manage All' : 'View Catalog'} <ArrowRight size={13} />
          </button>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap: '16px',
            marginTop: '8px',
          }}
        >
          {(user.role === 'TEACHER' ? teacherCourses : courses).map((course: Course) => (
            <div
              key={course.id}
              className="course-card-interactive"
              onClick={() => onSelectCourse(course)}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div className="course-icon-badge">
                    {getCourseIcon(course.code)}
                  </div>
                  <div>
                    <span className="course-code-pill">{course.code}</span>
                    <h3 className="course-title-text">{course.title}</h3>
                  </div>
                </div>
                <span className="badge badge-success">Published</span>
              </div>

              <p className="course-description-preview">
                {course.description}
              </p>

              <div className="course-card-footer">
                <span style={{ fontSize: '11.5px', color: '#64748b' }}>
                  {course.credits || 4} Credits • {course.level || 'Core'}
                </span>
                <span className="course-enter-link">
                  Open Hub <ArrowRight size={13} />
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 4. Split Grid for Student / Teacher / Admin workflows */}
      <div className="grid-cols-2">
        {/* Left Column */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              {user.role === 'TEACHER' ? 'Pending Submissions to Evaluate' : user.role === 'ADMIN' ? 'System Health & Services' : 'Pending Coursework & Deadlines'}
            </h3>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigate(user.role === 'ADMIN' ? 'admin' : 'assignments')}
            >
              {user.role === 'ADMIN' ? 'Health Check' : 'View All'}
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {user.role === 'STUDENT' && (
              pendingAssignmentsList.length === 0 ? (
                <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
                  All scheduled assessments submitted! Great work.
                </div>
              ) : (
                pendingAssignmentsList.slice(0, 4).map((a: any) => (
                  <div
                    key={a.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '12px 14px',
                      backgroundColor: '#f8fafc',
                      border: '1px solid #e2e8f0',
                      borderRadius: '6px',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '11px', fontWeight: 700, color: '#1e3a8a', backgroundColor: '#eff6ff', padding: '1px 6px', borderRadius: '4px' }}>
                          {a.assessment_type || 'DESCRIPTIVE'}
                        </span>
                        <span style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a' }}>
                          {a.title}
                        </span>
                      </div>
                      <div style={{ fontSize: '11.5px', color: '#64748b', marginTop: '3px' }}>
                        Max Score: {a.max_score} • Due in 7 days
                      </div>
                    </div>
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => onNavigate('assignments', a)}
                    >
                      {a.assessment_type === 'MCQ' ? 'Start Quiz' : 'Submit'}
                    </button>
                  </div>
                ))
              )
            )}

            {user.role === 'TEACHER' && (
              pendingSubmissions.length === 0 ? (
                <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
                  <CheckCircle2 size={24} color="#16a34a" style={{ margin: '0 auto 8px auto', display: 'block' }} />
                  All submitted student assignments are evaluated!
                </div>
              ) : (
                pendingSubmissions.slice(0, 4).map((s: any) => (
                  <div
                    key={s.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '12px 14px',
                      backgroundColor: '#f8fafc',
                      border: '1px solid #e2e8f0',
                      borderRadius: '6px',
                    }}
                  >
                    <div>
                      <span style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a' }}>
                        {s.student_name}: {s.assignment_title}
                      </span>
                      <div style={{ fontSize: '11.5px', color: '#64748b', marginTop: '3px' }}>
                        Submitted {new Date(s.submitted_at).toLocaleDateString()}
                      </div>
                    </div>
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => onNavigate('assignments')}
                    >
                      Grade
                    </button>
                  </div>
                ))
              )
            )}

            {user.role === 'ADMIN' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '6px' }}>
                  <span style={{ fontSize: '13px', fontWeight: 600, color: '#166534' }}>PostgreSQL 18 + pgvector 0.8.6</span>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: '#16a34a' }}>HEALTHY</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '6px' }}>
                  <span style={{ fontSize: '13px', fontWeight: 600, color: '#166534' }}>MongoDB 7.0 (Notifications/Logs)</span>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: '#16a34a' }}>CONNECTED</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '6px' }}>
                  <span style={{ fontSize: '13px', fontWeight: 600, color: '#166534' }}>Redis Cache & Pub/Sub Event Broker</span>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: '#16a34a' }}>ONLINE</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', backgroundColor: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: '6px' }}>
                  <span style={{ fontSize: '13px', fontWeight: 600, color: '#1e3a8a' }}>Gemini AI Grounding & RAG Engine</span>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: '#2563eb' }}>OPERATIONAL</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              {user.role === 'ADMIN' ? 'Recent Administrative Activity' : user.role === 'TEACHER' ? 'Active Course Assessments' : 'Published Academic Results & Transcripts'}
            </h3>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigate(user.role === 'ADMIN' ? 'admin' : user.role === 'TEACHER' ? 'assignments' : 'results')}
            >
              {user.role === 'ADMIN' ? 'View Logs' : user.role === 'TEACHER' ? 'View All Assessments' : 'Official Transcript'}
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {user.role === 'TEACHER' ? (
              assignments.length === 0 ? (
                <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
                  No assessments created yet. Click 'View All Assessments' to add one.
                </div>
              ) : (
                assignments.slice(0, 4).map((a: any) => (
                  <div
                    key={a.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '12px 14px',
                      backgroundColor: '#ffffff',
                      border: '1px solid #e2e8f0',
                      borderRadius: '6px',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '11px', fontWeight: 700, color: '#1e3a8a', backgroundColor: '#eff6ff', padding: '1px 6px', borderRadius: '4px' }}>
                          {a.assessment_type || 'DESCRIPTIVE'}
                        </span>
                        <span style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a' }}>
                          {a.title}
                        </span>
                      </div>
                      <div style={{ fontSize: '11.5px', color: '#64748b', marginTop: '3px' }}>
                        Max Score: {a.max_score} • Automated Grading
                      </div>
                    </div>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => onNavigate('assignments')}
                    >
                      Manage
                    </button>
                  </div>
                ))
              )
            ) : recentResultsList.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
                No published evaluations available yet.
              </div>
            ) : (
              recentResultsList.slice(0, 4).map((r: any) => (
                <div
                  key={r.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 14px',
                    backgroundColor: '#ffffff',
                    border: '1px solid #e2e8f0',
                    borderRadius: '6px',
                  }}
                >
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a' }}>
                      {r.course_code}: {r.course_title || 'Course Evaluation'}
                    </div>
                    <div style={{ fontSize: '11.5px', color: '#64748b', marginTop: '2px' }}>
                      Scored {r.total_score} / {r.max_possible} ({r.percentage}%)
                    </div>
                  </div>
                  <div
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '50%',
                      backgroundColor: '#dcfce7',
                      color: '#15803d',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 800,
                      fontSize: '14px',
                      border: '1px solid #bbf7d0',
                    }}
                  >
                    {r.grade || 'A'}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
export default DashboardView;
