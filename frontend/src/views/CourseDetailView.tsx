import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  BookOpen,
  FileText,
  CheckSquare,
  Eye,
  Sparkles,
  X,
  Download,
  Loader2,
  AlertCircle,
  Check,
  Megaphone,
  Info
} from 'lucide-react';
import type { Course, StudyMaterial, Assignment } from '../types';
import { openProtectedMaterial, downloadProtectedMaterial } from '../utils/materialViewer';
import { api } from '../api';

interface CourseDetailViewProps {
  course: Course;
  materials: StudyMaterial[];
  assignments: Assignment[];
  onBack: () => void;
  onOpenAssignment: (assignment: Assignment) => void;
  onOpenAISearchForCourse: (courseId: number, courseCode: string) => void;
}

type TabType = 'overview' | 'materials' | 'assignments' | 'syllabus' | 'announcements';

export const CourseDetailView: React.FC<CourseDetailViewProps> = ({
  course,
  materials,
  assignments,
  onBack,
  onOpenAssignment,
  onOpenAISearchForCourse,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [readingMaterial, setReadingMaterial] = useState<StudyMaterial | null>(null);
  const [activeMaterialAction, setActiveMaterialAction] = useState<{ materialId: number; type: 'open' | 'download' } | null>(null);
  const [materialFeedback, setMaterialFeedback] = useState<{ text: string; isError: boolean } | null>(null);
  const [announcements, setAnnouncements] = useState<any[]>([]);

  useEffect(() => {
    let isMounted = true;
    api.getCourseDetail(course.id)
      .then((detail) => {
        if (isMounted && detail?.announcements) {
          setAnnouncements(detail.announcements);
        }
      })
      .catch((err) => console.warn('Could not load course detail extras:', err));
    return () => { isMounted = false; };
  }, [course.id]);

  const handleOpenMaterial = async (mat: StudyMaterial) => {
    setActiveMaterialAction({ materialId: mat.id, type: 'open' });
    setMaterialFeedback(null);
    try {
      const res = await openProtectedMaterial(
        mat.course_id,
        mat.id,
        mat.title,
        (text, filename) => {
          setReadingMaterial({ ...mat, title: filename, content: text });
        }
      );
      if (res.action === 'DOWNLOADED') {
        setMaterialFeedback({ text: `Downloaded "${res.filename}" successfully.`, isError: false });
      }
    } catch (err: any) {
      setMaterialFeedback({ text: err.message || 'Failed to open material.', isError: true });
    } finally {
      setActiveMaterialAction(null);
    }
  };

  const handleDownloadMaterial = async (mat: StudyMaterial) => {
    setActiveMaterialAction({ materialId: mat.id, type: 'download' });
    setMaterialFeedback(null);
    try {
      const res = await downloadProtectedMaterial(mat.course_id, mat.id, mat.title);
      setMaterialFeedback({ text: `Downloaded "${res.filename}" successfully.`, isError: false });
    } catch (err: any) {
      setMaterialFeedback({ text: err.message || 'Failed to download material.', isError: true });
    } finally {
      setActiveMaterialAction(null);
    }
  };

  const courseMaterials = materials.filter((m) => m.course_id === course.id);
  const courseAssignments = assignments.filter((a) => a.course_id === course.id);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Course Header Banner */}
      <div className="card" style={{ padding: '22px 28px', borderLeft: '4px solid #1e3a8a' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
          <button className="btn btn-secondary btn-sm" onClick={onBack}>
            <ArrowLeft size={14} /> Back to Courses
          </button>
          <span className="course-code-pill">{course.code}</span>
          <span className="badge badge-success">Active Enrollment</span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#0f172a', letterSpacing: '-0.02em' }}>
              {course.title}
            </h1>
            <p style={{ fontSize: '13.5px', color: '#475569', marginTop: '6px', maxWidth: '750px', lineHeight: 1.5 }}>
              {course.description}
            </p>
            <div style={{ display: 'flex', gap: '14px', marginTop: '10px', fontSize: '12px', color: '#64748b', flexWrap: 'wrap' }}>
              <span><strong>Instructor:</strong> {course.teacher_name || 'Prof. Alan Turing'}</span>
              <span>•</span>
              <span><strong>Credits:</strong> {course.credits || 4}</span>
              <span>•</span>
              <span><strong>Department:</strong> {course.department || 'Computer Science & Engineering'}</span>
              <span>•</span>
              <span><strong>Session:</strong> Spring 2026</span>
            </div>
          </div>

          <button
            className="btn btn-primary"
            onClick={() => onOpenAISearchForCourse(course.id, course.code)}
            style={{ gap: '8px' }}
          >
            <Sparkles size={15} /> Search Notes with AI
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="course-nav-tabs">
        <button
          className={`course-nav-tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <Info size={15} />
          <span>Overview</span>
        </button>

        <button
          className={`course-nav-tab ${activeTab === 'materials' ? 'active' : ''}`}
          onClick={() => setActiveTab('materials')}
        >
          <FileText size={15} />
          <span>Study Materials ({courseMaterials.length})</span>
        </button>

        <button
          className={`course-nav-tab ${activeTab === 'assignments' ? 'active' : ''}`}
          onClick={() => setActiveTab('assignments')}
        >
          <CheckSquare size={15} />
          <span>Assignments & Quizzes ({courseAssignments.length})</span>
        </button>

        <button
          className={`course-nav-tab ${activeTab === 'syllabus' ? 'active' : ''}`}
          onClick={() => setActiveTab('syllabus')}
        >
          <BookOpen size={15} />
          <span>Syllabus</span>
        </button>

        <button
          className={`course-nav-tab ${activeTab === 'announcements' ? 'active' : ''}`}
          onClick={() => setActiveTab('announcements')}
        >
          <Megaphone size={15} />
          <span>Announcements ({announcements.length})</span>
        </button>
      </div>

      {/* Tab 0: Overview */}
      {activeTab === 'overview' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div className="card" style={{ padding: '20px 24px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a', marginBottom: '12px' }}>
              Academic Course Specification
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
              <div style={{ padding: '12px 14px', backgroundColor: '#f8fafc', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 600, display: 'block' }}>Faculty Instructor</span>
                <span style={{ fontSize: '13.5px', fontWeight: 600, color: '#0f172a' }}>{course.teacher_name || 'Prof. Alan Turing'}</span>
              </div>
              <div style={{ padding: '12px 14px', backgroundColor: '#f8fafc', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 600, display: 'block' }}>Department</span>
                <span style={{ fontSize: '13.5px', fontWeight: 600, color: '#0f172a' }}>{course.department || 'Computer Science & Engineering'}</span>
              </div>
              <div style={{ padding: '12px 14px', backgroundColor: '#f8fafc', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 600, display: 'block' }}>Academic Level</span>
                <span style={{ fontSize: '13.5px', fontWeight: 600, color: '#0f172a' }}>{course.level || 'Undergraduate Core'}</span>
              </div>
              <div style={{ padding: '12px 14px', backgroundColor: '#f8fafc', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 600, display: 'block' }}>Credits / Term</span>
                <span style={{ fontSize: '13.5px', fontWeight: 600, color: '#0f172a' }}>{course.credits || 4} Credits • Spring 2026</span>
              </div>
            </div>

            <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#0f172a', marginTop: '20px', marginBottom: '8px' }}>
              Course Description & Objectives
            </h4>
            <p style={{ fontSize: '13px', lineHeight: 1.6, color: '#334155', margin: 0 }}>
              {course.description}
            </p>
          </div>
        </div>
      )}

      {/* Tab 1: Study Materials */}
      {activeTab === 'materials' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {materialFeedback && (
            <div
              style={{
                padding: '10px 14px',
                borderRadius: '6px',
                fontSize: '13px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                backgroundColor: materialFeedback.isError ? '#fef2f2' : '#f0fdf4',
                border: `1px solid ${materialFeedback.isError ? '#fecaca' : '#bbf7d0'}`,
                color: materialFeedback.isError ? '#991b1b' : '#166534',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {materialFeedback.isError ? <AlertCircle size={15} /> : <Check size={15} />}
                <span>{materialFeedback.text}</span>
              </div>
              <button
                onClick={() => setMaterialFeedback(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}
              >
                <X size={14} />
              </button>
            </div>
          )}

          {courseMaterials.length === 0 ? (
            <div className="card empty-state" style={{ padding: '40px' }}>
              <FileText className="empty-state-icon" />
              <div className="empty-state-title">No Materials Published Yet</div>
              <p className="empty-state-desc">The instructor has not uploaded lecture notes for this course.</p>
            </div>
          ) : (
            courseMaterials.map((mat) => {
              const isOpenLoading = activeMaterialAction?.materialId === mat.id && activeMaterialAction.type === 'open';
              const isDownloadLoading = activeMaterialAction?.materialId === mat.id && activeMaterialAction.type === 'download';

              return (
                <div
                  key={mat.id}
                  className="card"
                  style={{
                    padding: '16px 20px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '16px',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <div
                      style={{
                        width: '38px',
                        height: '38px',
                        borderRadius: '8px',
                        backgroundColor: '#eff6ff',
                        color: '#1e3a8a',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      <FileText size={18} />
                    </div>
                    <div>
                      <h3 style={{ fontSize: '14.5px', fontWeight: 600, color: '#0f172a' }}>{mat.title}</h3>
                      <div style={{ display: 'flex', gap: '10px', marginTop: '4px', fontSize: '12px', color: '#64748b' }}>
                        <span>Type: {mat.material_type || 'NOTES'}</span>
                        <span>•</span>
                        <span style={{ color: mat.status === 'INDEXED' ? '#15803d' : '#2563eb', fontWeight: 600 }}>
                          ✓ Vectorized in pgvector ({mat.chunk_count || 1} chunks)
                        </span>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleOpenMaterial(mat)}
                      disabled={isOpenLoading || isDownloadLoading}
                      style={{ gap: '5px' }}
                    >
                      {isOpenLoading ? <Loader2 size={13} className="animate-spin" /> : <Eye size={13} />}
                      <span>{isOpenLoading ? 'Opening...' : 'Read Notes'}</span>
                    </button>

                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => handleDownloadMaterial(mat)}
                      disabled={isOpenLoading || isDownloadLoading}
                      style={{ gap: '5px' }}
                    >
                      {isDownloadLoading ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
                      <span>{isDownloadLoading ? 'Downloading...' : 'Download'}</span>
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Tab 2: Assignments & Quizzes */}
      {activeTab === 'assignments' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {courseAssignments.length === 0 ? (
            <div className="card empty-state" style={{ padding: '40px' }}>
              <CheckSquare className="empty-state-icon" />
              <div className="empty-state-title">No Assignments Published</div>
              <p className="empty-state-desc">There are no pending assignments or quizzes for this course.</p>
            </div>
          ) : (
            courseAssignments.map((a) => (
              <div
                key={a.id}
                className="card"
                style={{
                  padding: '16px 20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '16px',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        backgroundColor: a.assessment_type === 'MCQ' ? '#f0fdf4' : '#eff6ff',
                        color: a.assessment_type === 'MCQ' ? '#15803d' : '#1e3a8a',
                        padding: '2px 7px',
                        borderRadius: '4px',
                      }}
                    >
                      {a.assessment_type}
                    </span>
                    <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#0f172a' }}>{a.title}</h3>
                  </div>
                  <p style={{ fontSize: '13px', color: '#475569', marginTop: '4px' }}>{a.description}</p>
                  <div style={{ display: 'flex', gap: '12px', marginTop: '6px', fontSize: '12px', color: '#64748b' }}>
                    <span>Max Score: <strong>{a.max_score}</strong></span>
                    <span>•</span>
                    <span>Due: 7 Days from Enrollment</span>
                  </div>
                </div>

                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => onOpenAssignment(a)}
                >
                  {a.assessment_type === 'MCQ' ? 'Start Quiz' : 'Open Workspace'}
                </button>
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab 3: Syllabus */}
      {activeTab === 'syllabus' && (
        <div className="card" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#0f172a', marginBottom: '12px' }}>
            Official Unit & Curriculum Breakdown
          </h3>
          <div
            style={{
              backgroundColor: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '6px',
              padding: '20px',
              whiteSpace: 'pre-line',
              fontSize: '13.5px',
              lineHeight: 1.7,
              color: '#334155',
            }}
          >
            {course.syllabus || 'Unit 1: Fundamentals\nUnit 2: Core Paradigms\nUnit 3: Implementation & Benchmarks\nUnit 4: Advanced Systems'}
          </div>
        </div>
      )}

      {/* Tab 4: Announcements */}
      {activeTab === 'announcements' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {announcements.length === 0 ? (
            <div className="card empty-state" style={{ padding: '40px' }}>
              <Megaphone className="empty-state-icon" />
              <div className="empty-state-title">No Course Announcements</div>
              <p className="empty-state-desc">The instructor has not posted any announcements for this course yet.</p>
            </div>
          ) : (
            announcements.map((ann) => (
              <div key={ann.id} className="card" style={{ padding: '18px 22px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a', margin: 0 }}>
                    {ann.title}
                  </h3>
                  <span style={{ fontSize: '12px', color: '#64748b' }}>
                    {new Date(ann.created_at).toLocaleDateString()}
                  </span>
                </div>
                <p style={{ fontSize: '13.5px', color: '#334155', lineHeight: 1.6, margin: 0 }}>
                  {ann.content}
                </p>
                <div style={{ marginTop: '10px', fontSize: '11.5px', color: '#64748b' }}>
                  Posted by: <strong>{ann.author_name || 'Faculty Instructor'}</strong>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Full-Text Material Reader Modal */}
      {readingMaterial && (
        <div className="modal-overlay" onClick={() => setReadingMaterial(null)}>
          <div className="modal-content modal-content-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileText size={18} color="#1e3a8a" />
                <h3>{readingMaterial.title}</h3>
              </div>
              <button
                onClick={() => setReadingMaterial(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              <div
                style={{
                  backgroundColor: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  padding: '20px',
                  fontSize: '14px',
                  lineHeight: 1.7,
                  color: '#1e293b',
                  whiteSpace: 'pre-line',
                }}
              >
                {readingMaterial.content}
              </div>
            </div>

            <div className="modal-footer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => handleDownloadMaterial(readingMaterial)}
                disabled={activeMaterialAction?.materialId === readingMaterial.id}
                style={{ gap: '5px' }}
              >
                {activeMaterialAction?.materialId === readingMaterial.id && activeMaterialAction.type === 'download' ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <Download size={12} />
                )}
                <span>Download Notes</span>
              </button>

              <button className="btn btn-secondary" onClick={() => setReadingMaterial(null)}>
                Close Reader
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default CourseDetailView;
