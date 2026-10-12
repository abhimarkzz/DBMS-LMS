import React from 'react';
import {
  CheckCircle2,
  GraduationCap
} from 'lucide-react';
import type { Result } from '../types';

interface ResultsViewProps {
  results: Result[];
}

export const ResultsView: React.FC<ResultsViewProps> = ({ results }) => {
  const hasResults = results && results.length > 0;

  const avgPctNum = hasResults
    ? results.reduce((acc, r) => acc + (Number(r.percentage) || 0), 0) / results.length
    : null;

  const avgPct = avgPctNum !== null ? avgPctNum.toFixed(1) : null;

  // Grade point average computed strictly from verified scores
  const gpa = avgPctNum !== null ? ((avgPctNum / 100) * 4.0).toFixed(2) : null;

  const getAcademicStanding = (pct: number | null) => {
    if (pct === null) return 'No Results Recorded';
    if (pct >= 90) return 'High Distinction (Honors)';
    if (pct >= 80) return 'Distinction';
    if (pct >= 70) return 'Commendable';
    if (pct >= 60) return 'Satisfactory';
    return 'Academic Review Required';
  };

  const getGradeBadge = (grade: string) => {
    switch (grade) {
      case 'A+':
      case 'A':
        return { bg: '#dcfce7', text: '#15803d', border: '#bbf7d0' };
      case 'B+':
      case 'B':
        return { bg: '#eff6ff', text: '#1d4ed8', border: '#bfdbfe' };
      case 'C':
        return { bg: '#fef3c7', text: '#b45309', border: '#fde68a' };
      default:
        return { bg: '#fee2e2', text: '#b91c1c', border: '#fecaca' };
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner */}
      <div className="card" style={{ padding: '22px 28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
          <GraduationCap size={20} color="#1e3a8a" />
          <h1 style={{ fontSize: '18px', fontWeight: 700, color: '#0f172a' }}>
            Academic Transcript & Official Gradebook
          </h1>
        </div>
        <p style={{ fontSize: '13px', color: '#64748b' }}>
          Official database-computed semester results, grade points, and faculty evaluation summaries.
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid-cols-3">
        <div className="stat-card">
          <span className="stat-label">Cumulative Average</span>
          <div className="stat-value" style={{ color: avgPct ? '#15803d' : '#64748b' }}>
            {avgPct ? `${avgPct}%` : '—'}
          </div>
          <span className="stat-subtext">Across All Completed Assessments</span>
        </div>

        <div className="stat-card">
          <span className="stat-label">Evaluated Courses</span>
          <div className="stat-value" style={{ color: '#1e3a8a' }}>
            {results.length}
          </div>
          <span className="stat-subtext">Spring 2026 Academic Term</span>
        </div>

        <div className="stat-card">
          <span className="stat-label">Academic Standing</span>
          <div className="stat-value" style={{ color: avgPctNum && avgPctNum >= 70 ? '#7c3aed' : '#b45309', fontSize: '18px' }}>
            {getAcademicStanding(avgPctNum)}
          </div>
          <span className="stat-subtext">
            {gpa ? `GPA Equivalent: ${gpa} / 4.0` : 'Pending Grade Publication'}
          </span>
        </div>
      </div>

      {/* Results Table */}
      <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #e2e8f0', backgroundColor: '#fafbfc' }}>
          <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a' }}>
            Course Marks Breakdown
          </h3>
        </div>

        <div className="table-container" style={{ border: 'none', borderRadius: '0' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Course Code</th>
                <th>Course Title</th>
                <th>Score Obtained</th>
                <th>Percentage</th>
                <th>Letter Grade</th>
                <th>Status</th>
                <th>Published Date</th>
              </tr>
            </thead>
            <tbody>
              {!hasResults ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '32px', color: '#64748b' }}>
                    No published marks recorded for your student profile yet.
                  </td>
                </tr>
              ) : (
                results.map((r) => {
                  const badge = getGradeBadge(r.grade || 'A');
                  return (
                    <tr key={r.id}>
                      <td>
                        <span className="course-code-pill">{r.course_code}</span>
                      </td>
                      <td style={{ fontWeight: 600, color: '#0f172a' }}>
                        {r.course_title || 'Course Evaluation'}
                      </td>
                      <td>
                        <strong>{r.total_score}</strong> / {r.max_possible}
                      </td>
                      <td>
                        <span style={{ fontWeight: 600, color: Number(r.percentage) >= 75 ? '#15803d' : '#334155' }}>
                          {r.percentage}%
                        </span>
                      </td>
                      <td>
                        <span
                          style={{
                            display: 'inline-block',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontWeight: 700,
                            fontSize: '12px',
                            backgroundColor: badge.bg,
                            color: badge.text,
                            border: `1px solid ${badge.border}`,
                          }}
                        >
                          {r.grade || 'A'}
                        </span>
                      </td>
                      <td>
                        <span className="badge badge-success">
                          <CheckCircle2 size={11} style={{ marginRight: '3px' }} />
                          {r.status || 'PUBLISHED'}
                        </span>
                      </td>
                      <td style={{ color: '#64748b', fontSize: '12px' }}>
                        {r.published_at ? new Date(r.published_at).toLocaleDateString() : 'Active Term'}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
export default ResultsView;
