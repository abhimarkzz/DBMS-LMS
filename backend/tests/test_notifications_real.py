import pytest
import asyncio
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.models.sql_models import User, Role, Course, Enrollment, Assignment, Submission
from app.database.postgres import SessionLocal, init_db
from app.database.mongo import get_mongo_db
from app.services.auth_service import hash_password, create_access_token
from app.services.notification_service import NotificationService
from app.services.assignment_service import AssignmentService
from app.services.course_service import CourseService


@pytest.fixture(scope="module")
def setup_notifs_db():
    init_db()
    db = SessionLocal()

    # Ensure Roles
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

    ts = int(datetime.utcnow().timestamp() * 1000)

    # Create Teacher
    teacher = User(
        email=f"prof_notif_{ts}@university.edu",
        password_hash=hash_password("teacher123"),
        full_name=f"Prof. Notification {ts}",
        role_id=teacher_role.id,
        is_active=True
    )
    db.add(teacher)

    # Create 2 Students
    students = []
    for i in range(1, 3):
        s = User(
            email=f"stud_notif_{i}_{ts}@university.edu",
            password_hash=hash_password("student123"),
            full_name=f"Student {i} {ts}",
            role_id=student_role.id,
            is_active=True
        )
        db.add(s)
        students.append(s)

    db.commit()
    db.refresh(teacher)
    for s in students:
        db.refresh(s)

    # Create Course
    course = Course(
        code=f"NOTIF{ts % 10000}",
        title=f"Notification Systems {ts}",
        credits=4,
        teacher_id=teacher.id,
        status="PUBLISHED",
        is_published=True
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    # Enroll Students
    for s in students:
        enrollment = Enrollment(student_id=s.id, course_id=course.id, status="ACTIVE")
        db.add(enrollment)
    db.commit()

    teacher_token = create_access_token({"sub": str(teacher.id), "role": "TEACHER"})
    student_1_token = create_access_token({"sub": str(students[0].id), "role": "STUDENT"})
    student_2_token = create_access_token({"sub": str(students[1].id), "role": "STUDENT"})

    client = TestClient(app)

    yield {
        "db": db,
        "teacher": teacher,
        "student_1": students[0],
        "student_2": students[1],
        "course": course,
        "teacher_token": teacher_token,
        "student_1_token": student_1_token,
        "student_2_token": student_2_token,
        "client": client
    }
    db.close()


@pytest.mark.asyncio
async def test_notification_creation(setup_notifs_db):
    data = setup_notifs_db
    user_id = data["student_1"].id

    doc = await NotificationService.create_notification(
        user_id=user_id,
        title="Direct Notification Test",
        message="System alert verification for student.",
        notif_type="SYSTEM",
        metadata={"test_key": "val1"}
    )
    assert doc is not None
    assert doc["user_id"] == user_id
    assert doc["title"] == "Direct Notification Test"
    assert doc["type"] == "SYSTEM"
    assert doc["is_read"] is False
    assert "id" in doc


@pytest.mark.asyncio
async def test_unread_count_from_mongo(setup_notifs_db):
    data = setup_notifs_db
    user_id = data["student_2"].id

    # Count before
    count_before = await NotificationService.get_unread_count(user_id)

    # Add 2 unread notifications
    await NotificationService.create_notification(
        user_id=user_id,
        title="Alert 1",
        message="Message 1",
        notif_type="SYSTEM"
    )
    await NotificationService.create_notification(
        user_id=user_id,
        title="Alert 2",
        message="Message 2",
        notif_type="SYSTEM"
    )

    count_after = await NotificationService.get_unread_count(user_id)
    assert count_after == count_before + 2


@pytest.mark.asyncio
async def test_mark_as_read(setup_notifs_db):
    data = setup_notifs_db
    user_id = data["student_2"].id

    doc = await NotificationService.create_notification(
        user_id=user_id,
        title="Unread Note",
        message="Please read me",
        notif_type="SYSTEM"
    )
    notif_id = doc["id"]
    count_before = await NotificationService.get_unread_count(user_id)

    # Mark as read
    res = await NotificationService.mark_as_read(notif_id, user_id)
    assert res is True

    count_after = await NotificationService.get_unread_count(user_id)
    assert count_after == count_before - 1


@pytest.mark.asyncio
async def test_mark_all_as_read(setup_notifs_db):
    data = setup_notifs_db
    user_id = data["student_2"].id

    # Create multiple unread notifications
    for i in range(3):
        await NotificationService.create_notification(
            user_id=user_id,
            title=f"Bulk Notif {i}",
            message=f"Bulk content {i}",
            notif_type="SYSTEM"
        )

    count_before = await NotificationService.get_unread_count(user_id)
    assert count_before >= 3

    # Mark all read
    marked_count = await NotificationService.mark_all_as_read(user_id)
    assert marked_count >= 3

    count_after = await NotificationService.get_unread_count(user_id)
    assert count_after == 0


@pytest.mark.asyncio
async def test_assignment_notification(setup_notifs_db):
    data = setup_notifs_db
    client = data["client"]
    teacher_token = data["teacher_token"]
    course = data["course"]
    student_1 = data["student_1"]
    student_2 = data["student_2"]

    s1_count_before = await NotificationService.get_unread_count(student_1.id)
    s2_count_before = await NotificationService.get_unread_count(student_2.id)

    # Teacher publishes an assignment via API
    resp = client.post(
        "/api/assignments",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "course_id": course.id,
            "title": "Quantum Computing Lab 1",
            "description": "Implement Deutsch-Jozsa algorithm",
            "max_score": 100.0,
            "assessment_type": "DESCRIPTIVE",
            "status": "PUBLISHED"
        }
    )
    assert resp.status_code == 201
    assign_data = resp.json()
    assert assign_data["title"] == "Quantum Computing Lab 1"

    # Both enrolled students must have received ASSIGNMENT_PUBLISHED notification
    s1_notifs = await NotificationService.get_user_notifications(student_1.id, limit=5)
    published_notif = next((n for n in s1_notifs if n["type"] == "ASSIGNMENT_PUBLISHED"), None)
    assert published_notif is not None
    assert "Quantum Computing Lab 1" in published_notif["title"]

    s2_count_after = await NotificationService.get_unread_count(student_2.id)
    assert s2_count_after > s2_count_before


@pytest.mark.asyncio
async def test_submission_notification(setup_notifs_db):
    data = setup_notifs_db
    client = data["client"]
    student_1 = data["student_1"]
    student_1_token = data["student_1_token"]
    teacher = data["teacher"]
    course = data["course"]
    db = data["db"]

    # Create assignment
    assign_service = AssignmentService(db)
    assignment = assign_service.create_assignment(
        course_id=course.id,
        title="Submission Test Essay",
        description="Write 500 words",
        max_score=50.0,
        due_date=datetime.utcnow() + timedelta(days=7),
        teacher_id=teacher.id,
        status_val="PUBLISHED"
    )

    t_count_before = await NotificationService.get_unread_count(teacher.id)

    # Student submits assignment
    sub_resp = client.post(
        f"/api/assignments/{assignment.id}/submit",
        headers={"Authorization": f"Bearer {student_1_token}"},
        json={
            "submission_type": "TEXT",
            "content": "This is my research essay content for grading."
        }
    )
    assert sub_resp.status_code == 200

    # 1. Student must have received SUBMISSION_SUCCESS
    s1_notifs = await NotificationService.get_user_notifications(student_1.id, limit=5)
    success_notif = next((n for n in s1_notifs if n["type"] == "SUBMISSION_SUCCESS"), None)
    assert success_notif is not None
    assert "Submission Successful" in success_notif["title"]

    # 2. Teacher must have received NEW_SUBMISSION & SUBMISSION_READY_FOR_GRADING
    t_notifs = await NotificationService.get_user_notifications(teacher.id, limit=5)
    new_sub_notif = next((n for n in t_notifs if n["type"] == "NEW_SUBMISSION"), None)
    assert new_sub_notif is not None
    ready_notif = next((n for n in t_notifs if n["type"] == "SUBMISSION_READY_FOR_GRADING"), None)
    assert ready_notif is not None


@pytest.mark.asyncio
async def test_grade_notification(setup_notifs_db):
    data = setup_notifs_db
    client = data["client"]
    teacher_token = data["teacher_token"]
    student_1 = data["student_1"]
    student_1_token = data["student_1_token"]
    teacher = data["teacher"]
    course = data["course"]
    db = data["db"]

    # Create & submit assignment
    assign_service = AssignmentService(db)
    assignment = assign_service.create_assignment(
        course_id=course.id,
        title="Grading Flow Assessment",
        description="Exam problem set",
        max_score=100.0,
        due_date=datetime.utcnow() + timedelta(days=7),
        teacher_id=teacher.id,
        status_val="PUBLISHED"
    )

    sub = await assign_service.submit_assignment(
        assignment_id=assignment.id,
        student_id=student_1.id,
        content="Here is my proof.",
        submission_type="TEXT"
    )

    # Teacher grades submission and publishes
    grade_resp = client.post(
        f"/api/assignments/submissions/{sub.id}/grade",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "score": 92.5,
            "feedback": "Outstanding derivation and clarity.",
            "publish": True
        }
    )
    assert grade_resp.status_code == 200

    # Student must have received GRADE_PUBLISHED notification
    s1_notifs = await NotificationService.get_user_notifications(student_1.id, limit=5)
    grade_notif = next((n for n in s1_notifs if n["type"] == "GRADE_PUBLISHED"), None)
    assert grade_notif is not None
    assert "92.5" in grade_notif["message"] or "92.5" in str(grade_notif.get("metadata", {}))


@pytest.mark.asyncio
async def test_announcement_notification(setup_notifs_db):
    data = setup_notifs_db
    client = data["client"]
    teacher = data["teacher"]
    teacher_token = data["teacher_token"]
    student_1 = data["student_1"]
    course = data["course"]

    # Teacher posts course announcement via API
    ann_resp = client.post(
        "/api/notifications/announcements",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "course_id": course.id,
            "title": "Guest Lecture on Monday",
            "content": "Dr. Turing will be delivering a guest lecture on computability."
        }
    )
    assert ann_resp.status_code == 201

    # Student must have received COURSE_ANNOUNCEMENT
    s1_notifs = await NotificationService.get_user_notifications(student_1.id, limit=5)
    ann_notif = next((n for n in s1_notifs if n["type"] == "COURSE_ANNOUNCEMENT"), None)
    assert ann_notif is not None
    assert "Guest Lecture on Monday" in ann_notif["title"]

    # Teacher must have received ANNOUNCEMENT_CONFIRMATION
    t_notifs = await NotificationService.get_user_notifications(teacher.id, limit=5)
    conf_notif = next((n for n in t_notifs if n["type"] == "ANNOUNCEMENT_CONFIRMATION"), None)
    assert conf_notif is not None
    assert "Announcement Published" in conf_notif["title"]


@pytest.mark.asyncio
async def test_api_unread_count_and_read_endpoints(setup_notifs_db):
    data = setup_notifs_db
    client = data["client"]
    student_1 = data["student_1"]
    student_1_token = data["student_1_token"]

    # 1. Test GET /api/notifications/unread-count
    count_resp = client.get(
        "/api/notifications/unread-count",
        headers={"Authorization": f"Bearer {student_1_token}"}
    )
    assert count_resp.status_code == 200
    assert "unread_count" in count_resp.json()
    assert isinstance(count_resp.json()["unread_count"], int)

    # 2. Test GET /api/notifications list
    list_resp = client.get(
        "/api/notifications",
        headers={"Authorization": f"Bearer {student_1_token}"}
    )
    assert list_resp.status_code == 200
    notifs = list_resp.json()
    assert len(notifs) > 0
    target_id = notifs[0]["id"]

    # 3. Test POST /api/notifications/{id}/read
    read_resp = client.post(
        f"/api/notifications/{target_id}/read",
        headers={"Authorization": f"Bearer {student_1_token}"}
    )
    assert read_resp.status_code == 200
    assert read_resp.json()["success"] is True

    # 4. Test POST /api/notifications/read-all
    read_all_resp = client.post(
        "/api/notifications/read-all",
        headers={"Authorization": f"Bearer {student_1_token}"}
    )
    assert read_all_resp.status_code == 200
    assert read_all_resp.json()["success"] is True

    # Unread count should now be 0
    count_after = client.get(
        "/api/notifications/unread-count",
        headers={"Authorization": f"Bearer {student_1_token}"}
    ).json()["unread_count"]
    assert count_after == 0
