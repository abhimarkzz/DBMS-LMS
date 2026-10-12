from typing import Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.postgres import get_db
from app.database.mongo import get_mongo_db
from app.services.auth_service import get_current_user, require_roles
from app.services.notification_service import NotificationService
from app.models.sql_models import (
    User, Role, Course, Enrollment, Assignment, Submission, Result, NoteChunk, Announcement
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboards"])


@router.get("/student")
async def get_student_dashboard(
    current_user: User = Depends(require_roles(["STUDENT"])),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    # 1. Enrolled courses with real calculated progress
    enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == current_user.id,
        Enrollment.status == "ACTIVE"
    ).all()

    enrolled_courses = []
    course_ids = [e.course_id for e in enrollments]

    total_course_assignments = 0
    total_student_submissions = 0

    for e in enrollments:
        c = e.course
        if not c:
            continue
        c_assign_count = db.query(Assignment).filter(Assignment.course_id == c.id).count()
        c_sub_count = db.query(Submission).join(Assignment).filter(
            Assignment.course_id == c.id,
            Submission.student_id == current_user.id
        ).count()

        total_course_assignments += c_assign_count
        total_student_submissions += c_sub_count

        progress_pct = round((c_sub_count / c_assign_count * 100), 1) if c_assign_count > 0 else 100.0

        enrolled_courses.append({
            "id": c.id,
            "course_id": c.id,
            "code": c.code,
            "title": c.title,
            "department": c.department or "Computer Science & Engineering",
            "level": c.level or "Graduate",
            "credits": c.credits or 4,
            "teacher_name": c.teacher.full_name if c.teacher else "Faculty Instructor",
            "enrolled_at": e.enrolled_at,
            "assignment_count": c_assign_count,
            "submitted_count": c_sub_count,
            "progress_pct": progress_pct,
            "progress_percentage": progress_pct,
            "status": c.status
        })

    # 2. Pending Assignments
    # Assignments from enrolled courses where student has NOT submitted
    submitted_assignment_ids = {
        row[0] for row in db.query(Submission.assignment_id).filter(
            Submission.student_id == current_user.id
        ).all()
    }

    pending_query = db.query(Assignment).filter(
        Assignment.course_id.in_(course_ids)
    ) if course_ids else None

    pending_assignments = []
    upcoming_deadlines = []

    if pending_query:
        all_assigns = pending_query.order_by(Assignment.due_date.asc().nulls_last()).all()
        for a in all_assigns:
            is_done = a.id in submitted_assignment_ids
            assign_item = {
                "id": a.id,
                "assignment_id": a.id,
                "course_id": a.course_id,
                "course_code": a.course.code if a.course else "",
                "course_title": a.course.title if a.course else "",
                "title": a.title,
                "due_date": a.due_date,
                "max_score": float(a.max_score) if a.max_score else 100.0,
                "has_submitted": is_done
            }
            if not is_done:
                pending_assignments.append(assign_item)
            if a.due_date and a.due_date >= datetime.utcnow():
                upcoming_deadlines.append(assign_item)

    # 3. Recently Published Results
    results = db.query(Result).filter(
        Result.student_id == current_user.id,
        Result.status == "PUBLISHED"
    ).order_by(Result.published_at.desc()).limit(10).all()

    recent_results = [
        {
            "id": r.id,
            "result_id": r.id,
            "submission_id": r.id,
            "course_id": r.course_id,
            "course_code": r.course.code if r.course else "",
            "course_title": r.course.title if r.course else "",
            "assignment_title": f"{r.course.code if r.course else 'Course'} Cumulative Evaluation",
            "score": float(r.total_score),
            "max_score": float(r.max_possible),
            "total_score": float(r.total_score),
            "max_possible": float(r.max_possible),
            "percentage": float(r.percentage),
            "grade": r.grade,
            "published_at": r.published_at,
            "feedback": "Official grade published in academic transcript."
        }
        for r in results
    ]

    # Calculate overall GPA / Average Percentage
    avg_pct = round(sum(r["percentage"] for r in recent_results) / len(recent_results), 1) if recent_results else 0.0

    # 4. Unread Notifications Count from MongoDB
    unread_notifs = await NotificationService.get_unread_count(current_user.id)

    return {
        "welcome": {
            "full_name": current_user.full_name,
            "email": current_user.email,
            "academic_session": "Spring 2026",
            "semester": "Term 2",
            "department": "Computer Science & Engineering"
        },
        "stats": {
            "enrolled_courses_count": len(enrolled_courses),
            "pending_assignments_count": len(pending_assignments),
            "completed_assignments_count": total_student_submissions,
            "average_percentage": avg_pct,
            "average_progress": avg_pct,
            "unread_notifications_count": unread_notifs
        },
        "enrolled_courses": enrolled_courses,
        "pending_assignments": pending_assignments[:5],
        "upcoming_deadlines": upcoming_deadlines[:5],
        "recent_results": recent_results[:5]
    }


@router.get("/teacher")
async def get_teacher_dashboard(
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    # 1. Courses taught
    taught_courses = db.query(Course).filter(Course.teacher_id == current_user.id).order_by(Course.code).all()
    course_ids = [c.id for c in taught_courses]

    courses_summary = []
    total_enrolled = 0

    for c in taught_courses:
        enroll_count = db.query(Enrollment).filter(
            Enrollment.course_id == c.id,
            Enrollment.status == "ACTIVE"
        ).count()
        total_enrolled += enroll_count

        courses_summary.append({
            "id": c.id,
            "code": c.code,
            "title": c.title,
            "department": c.department,
            "level": c.level,
            "credits": c.credits,
            "capacity": c.capacity,
            "status": c.status,
            "is_published": c.is_published,
            "enrolled_count": enroll_count
        })

    # 2. Pending Submissions (ungraded)
    pending_submissions = []
    if course_ids:
        subs = db.query(Submission).join(Assignment).filter(
            Assignment.course_id.in_(course_ids),
            Submission.status.in_(["SUBMITTED", "EVALUATED", "LATE"])
        ).order_by(Submission.submitted_at.desc()).all()

        for s in subs:
            pending_submissions.append({
                "id": s.id,
                "submission_id": s.id,
                "assignment_id": s.assignment_id,
                "assignment_title": s.assignment.title if s.assignment else "Assignment",
                "course_code": s.assignment.course.code if s.assignment and s.assignment.course else "",
                "student_id": s.student_id,
                "student_name": s.student.full_name if s.student else "Student",
                "student_email": s.student.email if s.student else "",
                "submitted_at": s.submitted_at,
                "content": s.content,
                "content_preview": s.content[:120] + "..." if len(s.content) > 120 else s.content,
                "max_score": float(s.assignment.max_score) if s.assignment else 100.0,
                "submission_type": s.submission_type or "TEXT",
                "is_late": s.is_late or False,
                "file_storage_id": s.file_storage_id,
                "file_name": s.file_name,
                "file_size": s.file_size,
                "mcq_answers": s.mcq_answers,
                "rubric_evaluation": s.rubric_evaluation,
                "attempt_number": s.attempt_number or 1,
                "assessment_type": s.assignment.assessment_type if s.assignment else "DESCRIPTIVE",
                "assessment_config": s.assignment.assessment_config if s.assignment else None,
                "instructions": s.assignment.instructions if s.assignment else None,
                "status": s.status,
                "grade_status": s.grade_status,
                "score": float(s.score) if s.score is not None else None,
                "feedback": s.feedback
            })

    # 3. Upcoming Assignment Deadlines
    upcoming_deadlines = []
    if course_ids:
        upcoming = db.query(Assignment).filter(
            Assignment.course_id.in_(course_ids),
            Assignment.due_date.isnot(None),
            Assignment.due_date >= datetime.utcnow()
        ).order_by(Assignment.due_date.asc()).limit(5).all()

        for u in upcoming:
            upcoming_deadlines.append({
                "id": u.id,
                "course_code": u.course.code if u.course else "",
                "title": u.title,
                "due_date": u.due_date,
                "max_score": float(u.max_score) if u.max_score else 100.0
            })

    # 4. Recent Announcements
    announcements = []
    if course_ids:
        anns = db.query(Announcement).filter(
            Announcement.course_id.in_(course_ids)
        ).order_by(Announcement.created_at.desc()).limit(5).all()

        for a in anns:
            announcements.append({
                "id": a.id,
                "course_code": a.course.code if a.course else "",
                "title": a.title,
                "content": a.content,
                "created_at": a.created_at
            })

    # 5. Course Performance & Recent Grading Activity
    recent_grading = []
    course_performance = []

    if course_ids:
        # Graded submissions
        graded = db.query(Submission).join(Assignment).filter(
            Assignment.course_id.in_(course_ids),
            Submission.status == "GRADED"
        ).order_by(Submission.graded_at.desc().nulls_last()).limit(5).all()

        for g in graded:
            recent_grading.append({
                "id": g.id,
                "assignment_title": g.assignment.title if g.assignment else "",
                "course_code": g.assignment.course.code if g.assignment and g.assignment.course else "",
                "student_name": g.student.full_name if g.student else "",
                "score": float(g.score) if g.score is not None else 0.0,
                "feedback": g.feedback,
                "graded_at": g.graded_at
            })

        # Performance per course
        for c in taught_courses:
            avg_res = db.query(func.avg(Result.percentage)).filter(Result.course_id == c.id).scalar()
            course_performance.append({
                "course_id": c.id,
                "course_code": c.code,
                "title": c.title,
                "average_percentage": round(float(avg_res), 1) if avg_res is not None else 0.0,
                "total_graded_results": db.query(Result).filter(Result.course_id == c.id).count()
            })

    # 6. Indexed Study Material / Vectors Count
    indexed_notes_count = db.query(NoteChunk).filter(
        NoteChunk.course_id.in_(course_ids)
    ).count() if course_ids else 0

    return {
        "stats": {
            "courses_taught_count": len(taught_courses),
            "total_enrolled_students": total_enrolled,
            "pending_submissions_count": len(pending_submissions),
            "upcoming_deadlines_count": len(upcoming_deadlines),
            "indexed_study_materials_count": indexed_notes_count,
            "indexed_materials_count": indexed_notes_count
        },
        "courses_taught": courses_summary,
        "courses": courses_summary,
        "pending_submissions": pending_submissions[:5],
        "upcoming_deadlines": upcoming_deadlines,
        "recent_announcements": announcements,
        "recent_grading_activity": recent_grading,
        "course_performance": course_performance
    }


@router.get("/admin")
async def get_admin_dashboard(
    _: User = Depends(require_roles(["ADMIN"])),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    total_users = db.query(User).count()
    total_students = db.query(User).join(Role).filter(Role.name == "STUDENT").count()
    total_teachers = db.query(User).join(Role).filter(Role.name == "TEACHER").count()
    active_courses = db.query(Course).filter(Course.is_published == True).count()
    total_assignments = db.query(Assignment).count()
    total_submissions = db.query(Submission).count()
    pending_evaluations = db.query(Submission).filter(Submission.status == "SUBMITTED").count()
    total_vector_chunks = db.query(NoteChunk).count()

    activities = await NotificationService.get_recent_activities(limit=12)

    total_admins = db.query(User).join(Role).filter(Role.name == "ADMIN").count()

    return {
        "stats": {
            "users": total_users,
            "total_users": total_users,
            "students": total_students,
            "total_students": total_students,
            "teachers": total_teachers,
            "total_teachers": total_teachers,
            "admins": total_admins,
            "total_admins": total_admins,
            "active_courses": active_courses,
            "total_active_courses": active_courses,
            "assignments": total_assignments,
            "total_assignments": total_assignments,
            "submissions": total_submissions,
            "total_submissions": total_submissions,
            "pending_evaluations": pending_evaluations,
            "total_vector_chunks": total_vector_chunks
        },
        "recent_activity": activities
    }
