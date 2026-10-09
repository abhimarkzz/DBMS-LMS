from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Numeric, DateTime, 
    ForeignKey, UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.database.postgres import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)  # STUDENT, TEACHER, ADMIN
    description = Column(String(255), nullable=True)

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    role = relationship("Role", back_populates="users")
    taught_courses = relationship("Course", back_populates="teacher")
    enrollments = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="student", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="student", cascade="all, delete-orphan")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # e.g. CS501
    title = Column(String(255), nullable=False)
    short_description = Column(String(300), nullable=True)
    description = Column(Text, nullable=True)
    department = Column(String(100), default="Computer Science & Engineering", nullable=False)
    level = Column(String(50), default="Graduate", nullable=False)
    academic_session = Column(String(50), default="Spring 2026", nullable=False)
    semester = Column(String(50), default="Term 2", nullable=False)
    credits = Column(Integer, default=4, nullable=False)
    prerequisites = Column(Text, nullable=True)
    learning_outcomes = Column(Text, nullable=True)
    syllabus = Column(Text, nullable=True)
    modules_outline = Column(Text, nullable=True)
    start_date = Column(String(50), default="2026-01-15", nullable=False)
    end_date = Column(String(50), default="2026-05-30", nullable=False)
    capacity = Column(Integer, default=50, nullable=False)
    status = Column(String(20), default="PUBLISHED", nullable=False)  # DRAFT, PUBLISHED, ARCHIVED
    teacher_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_published = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    teacher = relationship("User", back_populates="taught_courses")
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    materials = relationship("StudyMaterial", back_populates="course", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="course", cascade="all, delete-orphan")
    announcements = relationship("Announcement", back_populates="course", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="course", cascade="all, delete-orphan")


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    enrolled_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)  # ACTIVE, DROPPED, COMPLETED

    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_student_course_enrollment"),
        Index("idx_enrollment_student_status", "student_id", "status"),
    )

    student = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")


class StudyMaterial(Base):
    __tablename__ = "study_materials"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False, default="")
    material_type = Column(String(50), default="NOTES", nullable=False)  # PDF, DOCX, PPTX, TXT, MD, NOTES
    original_filename = Column(String(255), nullable=True)
    file_type = Column(String(50), nullable=True)  # PDF, DOCX, PPTX, TXT, MD, TEXT
    file_size = Column(Integer, default=0, nullable=False)
    file_storage_id = Column(String(255), nullable=True)
    file_url = Column(String(500), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), default="INDEXED", nullable=False)  # PROCESSING, INDEXED, FAILED
    chunk_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    course = relationship("Course", back_populates="materials")
    uploader = relationship("User")
    chunks = relationship("NoteChunk", back_populates="material", cascade="all, delete-orphan")

    @property
    def uploader_name(self) -> Optional[str]:
        return self.uploader.full_name if self.uploader else None


class NoteChunk(Base):
    __tablename__ = "note_chunks"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("study_materials.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=True)
    chunk_metadata = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_note_chunks_course_mat", "course_id", "material_id"),
    )

    material = relationship("StudyMaterial", back_populates="chunks")


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    instructions = Column(Text, nullable=True)
    max_score = Column(Numeric(5, 2), default=100.0, nullable=False)
    assessment_type = Column(String(50), default="DESCRIPTIVE", nullable=False)  # DESCRIPTIVE, MCQ, FILE, AUDIO
    due_date = Column(DateTime, nullable=True)
    start_date = Column(DateTime, nullable=True)
    due_time = Column(String(20), nullable=True)
    attempt_limit = Column(Integer, default=1, nullable=False)
    late_allowed = Column(Boolean, default=True, nullable=False)
    status = Column(String(50), default="PUBLISHED", nullable=False)  # DRAFT, PUBLISHED, ARCHIVED
    attachment_url = Column(String(500), nullable=True)
    assessment_config = Column(Text, nullable=True)  # JSON encoded configuration (rubric, mcq questions, file/audio specs)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("max_score > 0", name="chk_assignment_max_score_positive"),
    )

    course = relationship("Course", back_populates="assignments")
    submissions = relationship("Submission", back_populates="assignment", cascade="all, delete-orphan")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False, default="")
    file_url = Column(String(500), nullable=True)
    submission_type = Column(String(50), default="TEXT", nullable=False)  # TEXT, MCQ, FILE, AUDIO
    file_storage_id = Column(String(255), nullable=True)
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, default=0, nullable=False)
    mcq_answers = Column(Text, nullable=True)  # JSON of student selections
    rubric_evaluation = Column(Text, nullable=True)  # JSON of criteria marks & comments
    attempt_number = Column(Integer, default=1, nullable=False)
    is_late = Column(Boolean, default=False, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), default="SUBMITTED", nullable=False)  # SUBMITTED, GRADED, LATE, EVALUATED
    grade_status = Column(String(50), default="PUBLISHED", nullable=False)  # DRAFT, PUBLISHED
    score = Column(Numeric(5, 2), nullable=True)
    feedback = Column(Text, nullable=True)
    graded_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("assignment_id", "student_id", name="uq_assignment_student_submission"),
        CheckConstraint("score IS NULL OR score >= 0", name="chk_submission_score_non_negative"),
        Index("idx_submission_student_assignment", "student_id", "assignment_id"),
        Index("idx_submission_grade_status", "assignment_id", "grade_status"),
    )

    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("User", back_populates="submissions")


class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    total_score = Column(Numeric(7, 2), default=0.0, nullable=False)
    max_possible = Column(Numeric(7, 2), default=100.0, nullable=False)
    percentage = Column(Numeric(5, 2), default=0.0, nullable=False)
    grade = Column(String(5), default="N/A", nullable=False)  # A+, A, B, C, D, F
    status = Column(String(50), default="PUBLISHED", nullable=False)
    published_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_student_course_result"),
        Index("idx_result_course_pct", "course_id", "percentage"),
    )

    student = relationship("User", back_populates="results")
    course = relationship("Course", back_populates="results")


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    course = relationship("Course", back_populates="announcements")
    author = relationship("User")


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, default=30, nullable=False)
    total_points = Column(Integer, default=100, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    course = relationship("Course", back_populates="quizzes")
