import React, { useState } from 'react';
import {
  FileText,
  Search,
  CheckCircle2,
  Eye,
  Sparkles,
  X,
  Download,
  Loader2,
  AlertCircle,
  Check
} from 'lucide-react';
import type { StudyMaterial, Course } from '../types';
import { openProtectedMaterial, downloadProtectedMaterial } from '../utils/materialViewer';

interface StudyMaterialsViewProps {
  materials: StudyMaterial[];
  courses: Course[];
  onOpenAISearchForCourse: (courseId: number, courseCode: string) => void;
}

export const StudyMaterialsView: React.FC<StudyMaterialsViewProps> = ({
  materials,
  courses,
  onOpenAISearchForCourse,
}) => {
  const [selectedCourse, setSelectedCourse] = useState<number | 'ALL'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [readingMaterial, setReadingMaterial] = useState<StudyMaterial | null>(null);
  const [activeMaterialAction, setActiveMaterialAction] = useState<{ materialId: number; type: 'open' | 'download' } | null>(null);
  const [materialFeedback, setMaterialFeedback] = useState<{ text: string; isError: boolean } | null>(null);

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

  const getCourseCode = (courseId: number) => {
    const c = courses.find((course) => course.id === courseId);
    return c ? c.code : 'COURSE';
  };

  const filtered = materials.filter((m) => {
    if (selectedCourse !== 'ALL' && m.course_id !== selectedCourse) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return m.title.toLowerCase().includes(q) || m.content.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner & Filter Card */}
      <div className="card" style={{ padding: '20px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={18} color="#1e3a8a" />
              <h1 style={{ fontSize: '18px', fontWeight: 700, color: '#0f172a' }}>
                Course Study Materials & Lecture Notes
              </h1>
            </div>
            <p style={{ fontSize: '13px', color: '#64748b', marginTop: '4px' }}>
              Full text lecture modules vectorized in pgvector for semantic retrieval.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            {/* Search Input */}
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                className="form-input"
                style={{ paddingLeft: '32px', minWidth: '220px' }}
                placeholder="Search note contents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <Search size={14} color="#94a3b8" style={{ position: 'absolute', left: '10px', top: '10px' }} />
            </div>

            {/* Course Filter */}
            <select
              className="form-select"
              value={selectedCourse}
              onChange={(e) => setSelectedCourse(e.target.value === 'ALL' ? 'ALL' : Number(e.target.value))}
            >
              <option value="ALL">All Courses</option>
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code}: {c.title}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Feedback Banner */}
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

      {/* Materials Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '18px' }}>
        {filtered.length === 0 ? (
          <div className="empty-state" style={{ gridColumn: '1 / -1' }}>
            <FileText className="empty-state-icon" />
            <div className="empty-state-title">No Materials Found</div>
            <p className="empty-state-desc">No study notes match the chosen course or search criteria.</p>
          </div>
        ) : (
          filtered.map((mat) => (
            <div key={mat.id} className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                  <span className="course-code-pill">{getCourseCode(mat.course_id)}</span>
                  <span className="badge badge-success" style={{ gap: '4px' }}>
                    <CheckCircle2 size={11} /> Vector Indexed
                  </span>
                </div>

                <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a', margin: '12px 0 8px 0' }}>
                  {mat.title}
                </h3>

                <p style={{ fontSize: '13px', color: '#475569', lineHeight: 1.5, maxHeight: '80px', overflow: 'hidden' }}>
                  {mat.content}
                </p>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '18px', paddingTop: '12px', borderTop: '1px solid #f1f5f9', gap: '8px', flexWrap: 'wrap' }}>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => onOpenAISearchForCourse(mat.course_id, getCourseCode(mat.course_id))}
                  style={{ gap: '5px' }}
                >
                  <Sparkles size={12} color="#2563eb" /> Ask AI
                </button>

                <div style={{ display: 'flex', gap: '6px' }}>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => handleOpenMaterial(mat)}
                    disabled={activeMaterialAction?.materialId === mat.id}
                    style={{ gap: '4px' }}
                  >
                    {activeMaterialAction?.materialId === mat.id && activeMaterialAction.type === 'open' ? (
                      <Loader2 size={12} className="animate-spin" />
                    ) : (
                      <Eye size={12} />
                    )}
                    <span>Open Material</span>
                  </button>

                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleDownloadMaterial(mat)}
                    disabled={activeMaterialAction?.materialId === mat.id}
                    style={{ gap: '4px' }}
                    title="Download material file"
                  >
                    {activeMaterialAction?.materialId === mat.id && activeMaterialAction.type === 'download' ? (
                      <Loader2 size={12} className="animate-spin" />
                    ) : (
                      <Download size={12} />
                    )}
                    <span>Download</span>
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Note Reader Modal */}
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
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <span className="course-code-pill">{getCourseCode(readingMaterial.course_id)}</span>
                <span className="badge badge-success">Grounded & Verified</span>
              </div>

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
