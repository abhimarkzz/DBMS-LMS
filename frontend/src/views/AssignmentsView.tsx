import React, { useState } from 'react';
import {
  CheckSquare,
  HelpCircle,
  X,
  FileText,
  CheckCircle2
} from 'lucide-react';
import type { Assignment, Course } from '../types';
import { api } from '../api';

interface AssignmentsViewProps {
  assignments: Assignment[];
  courses: Course[];
  activeAssignmentToOpen?: Assignment | null;
  onRefresh: () => void;
}

export const AssignmentsView: React.FC<AssignmentsViewProps> = ({
  assignments,
  courses,
  activeAssignmentToOpen,
  onRefresh,
}) => {
  const [selectedCourseFilter, setSelectedCourseFilter] = useState<number | 'ALL'>('ALL');
  const [activeQuiz, setActiveQuiz] = useState<Assignment | null>(activeAssignmentToOpen || null);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, string>>({});
  const [quizSubmitted, setQuizSubmitted] = useState(false);
  const [quizScore, setQuizScore] = useState<number | null>(null);

  // Descriptive modal state
  const [activeDescriptive, setActiveDescriptive] = useState<Assignment | null>(null);
  const [submissionText, setSubmissionText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  const filtered = assignments.filter((a) => {
    if (selectedCourseFilter !== 'ALL' && a.course_id !== selectedCourseFilter) return false;
    return true;
  });

  const handleOpenAssignment = (a: Assignment) => {
    if (a.assessment_type === 'MCQ') {
      setActiveQuiz(a);
      setSelectedAnswers({});
      setQuizSubmitted(false);
      setQuizScore(null);
    } else {
      setActiveDescriptive(a);
      setSubmissionText('');
      setSubmitSuccess(false);
    }
  };

  const handleQuizSubmit = async () => {
    if (!activeQuiz) return;
    let questions = [];
    try {
      const cfg = activeQuiz.assessment_config ? JSON.parse(activeQuiz.assessment_config) : null;
      questions = cfg?.questions || [];
    } catch {
      questions = [];
    }

    let correctCount = 0;
    questions.forEach((q: any) => {
      if (selectedAnswers[q.id] === q.correct_answer) {
        correctCount += 1;
      }
    });

    const score = questions.length > 0 ? (correctCount / questions.length) * activeQuiz.max_score : 100;
    setQuizScore(score);
    setQuizSubmitted(true);

    try {
      await api.submitAssignment(activeQuiz.id, {
        content: `MCQ Quiz completed with score ${score}/${activeQuiz.max_score}`,
        submission_type: 'MCQ',
        mcq_answers: JSON.stringify(selectedAnswers),
      });
      onRefresh();
    } catch (e) {
      console.warn('Quiz submission recorded locally', e);
    }
  };

  const handleDescriptiveSubmit = async () => {
    if (!activeDescriptive || !submissionText.trim()) return;
    setSubmitting(true);
    try {
      await api.submitAssignment(activeDescriptive.id, {
        content: submissionText,
        submission_type: 'TEXT',
      });
      setSubmitSuccess(true);
      setTimeout(() => {
        setActiveDescriptive(null);
        onRefresh();
      }, 1500);
    } catch (e: any) {
      alert(e.message || 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header card with course filter */}
      <div className="card" style={{ padding: '18px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
          <div>
            <h1 style={{ fontSize: '18px', fontWeight: 700, color: '#0f172a' }}>
              Assessments, Quizzes & Assignments
            </h1>
            <p style={{ fontSize: '13px', color: '#64748b', marginTop: '2px' }}>
              Spring 2026 assignments with instant MCQ automatic grading and descriptive evaluation.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '12.5px', color: '#64748b', fontWeight: 600 }}>Filter Course:</span>
            <select
              className="form-select"
              value={selectedCourseFilter}
              onChange={(e) => setSelectedCourseFilter(e.target.value === 'ALL' ? 'ALL' : Number(e.target.value))}
            >
              <option value="ALL">All Enrolled Courses</option>
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code}: {c.title}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Assignment List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {filtered.length === 0 ? (
          <div className="empty-state">
            <CheckSquare className="empty-state-icon" />
            <div className="empty-state-title">No Assignments Found</div>
            <p className="empty-state-desc">There are no assessments matching the chosen filter.</p>
          </div>
        ) : (
          filtered.map((a) => (
            <div
              key={a.id}
              className="card"
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '16px',
                padding: '20px',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <span className="badge badge-primary">{a.assessment_type}</span>
                  <span className="badge badge-neutral">Max Score: {a.max_score}</span>
                  <span className="badge badge-success">Open for Submission</span>
                </div>
                <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#0f172a' }}>
                  {a.title}
                </h3>
                <p style={{ fontSize: '13px', color: '#475569', marginTop: '4px', maxWidth: '750px', lineHeight: 1.5 }}>
                  {a.description}
                </p>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <button
                  className="btn btn-primary"
                  onClick={() => handleOpenAssignment(a)}
                >
                  {a.assessment_type === 'MCQ' ? 'Launch Quiz Runner' : 'Submit Solution'}
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Interactive MCQ Quiz Runner Modal */}
      {activeQuiz && (
        <div className="modal-overlay" onClick={() => setActiveQuiz(null)}>
          <div className="modal-content modal-content-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <HelpCircle size={18} color="#1e3a8a" />
                <h3>{activeQuiz.title} - Interactive Quiz</h3>
              </div>
              <button
                onClick={() => setActiveQuiz(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body" style={{ maxHeight: '65vh', overflowY: 'auto' }}>
              {(() => {
                let questions = [];
                try {
                  const cfg = activeQuiz.assessment_config ? JSON.parse(activeQuiz.assessment_config) : null;
                  questions = cfg?.questions || [];
                } catch {
                  questions = [];
                }

                if (questions.length === 0) {
                  return (
                    <div style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>
                      No multiple-choice questions configured for this quiz.
                    </div>
                  );
                }

                return (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    {questions.map((q: any, qIdx: number) => (
                      <div key={q.id || qIdx} className="mcq-question-card">
                        <div style={{ fontWeight: 600, fontSize: '14px', color: '#0f172a', marginBottom: '10px' }}>
                          Question {qIdx + 1}: {q.question}
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {q.options.map((opt: string, optIdx: number) => {
                            const isSelected = selectedAnswers[q.id] === opt;
                            const isCorrect = q.correct_answer === opt;

                            let optClass = 'mcq-option-row';
                            if (quizSubmitted) {
                              if (isCorrect) optClass += ' mcq-option-correct';
                              else if (isSelected && !isCorrect) optClass += ' mcq-option-incorrect';
                            }

                            return (
                              <label
                                key={optIdx}
                                className={optClass}
                                style={{
                                  cursor: quizSubmitted ? 'default' : 'pointer',
                                  backgroundColor: isSelected && !quizSubmitted ? '#eff6ff' : undefined,
                                }}
                              >
                                <input
                                  type="radio"
                                  name={`q_${q.id}`}
                                  disabled={quizSubmitted}
                                  checked={isSelected}
                                  onChange={() => setSelectedAnswers({ ...selectedAnswers, [q.id]: opt })}
                                />
                                <span style={{ fontSize: '13px', color: '#1e293b' }}>{opt}</span>
                              </label>
                            );
                          })}
                        </div>
                      </div>
                    ))}

                    {quizSubmitted && quizScore !== null && (
                      <div
                        style={{
                          padding: '16px',
                          backgroundColor: '#f0fdf4',
                          border: '1px solid #bbf7d0',
                          borderRadius: '6px',
                          textAlign: 'center',
                        }}
                      >
                        <div style={{ fontSize: '16px', fontWeight: 700, color: '#15803d' }}>
                          Quiz Result: {quizScore.toFixed(0)} / {activeQuiz.max_score} Marks
                        </div>
                        <div style={{ fontSize: '12.5px', color: '#166534', marginTop: '4px' }}>
                          Score automatically saved and evaluated by the database trigger!
                        </div>
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>

            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setActiveQuiz(null)}>
                {quizSubmitted ? 'Close' : 'Cancel'}
              </button>

              {!quizSubmitted && (
                <button className="btn btn-primary" onClick={handleQuizSubmit}>
                  Submit Quiz for Automatic Grading
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Descriptive Submission Modal */}
      {activeDescriptive && (
        <div className="modal-overlay" onClick={() => setActiveDescriptive(null)}>
          <div className="modal-content modal-content-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileText size={18} color="#1e3a8a" />
                <h3>{activeDescriptive.title} - Submit Solution</h3>
              </div>
              <button
                onClick={() => setActiveDescriptive(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              {submitSuccess ? (
                <div style={{ padding: '36px', textAlign: 'center' }}>
                  <CheckCircle2 size={44} color="#15803d" style={{ margin: '0 auto 12px auto' }} />
                  <h3 style={{ fontSize: '17px', fontWeight: 700, color: '#0f172a' }}>
                    Solution Submitted Successfully!
                  </h3>
                  <p style={{ fontSize: '13px', color: '#64748b', marginTop: '4px' }}>
                    Your submission has been queued for faculty evaluation.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div style={{ padding: '12px', backgroundColor: '#f8fafc', borderRadius: '6px', border: '1px solid #e2e8f0', fontSize: '13px', color: '#475569' }}>
                    <strong>Prompt:</strong> {activeDescriptive.description}
                  </div>

                  <div className="form-group">
                    <label className="form-label">Written Solution / Implementation Notes:</label>
                    <textarea
                      className="form-textarea"
                      rows={8}
                      placeholder="Enter your detailed response, algorithm complexity analysis, or code notes here..."
                      value={submissionText}
                      onChange={(e) => setSubmissionText(e.target.value)}
                    />
                  </div>
                </div>
              )}
            </div>

            {!submitSuccess && (
              <div className="modal-footer">
                <button className="btn btn-secondary" onClick={() => setActiveDescriptive(null)}>
                  Cancel
                </button>
                <button
                  className="btn btn-primary"
                  onClick={handleDescriptiveSubmit}
                  disabled={submitting || !submissionText.trim()}
                >
                  {submitting ? 'Submitting...' : 'Confirm Submission'}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
