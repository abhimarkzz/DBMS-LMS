import pytest
import time
import uuid
from io import BytesIO
from fastapi.testclient import TestClient
from app.main import app
from app.database.postgres import SessionLocal
from app.models.sql_models import User, Course, Assignment, Submission, Role
from app.services.auth_service import hash_password, create_access_token
from datetime import timedelta


@pytest.fixture
def client():
    return TestClient(app)


def get_token(client: TestClient, email: str, password: str = "Password123!") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


# ============================================================================
# 1. AUTHENTICATION & TOKEN INTEGRITY TESTS
# ============================================================================

def test_auth_token_tampering_and_forgery(client):
    """Ensure tampered tokens or forged signatures return 401 Unauthorized."""
    # 1. No header
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/courses").status_code == 401
    assert client.get("/api/admin/overview").status_code == 401

    # 2. Forged signature
    forged_token = create_access_token({"sub": "1", "role": "ADMIN"}) + "malicious_tamper"
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged_token}"})
    assert res.status_code == 401
    assert "invalid" in res.json()["detail"].lower() or "token" in res.json()["detail"].lower()

    # 3. Expired token
    expired_token = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-10))
    res_exp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res_exp.status_code == 401
    assert "expired" in res_exp.json()["detail"].lower()


def test_auth_invalid_credentials(client):
    """Ensure wrong passwords and non-existent emails return 401."""
    res1 = client.post("/api/auth/login", json={"email": "alex@student.univ.edu", "password": "WrongPassword!"})
    assert res1.status_code == 401

    res2 = client.post("/api/auth/login", json={"email": "nonexistent_hacker@univ.edu", "password": "Password123!"})
    assert res2.status_code == 401


# ============================================================================
# 2. RBAC (ROLE-BASED ACCESS CONTROL) TESTS
# ============================================================================

def test_rbac_student_privilege_isolation(client):
    """Verify that Students are strictly blocked from privileged operations."""
    student_token = get_token(client, "alex@student.univ.edu")
    headers = {"Authorization": f"Bearer {student_token}"}

    # 1. Student must not create courses
    c_res = client.post("/api/courses", headers=headers, json={
        "code": f"HACK_{uuid.uuid4().hex[:4]}",
        "title": "Unauthorized Student Course",
        "credits": 3
    })
    assert c_res.status_code == 403
    assert "Access denied" in c_res.json()["detail"]

    # 2. Student must not access admin overview
    admin_res = client.get("/api/admin/overview", headers=headers)
    assert admin_res.status_code == 403

    # 3. Student must not access user directory
    users_res = client.get("/api/users", headers=headers)
    assert users_res.status_code == 403

    # 4. Student must not access admin academic stats
    stats_res = client.get("/api/results/admin/academic-stats", headers=headers)
    assert stats_res.status_code == 403

    # 5. Student must not access teacher gradebook
    gb_res = client.get("/api/results/course/1/gradebook", headers=headers)
    assert gb_res.status_code == 403

    # 6. Student must not trigger grade calculation directly
    calc_res = client.post("/api/results/calculate?student_id=1&course_id=1", headers=headers)
    assert calc_res.status_code == 403


def test_rbac_teacher_privilege_isolation(client):
    """Verify that Teachers cannot perform Admin-only operations or access other teachers' courses."""
    teacher_token = get_token(client, "prof.alan@univ.edu")
    headers = {"Authorization": f"Bearer {teacher_token}"}

    # 1. Teacher must not access admin overview
    assert client.get("/api/admin/overview", headers=headers).status_code == 403

    # 2. Teacher must not access user directory
    assert client.get("/api/users", headers=headers).status_code == 403

    # 3. Teacher must not access admin academic stats
    assert client.get("/api/results/admin/academic-stats", headers=headers).status_code == 403


def test_rbac_teacher_cross_course_grading_prevention(client):
    """Ensure a teacher cannot grade or view gradebook for another instructor's course."""
    db = SessionLocal()
    teacher_role = db.query(Role).filter(Role.name == "TEACHER").first()
    ts = int(time.time() * 1000)

    # Create Teacher A
    t_a = User(
        email=f"t_a_{ts}@univ.edu",
        password_hash=hash_password("Pass123!"),
        full_name=f"Teacher A {ts}",
        role_id=teacher_role.id
    )
    # Create Teacher B
    t_b = User(
        email=f"t_b_{ts}@univ.edu",
        password_hash=hash_password("Pass123!"),
        full_name=f"Teacher B {ts}",
        role_id=teacher_role.id
    )
    db.add_all([t_a, t_b])
    db.commit()
    db.refresh(t_a)
    db.refresh(t_b)

    t_a_id = t_a.id
    t_b_id = t_b.id

    # Course owned by Teacher A
    course_a = Course(
        code=f"CA{ts % 10000}",
        title="Course A Security Test",
        credits=3,
        teacher_id=t_a_id,
        is_published=True
    )
    db.add(course_a)
    db.commit()
    db.refresh(course_a)
    course_a_id = course_a.id

    assign_a = Assignment(
        course_id=course_a_id,
        title="Assignment in Course A",
        description="Testing cross teacher isolation",
        max_score=100.0,
        status="PUBLISHED"
    )
    db.add(assign_a)
    db.commit()
    db.refresh(assign_a)
    db.close()

    try:
        # Login as Teacher B
        token_b = get_token(client, f"t_b_{ts}@univ.edu", "Pass123!")
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 1. Teacher B tries to access Gradebook of Course A -> 403 Forbidden
        gb_res = client.get(f"/api/results/course/{course_a_id}/gradebook", headers=headers_b)
        assert gb_res.status_code == 403
        assert "only view the gradebook for courses you instruct" in gb_res.json()["detail"]

        # 2. Teacher B tries to access above-average analytics of Course A -> 403 Forbidden
        avg_res = client.get(f"/api/results/course/{course_a_id}/above-average", headers=headers_b)
        assert avg_res.status_code == 403

        # 3. Teacher B tries to recalculate grade in Course A -> 403 Forbidden
        calc_res = client.post(f"/api/results/calculate?student_id=1&course_id={course_a_id}", headers=headers_b)
        assert calc_res.status_code == 403
    finally:
        cleanup_db = SessionLocal()
        c = cleanup_db.query(Course).filter(Course.id == course_a_id).first()
        if c:
            cleanup_db.delete(c)
        ua = cleanup_db.query(User).filter(User.id == t_a_id).first()
        if ua:
            cleanup_db.delete(ua)
        ub = cleanup_db.query(User).filter(User.id == t_b_id).first()
        if ub:
            cleanup_db.delete(ub)
        cleanup_db.commit()
        cleanup_db.close()


# ============================================================================
# 3. INPUT VALIDATION, FILE SECURITY & SCORE MANIPULATION PREVENTION
# ============================================================================

def test_score_manipulation_prevention(client):
    """Ensure negative scores or scores exceeding max_score are rejected."""
    t_token = get_token(client, "prof.alan@univ.edu")
    s_token = get_token(client, "alex@student.univ.edu")
    t_headers = {"Authorization": f"Bearer {t_token}"}
    s_headers = {"Authorization": f"Bearer {s_token}"}

    # Create test course and assignment (max_score = 50.0)
    c_res = client.post("/api/courses", headers=t_headers, json={
        "code": f"SCR_{uuid.uuid4().hex[:6].upper()}",
        "title": "Score Limit Verification Course",
        "credits": 3
    })
    c_id = c_res.json()["id"]
    try:
        client.post(f"/api/courses/{c_id}/enroll", headers=s_headers)

        a_res = client.post("/api/assignments", headers=t_headers, json={
            "course_id": c_id,
            "title": "Strict Score Test",
            "description": "Max 50 points",
            "max_score": 50.0
        })
        a_id = a_res.json()["id"]

        sub_res = client.post(f"/api/assignments/{a_id}/submit", headers=s_headers, json={
            "content": "Student submission for score checks",
            "submission_type": "TEXT"
        })
        sub_id = sub_res.json()["id"]

        # 1. Attempt to grade higher than max_score (e.g. 55 / 50)
        high_res = client.post(f"/api/assignments/submissions/{sub_id}/grade", headers=t_headers, json={
            "score": 55.0,
            "feedback": "Illegitimate bonus"
        })
        assert high_res.status_code == 400
        assert "between 0 and 50" in high_res.json()["detail"]

        # 2. Attempt negative score -> rejected by Pydantic / service validation
        neg_res = client.post(f"/api/assignments/submissions/{sub_id}/grade", headers=t_headers, json={
            "score": -5.0,
            "feedback": "Penalty"
        })
        assert neg_res.status_code in [400, 422]

        # 3. Student tries to grade themselves -> 403 Forbidden
        student_grade_res = client.post(f"/api/assignments/submissions/{sub_id}/grade", headers=s_headers, json={
            "score": 50.0,
            "feedback": "Self-awarded grade"
        })
        assert student_grade_res.status_code == 403
    finally:
        client.delete(f"/api/courses/{c_id}", headers=t_headers)


def test_file_upload_security_validation(client):
    """Ensure empty files, malicious/disallowed extensions, and non-enrolled downloads are blocked."""
    t_token = get_token(client, "prof.alan@univ.edu")
    t_headers = {"Authorization": f"Bearer {t_token}"}

    c_res = client.post("/api/courses", headers=t_headers, json={
        "code": f"SEC_{uuid.uuid4().hex[:6].upper()}",
        "title": "Material Security Course",
        "credits": 3
    })
    course_id = c_res.json()["id"]

    try:
        # 1. Upload empty file (0 bytes) -> 400 Bad Request
        empty_file = ("empty.pdf", BytesIO(b""), "application/pdf")
        res_empty = client.post(
            f"/api/courses/{course_id}/materials/upload",
            headers=t_headers,
            files=[("files", empty_file)]
        )
        assert res_empty.status_code == 400
        assert "empty" in res_empty.json()["detail"].lower()

        # 2. Upload disallowed extension (.exe / .sh) -> 400 Bad Request
        exe_file = ("malware.exe", BytesIO(b"MZ\x90\x00\x03\x00\x00\x00"), "application/x-msdownload")
        res_exe = client.post(
            f"/api/courses/{course_id}/materials/upload",
            headers=t_headers,
            files=[("files", exe_file)]
        )
        assert res_exe.status_code == 400
        assert "unsupported" in res_exe.json()["detail"].lower()

        # 3. Valid PDF upload
        valid_pdf = ("syllabus.pdf", BytesIO(b"%PDF-1.4 Mock valid content for testing"), "application/pdf")
        res_valid = client.post(
            f"/api/courses/{course_id}/materials/upload",
            headers=t_headers,
            files=[("files", valid_pdf)]
        )
        assert res_valid.status_code == 201
        mat_id = res_valid.json()[0]["id"]

        # 4. Non-enrolled student attempts to download -> 403 Forbidden
        student_token = get_token(client, "alex@student.univ.edu")
        s_headers = {"Authorization": f"Bearer {student_token}"}
        dl_res = client.get(f"/api/courses/{course_id}/materials/{mat_id}/download", headers=s_headers)
        assert dl_res.status_code == 403
        assert "enrolled" in dl_res.json()["detail"].lower()
    finally:
        client.delete(f"/api/courses/{course_id}", headers=t_headers)
