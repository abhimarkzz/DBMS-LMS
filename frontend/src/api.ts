// API Client for Distributed LMS Platform

import { downloadProtectedMaterial } from './utils/materialViewer';

const API_BASE = (import.meta as any).env?.VITE_API_BASE || '/api';

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
    ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
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
    if (res.status === 401 && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/register')) {
      removeAuthToken();
      removeStoredUser();
    }
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

export function uploadCourseMaterialsWithProgress(
  courseId: number,
  formData: FormData,
  onProgress?: (percent: number) => void
): Promise<any[]> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}/courses/${courseId}/materials/upload`);
    const token = getAuthToken();
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          const percent = Math.round((e.loaded / e.total) * 100);
          onProgress(percent);
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          resolve(data);
        } catch {
          resolve([]);
        }
      } else {
        let msg = `Upload failed with status ${xhr.status}`;
        try {
          const err = JSON.parse(xhr.responseText);
          msg = err.detail || msg;
        } catch {}
        reject(new Error(msg));
      }
    };

    xhr.onerror = () => reject(new Error('Network error during file upload'));
    xhr.send(formData);
  });
}

export const api = {
  // Authentication
  login: (credentials: any) => request<any>('/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
  register: (data: any) => request<any>('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  getMe: () => request<any>('/auth/me'),
  changePassword: (data: { current_password: string; new_password: string }) => request<any>('/auth/change-password', { method: 'POST', body: JSON.stringify(data) }),

  // Courses
  getCourses: (includeAll: boolean = false) => request<any[]>(includeAll ? '/courses?include_all=true' : '/courses'),
  getCourseDetail: (id: number) => request<any>(`/courses/${id}`),
  createCourse: (data: any) => request<any>('/courses', { method: 'POST', body: JSON.stringify(data) }),
  updateCourse: (id: number, data: any) => request<any>(`/courses/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  updateCourseStatus: (id: number, status: string) => request<any>(`/courses/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  addCourseAnnouncement: (courseId: number, data: { title: string; content: string }) => request<any>(`/courses/${courseId}/announcements`, { method: 'POST', body: JSON.stringify(data) }),
  addCourseQuiz: (courseId: number, data: any) => request<any>(`/courses/${courseId}/quizzes`, { method: 'POST', body: JSON.stringify(data) }),
  enrollCourse: (courseId: number) => request<any>(`/courses/${courseId}/enroll`, { method: 'POST' }),
  getMyEnrollments: () => request<any[]>('/courses/my/enrollments'),
  addStudyMaterial: (courseId: number, data: any) => request<any>(`/courses/${courseId}/materials`, { method: 'POST', body: JSON.stringify(data) }),
  uploadCourseMaterials: (courseId: number, formData: FormData) => request<any[]>(`/courses/${courseId}/materials/upload`, { method: 'POST', body: formData }),
  getCourseMaterials: (courseId: number) => request<any[]>(`/courses/${courseId}/materials`),
  deleteCourseMaterial: (courseId: number, materialId: number) => request<any>(`/courses/${courseId}/materials/${materialId}`, { method: 'DELETE' }),
  reindexCourseMaterial: (courseId: number, materialId: number) => request<any>(`/courses/${courseId}/materials/${materialId}/reindex`, { method: 'POST' }),
  downloadCourseMaterial: (courseId: number, materialId: number, filename?: string) =>
    downloadProtectedMaterial(courseId, materialId, filename),

  // Dashboards (Role-Specific Real Database Computed)
  getStudentDashboard: () => request<any>('/dashboard/student'),
  getTeacherDashboard: () => request<any>('/dashboard/teacher'),
  getAdminDashboard: () => request<any>('/dashboard/admin'),

  // Assignments & Submissions
  getAssignments: (courseId?: number) => request<any[]>(courseId ? `/assignments?course_id=${courseId}` : '/assignments'),
  createAssignment: (data: any) => request<any>('/assignments', { method: 'POST', body: JSON.stringify(data) }),
  submitAssignment: (assignmentId: number, data: any) => request<any>(`/assignments/${assignmentId}/submit`, { method: 'POST', body: JSON.stringify(data) }),
  submitFileAssignment: async (assignmentId: number, file: File, notes?: string) => {
    const token = getAuthToken();
    const formData = new FormData();
    formData.append('file', file);
    if (notes) formData.append('notes', notes);

    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}/assignments/${assignmentId}/submit-file`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to upload file submission' }));
      throw new Error(err.detail || 'Failed to upload file submission');
    }
    return res.json();
  },
  getAssignmentSubmissions: (assignmentId: number) => request<any[]>(`/assignments/${assignmentId}/submissions`),
  getPendingSubmissions: () => request<any[]>('/assignments/submissions/pending'),
  gradeSubmission: (submissionId: number, data: any) => request<any>(`/assignments/submissions/${submissionId}/grade`, { method: 'POST', body: JSON.stringify(data) }),
  publishSubmissionGrade: (submissionId: number) => request<any>(`/assignments/submissions/${submissionId}/publish`, { method: 'POST' }),
  getSubmissionFileUrl: (submissionId: number) => `${API_BASE}/assignments/submissions/${submissionId}/file`,

  // Results & Advanced SQL Views (Phase 5 Gradebook & Academic Overview)
  getMyResults: () => request<any[]>('/results/my'),
  getProgressView: () => request<any[]>('/results/progress-view'),
  getCourseSummaryView: (courseId?: number) => request<any[]>(courseId ? `/results/course-summary-view?course_id=${courseId}` : '/results/course-summary-view'),
  getCourseLeaderboard: (courseId: number) => request<any[]>(`/results/course/${courseId}/leaderboard`),
  getAboveAverageStudents: (courseId: number) => request<any[]>(`/results/course/${courseId}/above-average`),
  calculateGradeProcedure: (studentId: number, courseId: number) => request<any>(`/results/calculate?student_id=${studentId}&course_id=${courseId}`, { method: 'POST' }),
  getStudentAcademicOverview: () => request<any>('/results/my/overview'),
  getStudentCourseBreakdown: (courseId: number) => request<any>(`/results/my/course/${courseId}/breakdown`),
  getCourseGradebook: (courseId: number) => request<any>(`/results/course/${courseId}/gradebook`),
  getAdminAcademicStats: () => request<any>('/results/admin/academic-stats'),

  // AI Smart Notes & Multi-Mode Research Engine (Course Notes, Web Research, Hybrid)
  searchNotes: (data: {
    query: string;
    mode?: string;
    depth?: string;
    freshness?: string;
    course_id?: number;
    top_k?: number;
  }) => request<any>('/search', { method: 'POST', body: JSON.stringify(data) }),
  uploadNotes: (data: any) => request<any>('/search/notes/upload', { method: 'POST', body: JSON.stringify(data) }),

  // Notifications & Announcements (MongoDB + Redis)
  getNotifications: (params?: { limit?: number; unread_only?: boolean; notif_type?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.append('limit', params.limit.toString());
    if (params?.unread_only) searchParams.append('unread_only', 'true');
    if (params?.notif_type) searchParams.append('notif_type', params.notif_type);
    const qs = searchParams.toString();
    return request<any[]>(`/notifications${qs ? `?${qs}` : ''}`);
  },
  getUnreadNotificationCount: () => request<{ unread_count: number }>('/notifications/unread-count'),
  markNotificationRead: (id: string) => request<any>(`/notifications/${id}/read`, { method: 'POST' }),
  markAllNotificationsRead: () => request<{ success: boolean; marked_count: number }>('/notifications/read-all', { method: 'POST' }),
  checkDueSoonNotifications: (hours: number = 24) => request<any>(`/notifications/check-due-soon?hours=${hours}`, { method: 'POST' }),
  getAnnouncements: (courseId: number) => request<any[]>(`/notifications/announcements/${courseId}`),
  createAnnouncement: (data: any) => request<any>('/notifications/announcements', { method: 'POST', body: JSON.stringify(data) }),

  // Admin & Observability
  getAdminOverview: () => request<any>('/admin/overview'),
  getHealth: () => request<any>('/admin/health'),
  getUsers: () => request<any[]>('/users'),
};
