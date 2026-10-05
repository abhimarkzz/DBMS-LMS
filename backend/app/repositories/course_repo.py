from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.models.sql_models import Course, Enrollment, StudyMaterial, User


class CourseRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_course_by_id(self, course_id: int) -> Optional[Course]:
        return self.db.query(Course).options(
            joinedload(Course.teacher),
            joinedload(Course.materials)
        ).filter(Course.id == course_id).first()

    def get_course_by_code(self, code: str) -> Optional[Course]:
        return self.db.query(Course).filter(Course.code == code.upper().strip()).first()

    def create_course(self, code: str, title: str, description: Optional[str], syllabus: Optional[str], teacher_id: int) -> Course:
        course = Course(
            code=code.upper().strip(),
            title=title.strip(),
            description=description,
            syllabus=syllabus,
            teacher_id=teacher_id,
            is_published=True
        )
        self.db.add(course)
        self.db.commit()
        self.db.refresh(course)
        return course

    def list_courses(self, student_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """List published courses with teacher name, enrollment count, and enrollment status."""
        query = self.db.query(
            Course.id,
            Course.code,
            Course.title,
            Course.description,
            Course.syllabus,
            Course.teacher_id,
            User.full_name.label("teacher_name"),
            Course.is_published,
            Course.created_at,
            func.count(Enrollment.id).label("enrolled_count")
        ).join(User, Course.teacher_id == User.id)\
         .outerjoin(Enrollment, Course.id == Enrollment.course_id)\
         .filter(Course.is_published == True)\
         .group_by(Course.id, User.full_name)\
         .order_by(Course.code)

        results = query.all()
        
        # Check student enrollments if student_id provided
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
                "description": r.description,
                "syllabus": r.syllabus,
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

    def add_study_material(self, course_id: int, title: str, content: str, material_type: str = "NOTES", file_url: Optional[str] = None) -> StudyMaterial:
        material = StudyMaterial(
            course_id=course_id,
            title=title.strip(),
            content=content.strip(),
            material_type=material_type,
            file_url=file_url
        )
        self.db.add(material)
        self.db.commit()
        self.db.refresh(material)
        return material

    def get_study_materials(self, course_id: int) -> List[StudyMaterial]:
        return self.db.query(StudyMaterial).filter(StudyMaterial.course_id == course_id).order_by(StudyMaterial.created_at.desc()).all()
