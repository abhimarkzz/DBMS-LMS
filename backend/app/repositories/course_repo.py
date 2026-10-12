from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.models.sql_models import Course, Enrollment, StudyMaterial, User, Announcement, Quiz, Assignment


class CourseRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_course_by_id(self, course_id: int) -> Optional[Course]:
        return self.db.query(Course).options(
            joinedload(Course.teacher),
            joinedload(Course.materials),
            joinedload(Course.announcements),
            joinedload(Course.quizzes),
            joinedload(Course.assignments),
            joinedload(Course.enrollments).joinedload(Enrollment.student)
        ).filter(Course.id == course_id).first()

    def get_course_by_code(self, code: str) -> Optional[Course]:
        return self.db.query(Course).filter(Course.code == code.upper().strip()).first()

    def create_course(
        self,
        code: str,
        title: str,
        short_description: Optional[str] = None,
        description: Optional[str] = None,
        department: str = "Computer Science & Engineering",
        level: str = "Graduate",
        academic_session: str = "Spring 2026",
        semester: str = "Term 2",
        credits: int = 4,
        prerequisites: Optional[str] = None,
        learning_outcomes: Optional[str] = None,
        syllabus: Optional[str] = None,
        modules_outline: Optional[str] = None,
        start_date: str = "2026-01-15",
        end_date: str = "2026-05-30",
        capacity: int = 50,
        status: str = "PUBLISHED",
        is_published: bool = True,
        teacher_id: int = 1
    ) -> Course:
        course = Course(
            code=code.upper().strip(),
            title=title.strip(),
            short_description=short_description,
            description=description,
            department=department,
            level=level,
            academic_session=academic_session,
            semester=semester,
            credits=credits,
            prerequisites=prerequisites,
            learning_outcomes=learning_outcomes,
            syllabus=syllabus,
            modules_outline=modules_outline,
            start_date=start_date,
            end_date=end_date,
            capacity=capacity,
            status=status,
            teacher_id=teacher_id,
            is_published=is_published
        )
        self.db.add(course)
        self.db.commit()
        self.db.refresh(course)
        return course

    def update_course(self, course_id: int, **kwargs) -> Optional[Course]:
        course = self.db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return None
        for key, val in kwargs.items():
            if val is not None and hasattr(course, key):
                setattr(course, key, val)
        if "status" in kwargs and kwargs["status"]:
            course.is_published = (kwargs["status"].upper() == "PUBLISHED")
        self.db.commit()
        self.db.refresh(course)
        return course

    def update_course_status(self, course_id: int, status_str: str) -> Optional[Course]:
        course = self.db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return None
        course.status = status_str.upper()
        course.is_published = (status_str.upper() == "PUBLISHED")
        self.db.commit()
        self.db.refresh(course)
        return course

    def list_courses(self, student_id: Optional[int] = None, teacher_id: Optional[int] = None, include_all: bool = False) -> List[Dict[str, Any]]:
        """List courses with instructor, department, academic metadata, and enrollment stats."""
        query = self.db.query(
            Course.id,
            Course.code,
            Course.title,
            Course.short_description,
            Course.description,
            Course.department,
            Course.level,
            Course.academic_session,
            Course.semester,
            Course.credits,
            Course.prerequisites,
            Course.learning_outcomes,
            Course.syllabus,
            Course.modules_outline,
            Course.start_date,
            Course.end_date,
            Course.capacity,
            Course.status,
            Course.teacher_id,
            User.full_name.label("teacher_name"),
            Course.is_published,
            Course.created_at,
            func.count(Enrollment.id).label("enrolled_count")
        ).join(User, Course.teacher_id == User.id)\
         .outerjoin(Enrollment, Course.id == Enrollment.course_id)

        if not include_all:
            query = query.filter(Course.is_published == True)
        if teacher_id is not None:
            query = query.filter(Course.teacher_id == teacher_id)

        query = query.group_by(Course.id, User.full_name).order_by(Course.code)
        results = query.all()

        enrolled_course_ids = set()
        if student_id:
            enrolled = self.db.query(Enrollment.course_id).filter(
                Enrollment.student_id == student_id,
                Enrollment.status == "ACTIVE"
            ).all()
            enrolled_course_ids = {row[0] for row in enrolled}

        output = []
        for r in results:
            output.append({
                "id": r.id,
                "code": r.code,
                "title": r.title,
                "short_description": r.short_description,
                "description": r.description,
                "department": r.department,
                "level": r.level,
                "academic_session": r.academic_session,
                "semester": r.semester,
                "credits": r.credits,
                "prerequisites": r.prerequisites,
                "learning_outcomes": r.learning_outcomes,
                "syllabus": r.syllabus,
                "modules_outline": r.modules_outline,
                "start_date": r.start_date,
                "end_date": r.end_date,
                "capacity": r.capacity,
                "status": r.status,
                "teacher_id": r.teacher_id,
                "teacher_name": r.teacher_name,
                "is_published": r.is_published,
                "created_at": r.created_at,
                "enrolled_count": r.enrolled_count,
                "is_enrolled": r.id in enrolled_course_ids
            })
        return output

    def enroll_student(self, student_id: int, course_id: int) -> Enrollment:
        existing = self.db.query(Enrollment).filter(
            Enrollment.student_id == student_id,
            Enrollment.course_id == course_id
        ).first()

        if existing:
            if existing.status != "ACTIVE":
                existing.status = "ACTIVE"
                self.db.commit()
                self.db.refresh(existing)
            return existing

        enrollment = Enrollment(student_id=student_id, course_id=course_id, status="ACTIVE")
        self.db.add(enrollment)
        self.db.commit()
        self.db.refresh(enrollment)
        return enrollment

    def get_student_enrollments(self, student_id: int) -> List[Enrollment]:
        return self.db.query(Enrollment).options(
            joinedload(Enrollment.course)
        ).filter(Enrollment.student_id == student_id, Enrollment.status == "ACTIVE").all()

    def is_student_enrolled(self, student_id: int, course_id: int) -> bool:
        return self.db.query(Enrollment).filter(
            Enrollment.student_id == student_id,
            Enrollment.course_id == course_id,
            Enrollment.status == "ACTIVE"
        ).first() is not None

    def get_enrolled_student_ids(self, course_id: int) -> List[int]:
        rows = self.db.query(Enrollment.student_id).filter(
            Enrollment.course_id == course_id,
            Enrollment.status == "ACTIVE"
        ).all()
        return [r[0] for r in rows]

    def add_study_material(
        self,
        course_id: int,
        title: str,
        content: str,
        material_type: str = "NOTES",
        file_url: Optional[str] = None,
        original_filename: Optional[str] = None,
        file_type: Optional[str] = None,
        file_size: int = 0,
        file_storage_id: Optional[str] = None,
        uploaded_by: Optional[int] = None,
        status: str = "INDEXED",
        chunk_count: int = 0,
        error_message: Optional[str] = None
    ) -> StudyMaterial:
        material = StudyMaterial(
            course_id=course_id,
            title=title.strip(),
            content=content.strip(),
            material_type=material_type,
            original_filename=original_filename,
            file_type=file_type or material_type,
            file_size=file_size,
            file_storage_id=file_storage_id,
            file_url=file_url,
            uploaded_by=uploaded_by,
            status=status,
            chunk_count=chunk_count,
            error_message=error_message
        )
        self.db.add(material)
        self.db.commit()
        self.db.refresh(material)
        return material

    def get_study_material(self, material_id: int) -> Optional[StudyMaterial]:
        return self.db.query(StudyMaterial).filter(StudyMaterial.id == material_id).first()

    def find_material_by_filename(self, course_id: int, filename: str) -> Optional[StudyMaterial]:
        return self.db.query(StudyMaterial).filter(
            StudyMaterial.course_id == course_id,
            StudyMaterial.original_filename == filename
        ).first()

    def update_study_material_status(
        self,
        material_id: int,
        status: str,
        chunk_count: Optional[int] = None,
        error_message: Optional[str] = None,
        content: Optional[str] = None
    ) -> Optional[StudyMaterial]:
        m = self.db.query(StudyMaterial).filter(StudyMaterial.id == material_id).first()
        if not m:
            return None
        m.status = status
        if chunk_count is not None:
            m.chunk_count = chunk_count
        if error_message is not None:
            m.error_message = error_message
        if content is not None:
            m.content = content
        self.db.commit()
        self.db.refresh(m)
        return m

    def delete_study_material(self, material_id: int) -> bool:
        m = self.db.query(StudyMaterial).filter(StudyMaterial.id == material_id).first()
        if not m:
            return False
        self.db.delete(m)
        self.db.commit()
        return True

    def get_study_materials(self, course_id: int) -> List[StudyMaterial]:
        return self.db.query(StudyMaterial).filter(StudyMaterial.course_id == course_id).order_by(StudyMaterial.created_at.desc()).all()

    def add_announcement(self, course_id: int, author_id: int, title: str, content: str) -> Announcement:
        ann = Announcement(course_id=course_id, author_id=author_id, title=title.strip(), content=content.strip())
        self.db.add(ann)
        self.db.commit()
        self.db.refresh(ann)
        return ann

    def get_announcements(self, course_id: int) -> List[Announcement]:
        return self.db.query(Announcement).options(joinedload(Announcement.author)).filter(
            Announcement.course_id == course_id
        ).order_by(Announcement.created_at.desc()).all()

    def add_quiz(self, course_id: int, title: str, description: Optional[str] = None, due_date: Optional[Any] = None, duration_minutes: int = 30, total_points: int = 100) -> Quiz:
        q = Quiz(
            course_id=course_id,
            title=title.strip(),
            description=description,
            due_date=due_date,
            duration_minutes=duration_minutes,
            total_points=total_points
        )
        self.db.add(q)
        self.db.commit()
        self.db.refresh(q)
        return q

    def get_quizzes(self, course_id: int) -> List[Quiz]:
        return self.db.query(Quiz).filter(Quiz.course_id == course_id).order_by(Quiz.created_at.desc()).all()

    def delete_course(self, course_id: int) -> bool:
        course = self.db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return False
        self.db.delete(course)
        self.db.commit()
        return True
