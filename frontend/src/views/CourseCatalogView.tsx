import React, { useState } from 'react';
import {
  Search,
  BookOpen,
  ArrowRight,
  GraduationCap,
  FileText,
  X,
  Code,
  Layers,
  Cpu,
  Languages,
  Brain
} from 'lucide-react';
import type { Course } from '../types';

interface CourseCatalogViewProps {
  courses: Course[];
  onSelectCourse: (course: Course) => void;
  onEnroll?: (courseId: number) => Promise<void>;
}

export const CourseCatalogView: React.FC<CourseCatalogViewProps> = ({
  courses,
  onSelectCourse,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilter, setSelectedFilter] = useState('ALL');
  const [syllabusModalCourse, setSyllabusModalCourse] = useState<Course | null>(null);

  const getCourseIcon = (code: string) => {
    switch (code) {
      case 'CS201':
        return <Code size={22} color="#2563eb" />;
      case 'CS301':
        return <Layers size={22} color="#0284c7" />;
      case 'CS305':
        return <Cpu size={22} color="#d97706" />;
      case 'LANG101':
        return <Languages size={22} color="#dc2626" />;
      case 'CS401':
        return <Brain size={22} color="#7c3aed" />;
      default:
        return <BookOpen size={22} color="#2563eb" />;
    }
  };

  const filteredCourses = courses.filter((c) => {
    const matchesSearch =
      c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.description.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (selectedFilter === 'CS') return c.code.startsWith('CS2');
    if (selectedFilter === 'SYSTEMS') return c.code.startsWith('CS3');
    if (selectedFilter === 'LANG') return c.code.startsWith('LANG');
    if (selectedFilter === 'AI') return c.code.startsWith('CS4');
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner / Filter Bar */}
      <div className="card" style={{ padding: '18px 24px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: '18px', fontWeight: 700, color: '#0f172a' }}>
              Academic Course Catalog
            </h1>
            <p style={{ fontSize: '13px', color: '#64748b', marginTop: '2px' }}>
              Explore core Computer Science, Systems, Languages, and AI curricula.
            </p>
          </div>

          {/* Search Box */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: '280px' }}>
            <div style={{ position: 'relative', width: '100%' }}>
              <input
                type="text"
                className="form-input"
                style={{ width: '100%', paddingLeft: '32px' }}
                placeholder="Search by code or title..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <Search size={15} color="#94a3b8" style={{ position: 'absolute', left: '10px', top: '10px' }} />
            </div>
          </div>
        </div>

        {/* Filter Chips */}
        <div style={{ display: 'flex', gap: '8px', marginTop: '16px', flexWrap: 'wrap' }}>
          {[
            { id: 'ALL', label: 'All Courses' },
            { id: 'CS', label: 'Data Structures (CS201)' },
            { id: 'SYSTEMS', label: 'Systems & OS (CS301, CS305)' },
            { id: 'LANG', label: 'Japanese & Humanities (LANG101)' },
            { id: 'AI', label: 'Machine Learning (CS401)' },
          ].map((chip) => (
            <button
              key={chip.id}
              onClick={() => setSelectedFilter(chip.id)}
              className={`type-tab-btn ${selectedFilter === chip.id ? 'active' : ''}`}
              style={{ fontSize: '12px', padding: '6px 14px' }}
            >
              {chip.label}
            </button>
          ))}
        </div>
      </div>

      {/* Courses Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
          gap: '18px',
        }}
      >
        {filteredCourses.map((course) => (
          <div key={course.id} className="card course-catalog-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div className="course-icon-badge">
                  {getCourseIcon(course.code)}
                </div>
                <div>
                  <span className="course-code-pill">{course.code}</span>
                  <h2 style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a', marginTop: '3px' }}>
                    {course.title}
                  </h2>
                </div>
              </div>
              <span className="badge badge-info">
                {course.credits || 4} Credits
              </span>
            </div>

            <p style={{ fontSize: '13px', color: '#475569', lineHeight: 1.5, margin: '14px 0', minHeight: '60px' }}>
              {course.description}
            </p>

            <div style={{ padding: '10px 12px', backgroundColor: '#f8fafc', borderRadius: '6px', border: '1px solid #e2e8f0', marginBottom: '14px', fontSize: '12px', color: '#64748b' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span><strong>Faculty:</strong> {course.teacher_name || 'Prof. Alan Turing'}</span>
                <span><strong>Term:</strong> Spring 2026</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span><strong>Dept:</strong> {course.department || 'Computer Science & Engineering'}</span>
                <span style={{ color: course.is_enrolled ? '#15803d' : '#2563eb', fontWeight: 600 }}>
                  {course.is_enrolled ? '✓ Enrolled' : 'Open for Registration'}
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setSyllabusModalCourse(course)}
              >
                <FileText size={13} /> View Syllabus
              </button>

              <button
                className="btn btn-primary btn-sm"
                onClick={() => onSelectCourse(course)}
              >
                Open Course Hub <ArrowRight size={13} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Syllabus Modal */}
      {syllabusModalCourse && (
        <div className="modal-overlay" onClick={() => setSyllabusModalCourse(null)}>
          <div className="modal-content modal-content-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <GraduationCap size={18} color="#1e3a8a" />
                <h3>{syllabusModalCourse.code}: {syllabusModalCourse.title} - Official Syllabus</h3>
              </div>
              <button
                onClick={() => setSyllabusModalCourse(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body" style={{ maxHeight: '65vh', overflowY: 'auto' }}>
              <div style={{ marginBottom: '16px', padding: '12px 14px', backgroundColor: '#eff6ff', borderRadius: '6px', border: '1px solid #bfdbfe' }}>
                <div style={{ fontWeight: 600, color: '#1e3a8a', fontSize: '13px' }}>Course Summary</div>
                <div style={{ fontSize: '12.5px', color: '#334155', marginTop: '4px' }}>
                  {syllabusModalCourse.description}
                </div>
              </div>

              <h4 style={{ fontSize: '13.5px', fontWeight: 700, color: '#0f172a', marginBottom: '8px' }}>
                Curriculum & Unit Breakdown
              </h4>
              <div
                style={{
                  backgroundColor: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  padding: '16px',
                  whiteSpace: 'pre-line',
                  fontSize: '13px',
                  lineHeight: 1.6,
                  color: '#334155',
                  fontFamily: 'inherit',
                }}
              >
                {syllabusModalCourse.syllabus || 'Unit 1: Foundations\nUnit 2: Core Concepts\nUnit 3: Applied Labs\nUnit 4: Advanced Topics'}
              </div>
            </div>

            <div className="modal-footer">
              <button
                className="btn btn-secondary"
                onClick={() => setSyllabusModalCourse(null)}
              >
                Close
              </button>
              <button
                className="btn btn-primary"
                onClick={() => {
                  const target = syllabusModalCourse;
                  setSyllabusModalCourse(null);
                  onSelectCourse(target);
                }}
              >
                Enter Course Workspace <ArrowRight size={13} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
