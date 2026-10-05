import pytest
import time
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.database.postgres import SessionLocal
from app.services.auth_service import create_access_token
from app.models.sql_models import User, Role, Assignment
from app.services.ai_search_service import AISearchService
from app.config import settings

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ============================================================================
# 1. TEST AUTH
# ============================================================================

def test_auth_registration_valid(client):
    email = f"qa_student_{int(time.time() * 1000)}@univ.edu"
    res = client.post("/api/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": "QA Student",
        "role": "STUDENT"
    })
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == email
    assert data["user"]["role"] == "STUDENT"


def test_auth_duplicate_registration(client):
    email = f"qa_dup_{int(time.time() * 1000)}@univ.edu"
    res1 = client.post("/api/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": "QA Dup",
        "role": "STUDENT"
    })
    assert res1.status_code == 201

    res2 = client.post("/api/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": "QA Dup Duplicate",
        "role": "STUDENT"
    })
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"].lower()


def test_auth_valid_login(client):
    res = client.post("/api/auth/login", json={
        "email": "alex@student.univ.edu",
        "password": "Password123!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "alex@student.univ.edu"
    assert data["user"]["role"] == "STUDENT"


def test_auth_invalid_password(client):
    res = client.post("/api/auth/login", json={
        "email": "alex@student.univ.edu",
        "password": "IncorrectPassword999!"
    })
    assert res.status_code == 401
    assert "incorrect email or password" in res.json()["detail"].lower()


def test_auth_invalid_email(client):
    res = client.post("/api/auth/login", json={
        "email": "nonexistent_ghost@univ.edu",
        "password": "Password123!"
    })
    assert res.status_code == 401
    assert "incorrect email or password" in res.json()["detail"].lower()


def test_auth_invalid_and_expired_token(client):
    # Malformed token
    res1 = client.get("/api/auth/me", headers={"Authorization": "Bearer malformed.token.value"})
    assert res1.status_code == 401
    assert "invalid authentication token" in res1.json()["detail"].lower()

    # Expired token simulation
    from datetime import timedelta
    expired_token = create_access_token(
        data={"sub": "1", "email": "alex@student.univ.edu", "role": "STUDENT"},
        expires_delta=timedelta(seconds=-10)
    )
    res2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res2.status_code == 401
    assert "token has expired" in res2.json()["detail"].lower()


def test_auth_role_access_and_unauthorized(client):
    # Student login
    s_login = client.post("/api/auth/login", json={"email": "alex@student.univ.edu", "password": "Password123!"})
    s_token = s_login.json()["access_token"]

    # Teacher login
    t_login = client.post("/api/auth/login", json={"email": "prof.alan@univ.edu", "password": "Password123!"})
    t_token = t_login.json()["access_token"]

    # Admin login
    a_login = client.post("/api/auth/login", json={"email": "admin@univ.edu", "password": "AdminPass123!"})
    a_token = a_login.json()["access_token"]

    # Student verifies own profile
    s_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {s_token}"})
    assert s_me.status_code == 200
    assert s_me.json()["role"] == "STUDENT"

    # Teacher verifies own profile
    t_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {t_token}"})
    assert t_me.status_code == 200
    assert t_me.json()["role"] == "TEACHER"

    # Admin verifies own profile
    a_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {a_token}"})
    assert a_me.status_code == 200
    assert a_me.json()["role"] == "ADMIN"

    # Unauthorized role access: Student attempts to create course (Requires TEACHER/ADMIN)
    unauth_course = client.post("/api/courses", headers={"Authorization": f"Bearer {s_token}"}, json={
        "code": "CS999",
        "title": "Unauthorized Course",
        "description": "Student should not create this"
    })
    assert unauth_course.status_code == 403
    assert "access denied" in unauth_course.json()["detail"].lower()

    # Unauthorized role access: Teacher attempts to view admin health
    unauth_admin = client.get("/api/admin/overview", headers={"Authorization": f"Bearer {t_token}"})
    assert unauth_admin.status_code == 403
    assert "access denied" in unauth_admin.json()["detail"].lower()


# ============================================================================
# 2. TEST STUDENT WORKFLOW
# ============================================================================

def test_student_complete_flow(client):
    # Register/login isolated QA student
    reg = client.post("/api/auth/register", json={
        "email": "qa.studentflow@student.univ.edu",
        "password": "Password123!",
        "full_name": "QA Flow Student",
        "role": "STUDENT"
    })
    if reg.status_code == 201:
        s_token = reg.json()["access_token"]
    else:
        s_login = client.post("/api/auth/login", json={"email": "qa.studentflow@student.univ.edu", "password": "Password123!"})
        s_token = s_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {s_token}"}

    # 1. Dashboard & Profile
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "qa.studentflow@student.univ.edu"

    # 2. Browse Courses

    courses = client.get("/api/courses", headers=headers)
    assert courses.status_code == 200
    course_list = courses.json()
    assert len(course_list) >= 4

    # 3. Enrollment in a course
    target_course = course_list[0]
    enroll_res = client.post(f"/api/courses/{target_course['id']}/enroll", headers=headers)
    assert enroll_res.status_code in [200, 201]

    # 4. Course Access (details and syllabus)
    course_detail = client.get(f"/api/courses/{target_course['id']}", headers=headers)
    assert course_detail.status_code == 200
    detail_data = course_detail.json()
    assert detail_data["code"] == target_course["code"]
    assert "materials" in detail_data

    # 5. Study Material
    materials = detail_data["materials"]
    assert len(materials) > 0
    assert "content" in materials[0]

    # 6. Assignment View
    assignments_res = client.get("/api/assignments", headers=headers)
    assert assignments_res.status_code == 200
    assignments = assignments_res.json()
    assert len(assignments) > 0

    # 7. Assignment Submission (find assignment in enrolled course, or enroll first)
    course_assignments = [a for a in assignments if a.get("course_id") == target_course["id"]]
    if course_assignments:
        target_assign = course_assignments[0]
    else:
        target_assign = assignments[0]
        client.post(f"/api/courses/{target_assign['course_id']}/enroll", headers=headers)
        
    assign_id = target_assign["id"]
    sub_res = client.post(f"/api/assignments/{assign_id}/submit", headers=headers, json={
        "content": "QA student comprehensive query optimization and index benchmarks.",
        "file_url": "https://github.com/alex/dbms-assignment"
    })
    assert sub_res.status_code in [200, 201]
    assert sub_res.json()["status"] in ["SUBMITTED", "GRADED"]


    # 8. Results & Views
    progress_res = client.get("/api/results/progress-view", headers=headers)
    assert progress_res.status_code == 200
    progress = progress_res.json()
    assert isinstance(progress, list)

    leaderboard_res = client.get(f"/api/results/course/{target_course['id']}/leaderboard", headers=headers)
    assert leaderboard_res.status_code == 200
    assert isinstance(leaderboard_res.json(), list)

    # 9. Notifications
    notifs_res = client.get("/api/notifications", headers=headers)
    assert notifs_res.status_code == 200
    notifs = notifs_res.json()
    assert isinstance(notifs, list)

    # 10. AI Smart Search
    ai_res = client.post("/api/search", headers=headers, json={
        "query": "How does PostgreSQL handle MVCC and vacuuming?",
        "course_id": target_course["id"]
    })
    assert ai_res.status_code == 200
    ai_data = ai_res.json()
    assert "answer" in ai_data
    assert "grounded" in ai_data


# ============================================================================
# 3. TEST TEACHER WORKFLOW
# ============================================================================

def test_teacher_complete_flow(client):
    t_login = client.post("/api/auth/login", json={"email": "prof.alan@univ.edu", "password": "Password123!"})
    t_token = t_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {t_token}"}

    # 1. Dashboard: teacher profile
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "TEACHER"

    # 2. Create Course
    unique_code = f"QA{int(time.time()) % 10000}"
    create_course_res = client.post("/api/courses", headers=headers, json={
        "code": unique_code,
        "title": "QA Test Distributed Systems",
        "description": "Comprehensive QA verified curriculum",
        "syllabus": "Unit 1: Concurrency. Unit 2: Consensus."
    })
    assert create_course_res.status_code == 201
    course_id = create_course_res.json()["id"]

    # 3. Add Material & Vectorize
    mat_res = client.post("/api/search/notes/upload", headers=headers, json={
        "course_id": course_id,
        "title": "Module 1: Write-Ahead Logging Mechanisms",
        "content": (
            "Write-Ahead Logging (WAL) ensures database durability and atomicity by requiring that "
            "changes to data pages are logged to stable storage before the dirty pages are flushed to disk. "
            "ARIES recovery algorithms utilize WAL records during crash recovery."
        ),
        "material_type": "NOTES"
    })
    assert mat_res.status_code == 201
    assert mat_res.json()["status"] == "SUCCESS"

    # 4. Create Assignment
    assign_res = client.post("/api/assignments", headers=headers, json={
        "course_id": course_id,
        "title": "WAL Benchmark Analysis",
        "description": "Evaluate synchronous_commit settings in PostgreSQL.",
        "max_score": 100
    })
    assert assign_res.status_code == 201
    assign_id = assign_res.json()["id"]

    # Student submits to this assignment
    s_login = client.post("/api/auth/login", json={"email": "marcus@student.univ.edu", "password": "Password123!"})
    s_token = s_login.json()["access_token"]
    # Enroll student in course
    client.post(f"/api/courses/{course_id}/enroll", headers={"Authorization": f"Bearer {s_token}"})
    # Submit assignment
    sub_res = client.post(f"/api/assignments/{assign_id}/submit", headers={"Authorization": f"Bearer {s_token}"}, json={
        "content": "Evaluating WAL fsync rates and disk throughput latency."
    })
    assert sub_res.status_code in [200, 201]

    # 5. Teacher Views Submissions
    subs_list_res = client.get(f"/api/assignments/{assign_id}/submissions", headers=headers)
    assert subs_list_res.status_code == 200
    subs_list = subs_list_res.json()
    assert len(subs_list) > 0
    submission_id = subs_list[0]["id"]

    # 6. Evaluate / Grade Submission
    grade_res = client.post(f"/api/assignments/submissions/{submission_id}/grade", headers=headers, json={
        "score": 95,
        "feedback": "Outstanding WAL throughput benchmarks and clean recovery analysis."
    })
    assert grade_res.status_code == 200
    graded_data = grade_res.json()
    assert graded_data["score"] == 95
    assert graded_data["status"] == "GRADED"

    # 7. Verify result published via DB trigger & view
    summary_res = client.get("/api/results/course-summary-view", headers=headers)
    assert summary_res.status_code == 200
    summaries = summary_res.json()
    matching_summary = next((s for s in summaries if s["course_id"] == course_id), None)
    if matching_summary:
        assert matching_summary["total_submissions_graded"] >= 1


# ============================================================================
# 4. TEST ADMIN WORKFLOW
# ============================================================================

def test_admin_complete_flow(client):
    a_login = client.post("/api/auth/login", json={"email": "admin@univ.edu", "password": "AdminPass123!"})
    a_token = a_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {a_token}"}

    # 1. Users Directory
    users_res = client.get("/api/users", headers=headers)
    assert users_res.status_code == 200
    users = users_res.json()
    assert len(users) >= 5

    # 2. Roles Verification
    roles_in_system = {u["role"] for u in users}
    assert "STUDENT" in roles_in_system
    assert "TEACHER" in roles_in_system
    assert "ADMIN" in roles_in_system

    # 3. Courses Oversight
    courses_res = client.get("/api/courses", headers=headers)
    assert courses_res.status_code == 200
    assert len(courses_res.json()) >= 4

    # 4. Activity & Platform Overview
    health_res = client.get("/api/admin/health", headers=headers)
    assert health_res.status_code == 200
    health = health_res.json()
    assert health["components"]["postgresql"]["status"] == "UP"
    assert health["components"]["pgvector"]["status"] == "UP"
    assert health["components"]["mongodb"]["status"] == "UP"
    assert health["components"]["redis"]["status"] == "UP"

    overview_res = client.get("/api/admin/overview", headers=headers)
    assert overview_res.status_code == 200
    overview = overview_res.json()
    assert "metrics" in overview
    assert "recent_activities" in overview
    assert overview["metrics"]["total_users"] >= 5


# ============================================================================
# 5. TEST DATABASE CONSTRAINTS, RELATIONSHIPS, TRANSACTIONS, OPERATIONS
# ============================================================================

def test_database_constraints_and_relationships():
    db = SessionLocal()
    try:
        # 1. Unique constraint on user email
        user_email = f"constraint_test_{int(time.time() * 1000)}@univ.edu"
        role_student = db.query(Role).filter(Role.name == "STUDENT").first()
        u1 = User(email=user_email, password_hash="dummyhash", full_name="User 1", role_id=role_student.id)
        db.add(u1)
        db.commit()

        # Duplicate email should violate unique constraint
        u2 = User(email=user_email, password_hash="dummyhash", full_name="User 2", role_id=role_student.id)
        db.add(u2)
        with pytest.raises(Exception):
            db.commit()
        db.rollback()

        # 2. Foreign Key relationship
        # Adding an assignment to a non-existent course_id
        invalid_assignment = Assignment(course_id=999999, title="Invalid Course FK", max_score=100)
        db.add(invalid_assignment)
        with pytest.raises(Exception):
            db.commit()
        db.rollback()

        # 3. Transaction rollback test
        try:
            with db.begin_nested():
                # Invalid query within nested savepoint
                db.execute(text("INSERT INTO enrollments (user_id, course_id) VALUES (999999, 999999)"))
        except Exception:
            pass  # Expected rollback
        
        # Verify db session is still valid after rollback
        alive_check = db.execute(text("SELECT 1")).scalar()
        assert alive_check == 1

        # 4. PostgreSQL Views & pgvector index check
        views = db.execute(text("""
            SELECT table_name FROM information_schema.views 
            WHERE table_schema = 'public' 
            AND table_name IN ('student_progress_view', 'course_result_summary_view');
        """)).fetchall()
        view_names = {v[0] for v in views}
        assert "student_progress_view" in view_names
        assert "course_result_summary_view" in view_names

        # 5. Check pgvector extension and HNSW index existence
        pgvector_ext = db.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector';")).scalar()
        assert pgvector_ext == "vector"

        indexes = db.execute(text("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'note_chunks';
        """)).fetchall()
        index_names = {idx[0] for idx in indexes}
        assert any("embedding" in name for name in index_names)

    finally:
        db.close()


def test_mongodb_operations():
    from pymongo import MongoClient
    client = MongoClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    test_id = str(uuid.uuid4())
    doc = {
        "test_id": test_id,
        "user_name": "QA Tester",
        "action": "AUTOMATED_QA_TEST",
        "timestamp": time.time()
    }
    ins = db.activity_logs.insert_one(doc)
    assert ins.inserted_id is not None
    found = db.activity_logs.find_one({"test_id": test_id})
    assert found is not None
    assert found["action"] == "AUTOMATED_QA_TEST"
    db.activity_logs.delete_one({"test_id": test_id})
    client.close()


def test_pgvector_cosine_search_operation():
    db = SessionLocal()
    try:
        from app.repositories.note_chunk_repo import NoteChunkRepository
        repo = NoteChunkRepository(db)
        
        # Search with a test 768-d vector
        test_vec = [0.01] * 768
        chunks = repo.search_similar_chunks(query_vector=test_vec, top_k=2)
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert "similarity_score" in chunks[0]
        assert "chunk_text" in chunks[0]
    finally:
        db.close()


# ============================================================================
# 6. TEST AI SEARCH (GROUNDING, GUARDRAILS, ERROR HANDLING, GEMINI FALLBACK)
# ============================================================================

def test_ai_valid_question_grounded_answer(client):
    s_login = client.post("/api/auth/login", json={"email": "alex@student.univ.edu", "password": "Password123!"})
    token = s_login.json()["access_token"]
    res = client.post("/api/search", headers={"Authorization": f"Bearer {token}"}, json={
        "query": "How does PostgreSQL handle MVCC and vacuuming?",
        "course_id": 1
    })
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is True
    assert len(data["sources"]) > 0
    assert len(data["answer"]) > 20


def test_ai_question_with_no_result(client):
    s_login = client.post("/api/auth/login", json={"email": "alex@student.univ.edu", "password": "Password123!"})
    token = s_login.json()["access_token"]
    res = client.post("/api/search", headers={"Authorization": f"Bearer {token}"}, json={
        "query": "What are quantum annealing algorithms?",
        "course_id": 99999  # Non-existent course filter
    })
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is False
    assert "not available in the uploaded course content" in data["answer"].lower()


def test_ai_unrelated_question_guardrail(client):
    s_login = client.post("/api/auth/login", json={"email": "alex@student.univ.edu", "password": "Password123!"})
    token = s_login.json()["access_token"]
    res = client.post("/api/search", headers={"Authorization": f"Bearer {token}"}, json={
        "query": "What is the secret recipe for baking sourdough bread?"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is False
    assert "not available in the uploaded course content" in data["answer"].lower()


def test_ai_empty_question_validation(client):
    s_login = client.post("/api/auth/login", json={"email": "alex@student.univ.edu", "password": "Password123!"})
    token = s_login.json()["access_token"]
    res = client.post("/api/search", headers={"Authorization": f"Bearer {token}"}, json={
        "query": "   "
    })
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is False
    assert "provide a valid question" in data["answer"].lower()


def test_ai_gemini_api_failure_graceful_fallback(client):
    """Simulate Gemini API timeout or exception to verify deterministic fallback answers."""
    s_login = client.post("/api/auth/login", json={"email": "alex@student.univ.edu", "password": "Password123!"})
    token = s_login.json()["access_token"]

    # Mock genai to simulate an API failure
    with patch("app.services.ai_search_service.settings.GEMINI_API_KEY", "mock_key"):
        with patch("google.genai.Client", side_effect=Exception("API Quota Exceeded")):
            res = client.post("/api/search", headers={"Authorization": f"Bearer {token}"}, json={
                "query": "How does PostgreSQL handle MVCC and vacuuming?",
                "course_id": 1
            })
            assert res.status_code == 200
            data = res.json()
            assert "answer" in data
            assert len(data["answer"]) > 10


def test_ai_vector_database_failure_graceful_handling():
    """Verify that if the database has an issue, the service handles it without unhandled crashes."""
    mock_db = MagicMock()
    mock_db.execute.side_effect = Exception("Simulated DB Connection Drop")
    service = AISearchService(mock_db)
    chunks = service.chunk_repo.search_similar_chunks([0.1] * 768)
    assert chunks == []
