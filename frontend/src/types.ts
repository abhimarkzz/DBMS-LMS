export type UserRole = 'STUDENT' | 'TEACHER' | 'ADMIN';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  department?: string;
  academic_session?: string;
}

export interface Course {
  id: number;
  code: string;
  title: string;
  description: string;
  syllabus?: string;
  department?: string;
  credits?: number;
  level?: string;
  teacher_id: number;
  teacher_name?: string;
  is_published: boolean;
  is_enrolled?: boolean;
  enrollment_count?: number;
  created_at?: string;
}

export interface StudyMaterial {
  id: number;
  course_id: number;
  title: string;
  content: string;
  material_type: string;
  status: 'PROCESSING' | 'INDEXED' | 'FAILED';
  file_url?: string;
  chunk_count?: number;
  created_at?: string;
}

export interface MCQQuestion {
  id: string;
  question: string;
  options: string[];
  correct_answer: string;
}

export interface Assignment {
  id: number;
  course_id: number;
  course_code?: string;
  course_title?: string;
  title: string;
  description: string;
  max_score: number;
  assessment_type: 'DESCRIPTIVE' | 'MCQ' | 'FILE' | 'AUDIO';
  due_date?: string;
  assessment_config?: string;
  status: string;
  has_submitted?: boolean;
  my_score?: number;
  my_grade?: string;
}

export interface Submission {
  id: number;
  assignment_id: number;
  assignment_title?: string;
  course_code?: string;
  student_id: number;
  student_name?: string;
  student_email?: string;
  content: string;
  submission_type: string;
  status: 'SUBMITTED' | 'GRADED';
  score?: number;
  feedback?: string;
  submitted_at: string;
  graded_at?: string;
}

export interface Result {
  id: number;
  student_id: number;
  student_name?: string;
  course_id: number;
  course_code?: string;
  course_title?: string;
  total_score: number;
  max_possible: number;
  percentage: number;
  grade: string;
  status: string;
  published_at?: string;
  rank?: number;
}

export interface NotificationItem {
  id: string;
  user_id: number;
  title: string;
  message: string;
  notif_type: 'ASSIGNMENT' | 'GRADE' | 'ANNOUNCEMENT' | 'SYSTEM';
  is_read: boolean;
  created_at: string;
  related_entity_id?: string;
}

export type SearchMode = 'course_notes' | 'web_research' | 'hybrid' | 'COURSE_NOTES' | 'WEB_RESEARCH' | 'HYBRID';
export type ResearchDepth = 'quick' | 'standard' | 'deep' | 'QUICK' | 'STANDARD' | 'DEEP';
export type FreshnessPreference = 'any' | 'day' | 'week' | 'month' | 'year' | 'ANY' | 'DAY' | 'WEEK' | 'MONTH' | 'YEAR';

export interface WebSourceItem {
  title: string;
  url: string;
  domain: string;
  publication_date?: string | null;
  retrieval_date: string;
  snippet: string;
  source_type: 'OFFICIAL_DOC' | 'ACADEMIC' | 'WEB_GENERAL' | 'GOVERNMENT' | string;
  relevance_score: number;
}

export interface CourseSourceItem {
  chunk_id: number;
  material_id: number;
  material_title: string;
  course_id: number;
  course_title: string;
  chunk_index: number;
  excerpt: string;
  similarity_score: number;
  download_url?: string;
}

export interface CitationItem {
  source_id: string;
  source_title: string;
  source_url?: string | null;
  citation_text: string;
  source_type: 'COURSE_NOTE' | 'WEB' | string;
}

export interface AISearchResult {
  query: string;
  mode?: SearchMode;
  depth?: ResearchDepth;
  freshness?: FreshnessPreference;
  answer: string;
  direct_answer?: string | null;
  key_findings?: string[];
  grounded?: boolean;
  confidence_score?: number;
  sources?: Array<{
    chunk_id?: number;
    material_id?: number;
    title?: string;
    material_title?: string;
    course_title?: string;
    course_code?: string;
    similarity?: number;
    similarity_score?: number;
    snippet?: string;
    chunk_text?: string;
  }>;
  course_sources?: CourseSourceItem[];
  web_sources?: WebSourceItem[];
  citations?: CitationItem[];
  search_status?: 'SUCCESS' | 'NO_RESULTS' | 'PARTIAL_SUCCESS' | 'QUOTA_EXHAUSTED' | 'UNAVAILABLE' | string;
  limitations?: string | null;
  model_used?: string;
  latency_ms?: number | null;
  diagnostics?: Record<string, any>;
}
