// API Client for Distributed LMS Platform

const API_BASE = '/api';

export function getAuthToken(): string | null {
  return localStorage.getItem('lms_token');
}

export function setAuthToken(token: string) {
  localStorage.setItem('lms_token', token);
}

export function removeAuthToken() {
  localStorage.removeItem('lms_token');
}

export function getStoredUser(): any | null {
  const u = localStorage.getItem('lms_user');
  return u ? JSON.parse(u) : null;
}

export function setStoredUser(user: any) {
  localStorage.setItem('lms_user', JSON.stringify(user));
}

export function removeStoredUser() {
  localStorage.removeItem('lms_user');
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let errorMsg = 'An unexpected error occurred';
    try {
      const errData = await res.json();
      errorMsg = errData.detail || errData.error || errData.message || JSON.stringify(errData);
    } catch {
      errorMsg = `HTTP Error ${res.status}: ${res.statusText}`;
    }
    throw new Error(errorMsg);
  }

  return res.json();
}

export const api = {
  // Authentication
  login: (credentials: any) => request<any>('/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
  register: (data: any) => request<any>('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  getMe: () => request<any>('/auth/me'),

  // Courses
  getCourses: () => request<any[]>('/courses'),
  getCourseDetail: (id: number) => request<any>(`/courses/${id}`),
  createCourse: (data: any) => request<any>('/courses', { method: 'POST', body: JSON.stringify(data) }),
  enrollCourse: (courseId: number) => request<any>(`/courses/${courseId}/enroll`, { method: 'POST' }),
  getMyEnrollments: () => request<any[]>('/courses/my/enrollments'),
  addStudyMaterial: (courseId: number, data: any) => request<any>(`/courses/${courseId}/materials`, { method: 'POST', body: JSON.stringify(data) }),

  // Assignments & Submissions
  getAssignments: (courseId?: number) => request<any[]>(courseId ? `/assignments?course_id=${courseId}` : '/assignments'),
  createAssignment: (data: any) => request<any>('/assignments', { method: 'POST', body: JSON.stringify(data) }),
  submitAssignment: (assignmentId: number, data: any) => request<any>(`/assignments/${assignmentId}/submit`, { method: 'POST', body: JSON.stringify(data) }),
  getAssignmentSubmissions: (assignmentId: number) => request<any[]>(`/assignments/${assignmentId}/submissions`),
  gradeSubmission: (submissionId: number, data: any) => request<any>(`/assignments/submissions/${submissionId}/grade`, { method: 'POST', body: JSON.stringify(data) }),

  // Results & Advanced SQL Views
  getMyResults: () => request<any[]>('/results/my'),
  getProgressView: () => request<any[]>('/results/progress-view'),
  getCourseSummaryView: (courseId?: number) => request<any[]>(courseId ? `/results/course-summary-view?course_id=${courseId}` : '/results/course-summary-view'),
  getCourseLeaderboard: (courseId: number) => request<any[]>(`/results/course/${courseId}/leaderboard`),
  getAboveAverageStudents: (courseId: number) => request<any[]>(`/results/course/${courseId}/above-average`),
  calculateGradeProcedure: (studentId: number, courseId: number) => request<any>(`/results/calculate?student_id=${studentId}&course_id=${courseId}`, { method: 'POST' }),

  // AI Smart Notes Search (pgvector + Gemini RAG)
  searchNotes: (data: { query: string; course_id?: number; top_k?: number }) => request<any>('/search', { method: 'POST', body: JSON.stringify(data) }),
  uploadNotes: (data: any) => request<any>('/search/notes/upload', { method: 'POST', body: JSON.stringify(data) }),

  // Notifications & Announcements (MongoDB + Redis)
  getNotifications: () => request<any[]>('/notifications'),
  markNotificationRead: (id: string) => request<any>(`/notifications/${id}/read`, { method: 'POST' }),
  getAnnouncements: (courseId: number) => request<any[]>(`/notifications/announcements/${courseId}`),
  createAnnouncement: (data: any) => request<any>('/notifications/announcements', { method: 'POST', body: JSON.stringify(data) }),

  // Admin & Observability
  getAdminOverview: () => request<any>('/admin/overview'),
  getHealth: () => request<any>('/admin/health'),
  getUsers: () => request<any[]>('/users'),
};
