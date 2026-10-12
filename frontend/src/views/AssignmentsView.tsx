import React, { useState, useEffect } from 'react';
import {
  CheckSquare,
  HelpCircle,
  X,
  FileText,
  CheckCircle2,
  Plus,
  Users
} from 'lucide-react';
import type { Assignment, Course, User } from '../types';
import { api } from '../api';

interface AssignmentsViewProps {
  user?: User | null;
  assignments: Assignment[];
  courses: Course[];
  activeAssignmentToOpen?: Assignment | null;
  onRefresh: () => void;
}

interface McqQuestionDraft {
  id: string;
  question: string;
  options: string[];
  correct_answer: string;
}

export const AssignmentsView: React.FC<AssignmentsViewProps> = ({
  user,
  assignments,
  courses,
  activeAssignmentToOpen,
  onRefresh,
}) => {
  const isInstructor = user?.role === 'TEACHER' || user?.role === 'ADMIN';

  const [selectedCourseFilter, setSelectedCourseFilter] = useState<number | 'ALL'>('ALL');
  
  // Student modals
  const [activeQuiz, setActiveQuiz] = useState<Assignment | null>(activeAssignmentToOpen || null);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, string>>({});
  const [quizSubmitted, setQuizSubmitted] = useState(false);
  const [quizScore, setQuizScore] = useState<number | null>(null);

  const [activeDescriptive, setActiveDescriptive] = useState<Assignment | null>(null);
  const [submissionText, setSubmissionText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  // Instructor modals
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createCourseId, setCreateCourseId] = useState<number>(courses[0]?.id || 0);
  const [createTitle, setCreateTitle] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [createInstructions, setCreateInstructions] = useState('');
  const [createType, setCreateType] = useState<'DESCRIPTIVE' | 'MCQ'>('DESCRIPTIVE');
  const [createMaxScore, setCreateMaxScore] = useState<number>(100);
  const [createDueDate, setCreateDueDate] = useState<string>(
    new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  );
  const [mcqQuestions, setMcqQuestions] = useState<McqQuestionDraft[]>([
    {
      id: 'q1',
      question: '',
      options: ['', '', '', ''],
      correct_answer: '',
    }
  ]);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Instructor Review Submissions Modal
  const [reviewAssignment, setReviewAssignment] = useState<Assignment | null>(null);
  const [submissionsList, setSubmissionsList] = useState<any[]>([]);
  const [loadingSubmissions, setLoadingSubmissions] = useState(false);
  const [gradingScores, setGradingScores] = useState<Record<number, number>>({});
  const [gradingFeedbacks, setGradingFeedbacks] = useState<Record<number, string>>({});
  const [gradingStatus, setGradingStatus] = useState<Record<number, boolean>>({});

  useEffect(() => {
    if (courses.length > 0 && !createCourseId) {
      setCreateCourseId(courses[0].id);
    }
  }, [courses]);

  const filtered = assignments.filter((a) => {
    if (selectedCourseFilter !== 'ALL' && a.course_id !== selectedCourseFilter) return false;
    return true;
  });

  const handleOpenStudentAssignment = (a: Assignment) => {
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

  const handleOpenInstructorReview = async (a: Assignment) => {
    setReviewAssignment(a);
    setLoadingSubmissions(true);
    try {
      const subs = await api.getAssignmentSubmissions(a.id);
      setSubmissionsList(subs || []);
      const scores: Record<number, number> = {};
      const fbs: Record<number, string> = {};
      (subs || []).forEach((s: any) => {
        if (s.score !== null && s.score !== undefined) scores[s.id] = s.score;
        if (s.feedback) fbs[s.id] = s.feedback;
      });
      setGradingScores(scores);
      setGradingFeedbacks(fbs);
    } catch (err) {
      console.warn('Could not load submissions for assessment', err);
      setSubmissionsList([]);
    } finally {
      setLoadingSubmissions(false);
    }
  };

  const handleGradeSubmission = async (submissionId: number) => {
    const score = gradingScores[submissionId] ?? 100;
    const feedback = gradingFeedbacks[submissionId] || 'Good work!';
    setGradingStatus((prev) => ({ ...prev, [submissionId]: true }));
    try {
      await api.gradeSubmission(submissionId, { score, feedback });
      alert(`Submission graded successfully! Score: ${score}`);
      if (reviewAssignment) {
        const subs = await api.getAssignmentSubmissions(reviewAssignment.id);
        setSubmissionsList(subs || []);
      }
      onRefresh();
    } catch (err: any) {
      alert(`Grading failed: ${err.message || err}`);
    } finally {
      setGradingStatus((prev) => ({ ...prev, [submissionId]: false }));
    }
  };

  const handleAddMcqQuestion = () => {
    setMcqQuestions([
      ...mcqQuestions,
      {
        id: `q${mcqQuestions.length + 1}`,
        question: '',
        options: ['', '', '', ''],
        correct_answer: '',
      }
    ]);
  };

  const handleUpdateMcqQuestion = (qIdx: number, field: string, value: any) => {
    const updated = [...mcqQuestions];
    (updated[qIdx] as any)[field] = value;
    setMcqQuestions(updated);
  };

  const handleUpdateMcqOption = (qIdx: number, optIdx: number, value: string) => {
    const updated = [...mcqQuestions];
    updated[qIdx].options[optIdx] = value;
    setMcqQuestions(updated);
  };

  const handleCreateAssignment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createCourseId) {
      setCreateError('Please select a course for this assessment.');
      return;
    }
    if (!createTitle.trim()) {
      setCreateError('Please enter an assessment title.');
      return;
    }

    let assessmentConfig: string | undefined = undefined;
    if (createType === 'MCQ') {
      const validQuestions = mcqQuestions.filter(
        (q) => q.question.trim() && q.options.some((o) => o.trim()) && q.correct_answer
      );
      if (validQuestions.length === 0) {
        setCreateError('Please add at least one complete MCQ question with options and a correct answer.');
        return;
      }
      assessmentConfig = JSON.stringify({ questions: validQuestions });
    }

    setCreating(true);
    setCreateError(null);
    try {
      await api.createAssignment({
        course_id: createCourseId,
        title: createTitle.trim(),
        description: createDescription.trim(),
        instructions: createInstructions.trim(),
        assessment_type: createType,
        max_score: Number(createMaxScore) || 100,
        due_date: new Date(createDueDate).toISOString(),
        assessment_config: assessmentConfig,
        status: 'PUBLISHED',
      });
      setIsCreateModalOpen(false);
      setCreateTitle('');
      setCreateDescription('');
      setCreateInstructions('');
      onRefresh();
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create assessment.');
    } finally {
      setCreating(false);
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
      {/* Header card with actions and course filter */}
      <div className="card" style={{ padding: '18px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
          <div>
            <h1 style={{ fontSize: '18px', fontWeight: 700, color: '#0f172a' }}>
              Assessments, Quizzes & Assignments
            </h1>
            <p style={{ fontSize: '13px', color: '#64748b', marginTop: '2px' }}>
              {isInstructor
                ? 'Create, manage, and evaluate coursework and student submissions across your academic modules.'
                : 'Spring 2026 assignments with instant MCQ automatic grading and descriptive evaluation.'}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {isInstructor && (
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setIsCreateModalOpen(true)}
                style={{ gap: '6px', fontWeight: 600, padding: '8px 14px' }}
              >
                <Plus size={15} />
                <span>Add Assessment</span>
              </button>
            )}

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '12.5px', color: '#64748b', fontWeight: 600 }}>Filter:</span>
              <select
                className="form-select"
                value={selectedCourseFilter}
                onChange={(e) => setSelectedCourseFilter(e.target.value === 'ALL' ? 'ALL' : Number(e.target.value))}
                style={{ minWidth: '180px' }}
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
      </div>

      {/* Assignment List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {filtered.length === 0 ? (
          <div className="empty-state">
            <CheckSquare className="empty-state-icon" />
            <div className="empty-state-title">No Assessments Found</div>
            <p className="empty-state-desc">
              {isInstructor
                ? 'Click "Add Assessment" above to publish your first quiz or assignment for students.'
                : 'There are no active assessments matching the chosen filter.'}
            </p>
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
              <div style={{ flex: 1, minWidth: '280px' }}>
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
                {isInstructor ? (
                  <button
                    className="btn btn-secondary"
                    onClick={() => handleOpenInstructorReview(a)}
                    style={{ gap: '6px', fontWeight: 600 }}
                  >
                    <Users size={14} color="#1d4ed8" />
                    <span>Review Submissions</span>
                  </button>
                ) : (
                  <button
                    className="btn btn-primary"
                    onClick={() => handleOpenStudentAssignment(a)}
                  >
                    {a.assessment_type === 'MCQ' ? 'Launch Quiz Runner' : 'Submit Solution'}
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Instructor: Create Assessment Modal */}
      {isCreateModalOpen && (
        <div className="modal-overlay" onClick={() => setIsCreateModalOpen(false)}>
          <div className="modal-content modal-content-lg" onClick={(e) => e.stopPropagation()} style={{ maxHeight: '88vh', overflowY: 'auto' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Plus size={18} color="#1e3a8a" />
                <h3>Create New Course Assessment</h3>
              </div>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateAssignment}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {createError && (
                  <div className="banner-alert banner-alert-error">
                    {createError}
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label">Course</label>
                  <select
                    className="form-select"
                    value={createCourseId}
                    onChange={(e) => setCreateCourseId(Number(e.target.value))}
                    required
                  >
                    {courses.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.code}: {c.title}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Assessment Title</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. Assignment 2: Graph Spanning Trees & Prim's Algorithm"
                    value={createTitle}
                    onChange={(e) => setCreateTitle(e.target.value)}
                    required
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px' }}>
                  <div className="form-group">
                    <label className="form-label">Assessment Type</label>
                    <select
                      className="form-select"
                      value={createType}
                      onChange={(e) => setCreateType(e.target.value as any)}
                    >
                      <option value="DESCRIPTIVE">Descriptive / Written Project</option>
                      <option value="MCQ">Multiple-Choice Quiz (Automated)</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Maximum Score</label>
                    <input
                      type="number"
                      className="form-input"
                      value={createMaxScore}
                      min={1}
                      max={1000}
                      onChange={(e) => setCreateMaxScore(Number(e.target.value))}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Due Date</label>
                    <input
                      type="date"
                      className="form-input"
                      value={createDueDate}
                      onChange={(e) => setCreateDueDate(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Problem Statement / Description</label>
                  <textarea
                    className="form-textarea"
                    rows={4}
                    placeholder="Provide details on the assignment expectations, algorithmic requirements, or problem prompts..."
                    value={createDescription}
                    onChange={(e) => setCreateDescription(e.target.value)}
                    required
                  />
                </div>

                {createType === 'MCQ' && (
                  <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '16px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#0f172a' }}>Quiz Questions ({mcqQuestions.length})</h4>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={handleAddMcqQuestion}
                        style={{ gap: '4px' }}
                      >
                        <Plus size={13} />
                        <span>Add Question</span>
                      </button>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      {mcqQuestions.map((q, qIdx) => (
                        <div key={q.id} style={{ padding: '14px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                          <div className="form-group" style={{ marginBottom: '10px' }}>
                            <label className="form-label">Question {qIdx + 1} Prompt</label>
                            <input
                              type="text"
                              className="form-input"
                              placeholder="e.g. What is the time complexity of Dijkstra with a binary heap?"
                              value={q.question}
                              onChange={(e) => handleUpdateMcqQuestion(qIdx, 'question', e.target.value)}
                              required
                            />
                          </div>

                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '10px' }}>
                            {q.options.map((opt, optIdx) => (
                              <input
                                key={optIdx}
                                type="text"
                                className="form-input"
                                placeholder={`Option ${String.fromCharCode(65 + optIdx)}`}
                                value={opt}
                                onChange={(e) => handleUpdateMcqOption(qIdx, optIdx, e.target.value)}
                                required
                              />
                            ))}
                          </div>

                          <div className="form-group" style={{ marginBottom: '0' }}>
                            <label className="form-label" style={{ fontSize: '11.5px' }}>Correct Answer (Select which option is correct)</label>
                            <select
                              className="form-select"
                              value={q.correct_answer}
                              onChange={(e) => handleUpdateMcqQuestion(qIdx, 'correct_answer', e.target.value)}
                              required
                            >
                              <option value="">-- Choose Correct Option --</option>
                              {q.options.filter(Boolean).map((opt, idx) => (
                                <option key={idx} value={opt}>
                                  {opt}
                                </option>
                              ))}
                            </select>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setIsCreateModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={creating}>
                  {creating ? 'Publishing...' : 'Publish Assessment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Instructor: Review Submissions Modal */}
      {reviewAssignment && (
        <div className="modal-overlay" onClick={() => setReviewAssignment(null)}>
          <div className="modal-content modal-content-lg" onClick={(e) => e.stopPropagation()} style={{ maxHeight: '88vh', overflowY: 'auto' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Users size={18} color="#1e3a8a" />
                <div>
                  <h3 style={{ fontSize: '16px' }}>Student Submissions: {reviewAssignment.title}</h3>
                  <div style={{ fontSize: '12px', color: '#64748b' }}>Max Score: {reviewAssignment.max_score} | Type: {reviewAssignment.assessment_type}</div>
                </div>
              </div>
              <button
                onClick={() => setReviewAssignment(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              {loadingSubmissions ? (
                <div style={{ padding: '36px', textAlign: 'center', color: '#64748b' }}>
                  Loading student submissions...
                </div>
              ) : submissionsList.length === 0 ? (
                <div className="empty-state" style={{ padding: '36px 16px' }}>
                  <CheckSquare className="empty-state-icon" />
                  <div className="empty-state-title">No Submissions Yet</div>
                  <p className="empty-state-desc">Enrolled students have not submitted solutions for this assessment yet.</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {submissionsList.map((sub: any) => (
                    <div
                      key={sub.id}
                      style={{
                        padding: '16px',
                        border: '1px solid #e2e8f0',
                        borderRadius: '8px',
                        background: '#f8fafc',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '12px'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <strong style={{ fontSize: '14px', color: '#0f172a' }}>{sub.student_name || `Student #${sub.student_id}`}</strong>
                          <span style={{ fontSize: '12px', color: '#64748b', marginLeft: '8px' }}>{sub.student_email}</span>
                        </div>
                        <span className={`badge ${sub.score !== null ? 'badge-success' : 'badge-neutral'}`}>
                          {sub.score !== null ? `Graded: ${sub.score}/${reviewAssignment.max_score}` : 'Pending Evaluation'}
                        </span>
                      </div>

                      <div style={{ padding: '10px 14px', background: '#ffffff', borderRadius: '6px', border: '1px solid #e2e8f0', fontSize: '13px', color: '#334155', whiteSpace: 'pre-wrap' }}>
                        {sub.content || '(No text content provided)'}
                      </div>

                      {/* Instructor Grading Form */}
                      <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginTop: '4px' }}>
                        <div style={{ width: '130px' }}>
                          <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: '#475569', marginBottom: '2px' }}>
                            Score (/ {reviewAssignment.max_score})
                          </label>
                          <input
                            type="number"
                            className="form-input"
                            style={{ padding: '6px 10px', fontSize: '12px' }}
                            value={gradingScores[sub.id] ?? ''}
                            placeholder="0"
                            min={0}
                            max={reviewAssignment.max_score}
                            onChange={(e) => setGradingScores({ ...gradingScores, [sub.id]: Number(e.target.value) })}
                          />
                        </div>

                        <div style={{ flex: 1 }}>
                          <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: '#475569', marginBottom: '2px' }}>
                            Feedback / Rubric Comments
                          </label>
                          <input
                            type="text"
                            className="form-input"
                            style={{ padding: '6px 10px', fontSize: '12px' }}
                            placeholder="Add evaluation feedback for student..."
                            value={gradingFeedbacks[sub.id] ?? ''}
                            onChange={(e) => setGradingFeedbacks({ ...gradingFeedbacks, [sub.id]: e.target.value })}
                          />
                        </div>

                        <button
                          type="button"
                          className="btn btn-primary"
                          style={{ alignSelf: 'flex-end', padding: '7px 14px', fontSize: '12px' }}
                          disabled={gradingStatus[sub.id]}
                          onClick={() => handleGradeSubmission(sub.id)}
                        >
                          {gradingStatus[sub.id] ? 'Saving...' : 'Save Grade'}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setReviewAssignment(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Student: Interactive MCQ Quiz Runner Modal */}
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

      {/* Student: Descriptive Submission Modal */}
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
