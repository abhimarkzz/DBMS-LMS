import pytest
from datetime import datetime, timedelta
from sqlalchemy import text
from app.models.sql_models import User, Role, Course, Enrollment, Assignment, Submission, Result
from app.database.postgres import SessionLocal, init_db
from app.services.result_service import ResultService
from app.services.auth_service import hash_password


@pytest.fixture(scope="module")
def setup_gradebook_db():
    init_db()
    db = SessionLocal()

    # Create Roles if not existing
    teacher_role = db.query(Role).filter(Role.name == "TEACHER").first()
    if not teacher_role:
        teacher_role = Role(name="TEACHER")
        db.add(teacher_role)
    student_role = db.query(Role).filter(Role.name == "STUDENT").first()
    if not student_role:
        student_role = Role(name="STUDENT")
        db.add(student_role)
    admin_role = db.query(Role).filter(Role.name == "ADMIN").first()
    if not admin_role:
        admin_role = Role(name="ADMIN")
        db.add(admin_role)
    db.commit()

    # Unique timestamp for isolation
    ts = int(datetime.utcnow().timestamp() * 1000)

    # Create Teacher
    teacher = User(
        email=f"prof_gb_{ts}@university.edu",
        password_hash=hash_password("teacher123"),
        full_name=f"Prof. Gradebook {ts}",
        role_id=teacher_role.id,
        is_active=True
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)

    # Create 3 Students
    students = []
    for i in range(1, 4):
        s = User(
            email=f"stud_{i}_{ts}@university.edu",
            password_hash=hash_password("student123"),
            full_name=f"Student {i} {ts}",
            role_id=student_role.id,
            is_active=True
        )

        db.add(s)
        students.append(s)
    db.commit()
    for s in students:
        db.refresh(s)

    # Create Course
    course = Course(
        code=f"GB{ts % 10000}",
        title=f"Advanced Algorithms {ts}",
        description="Comprehensive course on data structures and algorithms.",
        credits=4,
        teacher_id=teacher.id,
        academic_session="Fall 2026",
        is_published=True
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    # Enroll Students
    for s in students:
        enr = Enrollment(student_id=s.id, course_id=course.id)
        db.add(enr)
    db.commit()

    # Create 2 Assignments
    a1 = Assignment(
        course_id=course.id,
        title="Lab 1: Graph Traversal",
        description="Implement BFS and DFS with cycle detection.",
        assessment_type="Descriptive",
        max_score=100.0,
        due_date=datetime.utcnow() + timedelta(days=7),
        status="PUBLISHED"
    )
    a2 = Assignment(
        course_id=course.id,
        title="Lab 2: Dynamic Programming",
        description="Knapsack and shortest paths.",
        assessment_type="Descriptive",
        max_score=100.0,
        due_date=datetime.utcnow() + timedelta(days=14),
        status="PUBLISHED"
    )
    db.add_all([a1, a2])
    db.commit()
    db.refresh(a1)
    db.refresh(a2)

    yield {
        "db": db,
        "teacher": teacher,
        "students": students,
        "course": course,
        "assignments": [a1, a2]
    }

    # Teardown
    db.query(Submission).filter(Submission.assignment_id.in_([a1.id, a2.id])).delete(synchronize_session=False)
    db.query(Result).filter(Result.course_id == course.id).delete(synchronize_session=False)
    db.query(Assignment).filter(Assignment.id.in_([a1.id, a2.id])).delete(synchronize_session=False)
    db.query(Enrollment).filter(Enrollment.course_id == course.id).delete(synchronize_session=False)
    db.query(Course).filter(Course.id == course.id).delete(synchronize_session=False)
    db.query(User).filter(User.id.in_([teacher.id] + [s.id for s in students])).delete(synchronize_session=False)
    db.commit()
    db.close()


def test_1_no_submissions(setup_gradebook_db):
    """Test scenario: Student is enrolled, has 0 submissions."""
    data = setup_gradebook_db
    db = data["db"]
    student = data["students"][0]
    course = data["course"]
    service = ResultService(db)

    breakdown = service.get_student_course_breakdown(student.id, course.id)
    assert breakdown is not None
    assert breakdown["total_assignments"] == 2
    assert breakdown["completed_assignments"] == 0
    assert breakdown["pending_assignments"] == 2
    assert breakdown["completion_percentage"] == 0.0
    assert breakdown["course_percentage"] is None
    assert breakdown["status"] in ["IN_PROGRESS", "UNPUBLISHED"]

    # All assignment scores should be NOT_SUBMITTED with score None
    for asg in breakdown["assignments"]:
        assert asg["submission_status"] == "NOT_SUBMITTED"
        assert asg["score"] is None


def test_2_one_submission_and_auto_grading(setup_gradebook_db):
    """Test scenario: Student submits one assignment and teacher grades it."""
    data = setup_gradebook_db
    db = data["db"]
    student = data["students"][0]
    course = data["course"]
    a1 = data["assignments"][0]
    service = ResultService(db)

    sub = Submission(
        assignment_id=a1.id,
        student_id=student.id,
        score=85.0,
        status="GRADED",
        grade_status="PUBLISHED",
        feedback="Excellent graph implementation.",
        content="https://github.com/student1/lab1"
    )
    db.add(sub)
    db.commit()

    # Verify student course breakdown reflects the published submission
    breakdown = service.get_student_course_breakdown(student.id, course.id)
    assert breakdown["completed_assignments"] == 1
    assert breakdown["pending_assignments"] == 1
    assert breakdown["completion_percentage"] == 50.0

    a1_score = next(a for a in breakdown["assignments"] if a["assignment_id"] == a1.id)
    assert a1_score["submission_status"] == "GRADED"
    assert a1_score["score"] == 85.0
    assert a1_score["percentage"] == 85.0
    assert a1_score["grade"] == "A"
    assert a1_score["feedback"] == "Excellent graph implementation."

    # Verify auto-grade trigger updated the results table
    res = db.query(Result).filter(Result.student_id == student.id, Result.course_id == course.id).first()
    assert res is not None
    assert res.status == "PUBLISHED"
    # Total score 85 out of 200 = 42.5%
    assert float(res.total_score) == 85.0
    assert float(res.max_possible) == 200.0


def test_3_regrading_updates_results_automatically(setup_gradebook_db):
    """Test scenario: Regrading a submission triggers automatic update of results and views."""
    data = setup_gradebook_db
    db = data["db"]
    student = data["students"][0]
    course = data["course"]
    a1 = data["assignments"][0]
    service = ResultService(db)

    sub = db.query(Submission).filter(
        Submission.assignment_id == a1.id,
        Submission.student_id == student.id
    ).first()
    assert sub is not None

    # Teacher regrades from 85 to 95
    sub.score = 95.0
    sub.feedback = "Bonus points awarded for cycle detection optimization."
    db.commit()

    # Check updated breakdown
    breakdown = service.get_student_course_breakdown(student.id, course.id)
    a1_score = next(a for a in breakdown["assignments"] if a["assignment_id"] == a1.id)
    assert a1_score["score"] == 95.0
    assert a1_score["percentage"] == 95.0
    assert a1_score["grade"] == "A+"

    # Verify result table auto-updated via trigger
    res = db.query(Result).filter(Result.student_id == student.id, Result.course_id == course.id).first()
    assert float(res.total_score) == 95.0
    assert float(res.percentage) == 47.5


def test_4_unpublished_result_draft_withheld_from_student(setup_gradebook_db):
    """Test scenario: Teacher grades in draft; score is withheld from student view."""
    data = setup_gradebook_db
    db = data["db"]
    student = data["students"][1]
    course = data["course"]
    a1 = data["assignments"][0]
    service = ResultService(db)

    # Student 2 submits Lab 1, graded in draft
    sub2 = Submission(
        assignment_id=a1.id,
        student_id=student.id,
        score=90.0,
        status="GRADED",
        grade_status="DRAFT",
        feedback="Pending faculty moderation.",
        content="Code submitted"
    )
    db.add(sub2)
    db.commit()

    # For student, breakdown should show PENDING_GRADING and score hidden
    breakdown = service.get_student_course_breakdown(student.id, course.id)
    a1_score = next(a for a in breakdown["assignments"] if a["assignment_id"] == a1.id)
    assert a1_score["submission_status"] == "PENDING_GRADING"
    assert a1_score["score"] is None
    assert a1_score["grade"] is None

    # Student 2 should not have a published grade in student_progress_view
    progress_rows = service.get_student_progress_view(student.id)
    course_prog = next((p for p in progress_rows if p["course_id"] == course.id), None)
    if course_prog:
        assert course_prog.get("published_grade") is None


def test_5_publishing_draft_result(setup_gradebook_db):
    """Test scenario: Teacher publishes previously drafted grade."""
    data = setup_gradebook_db
    db = data["db"]
    student = data["students"][1]
    course = data["course"]
    a1 = data["assignments"][0]
    service = ResultService(db)

    sub2 = db.query(Submission).filter(
        Submission.assignment_id == a1.id,
        Submission.student_id == student.id
    ).first()
    sub2.grade_status = "PUBLISHED"
    db.commit()

    # Now student sees the grade
    breakdown = service.get_student_course_breakdown(student.id, course.id)
    a1_score = next(a for a in breakdown["assignments"] if a["assignment_id"] == a1.id)
    assert a1_score["submission_status"] == "GRADED"
    assert a1_score["score"] == 90.0
    assert a1_score["grade"] == "A+"


def test_6_multiple_students_top_rank_ties_and_gradebook_matrix(setup_gradebook_db):
    """
    Test scenario:
    - Multiple students enrolled
    - Top rank ties (Student 1 and Student 2 both score identically on remaining assignments)
    - Full Gradebook matrix consistency
    """
    data = setup_gradebook_db
    db = data["db"]
    s1, s2, s3 = data["students"]
    course = data["course"]
    a1, a2 = data["assignments"]
    service = ResultService(db)

    # Let s1 and s2 both have identical total scores to trigger a RANK() tie
    # s1 already has a1 = 95. Give s1 a2 = 95 -> total 190 / 200 = 95%
    sub_s1_a2 = Submission(
        assignment_id=a2.id,
        student_id=s1.id,
        score=95.0,
        status="GRADED",
        grade_status="PUBLISHED",
        content="DP solution"
    )
    # s2 currently has a1 = 90. Change s2 a1 to 95, and s2 a2 = 95 -> total 190 / 200 = 95%
    sub_s2_a1 = db.query(Submission).filter(Submission.assignment_id == a1.id, Submission.student_id == s2.id).first()
    sub_s2_a1.score = 95.0
    sub_s2_a2 = Submission(
        assignment_id=a2.id,
        student_id=s2.id,
        score=95.0,
        status="GRADED",
        grade_status="PUBLISHED",
        content="DP solution"
    )
    # s3 has a1 = 80, a2 = 80 -> total 160 / 200 = 80%
    sub_s3_a1 = Submission(
        assignment_id=a1.id,
        student_id=s3.id,
        score=80.0,
        status="GRADED",
        grade_status="PUBLISHED",
        content="Lab 1"
    )
    sub_s3_a2 = Submission(
        assignment_id=a2.id,
        student_id=s3.id,
        score=80.0,
        status="GRADED",
        grade_status="PUBLISHED",
        content="Lab 2"
    )

    db.add_all([sub_s1_a2, sub_s2_a2, sub_s3_a1, sub_s3_a2])
    db.commit()

    # Test Window Function Leaderboard: Check top rank ties
    leaderboard = service.get_course_leaderboard(course.id)
    assert len(leaderboard) >= 3

    rank1_items = [item for item in leaderboard if item["rank"] == 1]
    # S1 and S2 must both have rank 1 due to identical percentage 95.0%
    assert len(rank1_items) == 2
    student_ids_rank_1 = {item["student_id"] for item in rank1_items}
    assert s1.id in student_ids_rank_1
    assert s2.id in student_ids_rank_1

    # S3 should be rank 3 (due to standard SQL RANK behavior skipping rank 2 after a 2-way tie)
    s3_item = next(item for item in leaderboard if item["student_id"] == s3.id)
    assert s3_item["rank"] == 3
    assert s3_item["percentage"] == 80.0

    # Fetch complete Teacher Gradebook
    gradebook = service.get_course_gradebook(course.id)
    assert gradebook is not None
    assert len(gradebook["students"]) == 3
    assert len(gradebook["assignments"]) == 2

    # Check Gradebook stats consistency
    stats = gradebook["stats"]
    # (95 + 95 + 80) / 3 = 90.0% class average
    assert round(stats["class_average"], 1) == 90.0
    assert stats["highest_percentage"] == 95.0
    assert stats["lowest_percentage"] == 80.0
    assert stats["pending_grading"] == 0
    assert stats["completed_grading"] == 6

    # Verify course_result_summary_view yields exact same class average!
    view_summary = service.get_course_summary_view(course.id)
    assert len(view_summary) == 1
    assert round(float(view_summary[0]["course_average_percentage"]), 1) == 90.0


def test_7_missing_grades_handling(setup_gradebook_db):
    """Test scenario: An assignment is left unsubmitted, verifying missing grade identification."""
    data = setup_gradebook_db
    db = data["db"]
    course = data["course"]
    service = ResultService(db)

    # Add a 3rd assignment that no student has submitted yet
    a3 = Assignment(
        course_id=course.id,
        title="Lab 3: Red-Black Trees",
        description="Self-balancing binary search trees.",
        assessment_type="Descriptive",
        max_score=50.0,
        due_date=datetime.utcnow() + timedelta(days=21),
        status="PUBLISHED"
    )
    db.add(a3)
    db.commit()
    db.refresh(a3)

    gradebook = service.get_course_gradebook(course.id)
    assert len(gradebook["assignments"]) == 3

    # For all students, assignment 3 must show NOT_SUBMITTED with score None
    for st_row in gradebook["students"]:
        a3_cell = st_row["grades"][a3.id]
        assert a3_cell["status"] == "NOT_SUBMITTED"
        assert a3_cell["score"] is None
        assert a3_cell["letter_grade"] is None


def test_8_admin_academic_stats(setup_gradebook_db):
    """Test scenario: Admin academic statistics aggregation."""
    data = setup_gradebook_db
    db = data["db"]
    service = ResultService(db)

    admin_stats = service.get_admin_academic_stats()
    assert admin_stats["total_courses"] >= 1
    assert admin_stats["total_students"] >= 3
    assert admin_stats["total_results_published"] >= 3
    assert admin_stats["platform_average_percentage"] > 0
    assert "A+" in admin_stats["grade_distribution"]
    assert "A" in admin_stats["grade_distribution"]
