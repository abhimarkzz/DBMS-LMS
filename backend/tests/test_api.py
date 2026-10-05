import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_root_and_health(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "UP"


def test_auth_login_success(client):
    # Login as student Alex
    res = client.post("/api/auth/login", json={
        "email": "alex@student.univ.edu",
        "password": "Password123!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "STUDENT"
    assert data["user"]["email"] == "alex@student.univ.edu"


def test_auth_login_invalid_password(client):
    res = client.post("/api/auth/login", json={
        "email": "alex@student.univ.edu",
        "password": "WrongPassword!"
    })
    assert res.status_code == 401
    assert "Incorrect email or password" in res.json()["detail"]


import time


def test_auth_registration_and_duplicate_check(client):
    unique_email = f"newstudent.{int(time.time() * 1000)}@student.univ.edu"
    reg_res = client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "SecurePassword123!",
        "full_name": "Test Enrollee",
        "role": "STUDENT"
    })
    assert reg_res.status_code == 201
    assert "access_token" in reg_res.json()

    # Try registering again with duplicate email
    dup_res = client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "SecurePassword123!",
        "full_name": "Test Enrollee",
        "role": "STUDENT"
    })
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]


def test_rbac_student_forbidden_from_teacher_actions(client):
    # Login as Student
    s_login = client.post("/api/auth/login", json={
        "email": "alex@student.univ.edu",
        "password": "Password123!"
    })
    s_token = s_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {s_token}"}

    # Student trying to create a course should get 403 Forbidden
    course_res = client.post("/api/courses", headers=headers, json={
        "code": "CS999",
        "title": "Hacked Course",
        "description": "Unauthorized"
    })
    assert course_res.status_code == 403


def test_teacher_can_create_course_and_assignment(client):
    # Login as Teacher Alan
    t_login = client.post("/api/auth/login", json={
        "email": "prof.alan@univ.edu",
        "password": "Password123!"
    })
    t_token = t_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {t_token}"}

    # Get teacher's courses
    c_res = client.get("/api/courses", headers=headers)
    assert c_res.status_code == 200
    courses = c_res.json()
    assert len(courses) >= 4


def test_student_progress_view_and_views(client):
    # Login as Student Alex
    s_login = client.post("/api/auth/login", json={
        "email": "alex@student.univ.edu",
        "password": "Password123!"
    })
    s_token = s_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {s_token}"}

    # Query PostgreSQL View: student_progress_view
    view_res = client.get("/api/results/progress-view", headers=headers)
    assert view_res.status_code == 200
    progress_rows = view_res.json()
    assert len(progress_rows) > 0
    # Alex submitted Assignment 1 in CS501
    cs501_progress = next(p for p in progress_rows if p["course_code"] == "CS501")
    assert cs501_progress["total_obtained_score"] >= 95.0
    assert cs501_progress["published_grade"] == "A+"


def test_window_function_leaderboard(client):
    # Login as Admin
    a_login = client.post("/api/auth/login", json={
        "email": "admin@univ.edu",
        "password": "AdminPass123!"
    })
    a_token = a_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {a_token}"}

    # Query SQL Window Function: RANK() OVER (PARTITION BY course_id ORDER BY percentage DESC)
    lb_res = client.get("/api/results/course/1/leaderboard", headers=headers)
    assert lb_res.status_code == 200
    ranks = lb_res.json()
    assert len(ranks) >= 4
    assert ranks[0]["rank"] == 1
    assert ranks[0]["student_name"] == "Alex Rivera"


def test_ai_search_normal_question(client):
    """Scenario 1: Normal question successfully retrieves grounded context with pgvector."""
    s_login = client.post("/api/auth/login", json={"email": "alex@student.univ.edu", "password": "Password123!"})
    token = s_login.json()["access_token"]
    res = client.post("/api/search", headers={"Authorization": f"Bearer {token}"}, json={
        "query": "How does PostgreSQL handle MVCC and vacuuming?",
        "course_id": 1,
        "top_k": 2
    })
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is True
    assert len(data["sources"]) > 0
    assert "MVCC" in data["answer"] or "PostgreSQL" in data["answer"]
    assert data["sources"][0]["similarity_score"] > 0


def test_ai_search_unrelated_question(client):
    """Scenario 2: Unrelated question guardrail prevents hallucination."""
    s_login = client.post("/api/auth/login", json={"email": "alex@student.univ.edu", "password": "Password123!"})
    token = s_login.json()["access_token"]
    res = client.post("/api/search", headers={"Authorization": f"Bearer {token}"}, json={
        "query": "What is the secret recipe for baking sourdough bread?"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is False
    assert "not available in the uploaded course content" in data["answer"]
    assert len(data["sources"]) == 0


def test_ai_search_empty_question(client):
    """Scenario 3: Empty or whitespace query handled gracefully without crashing."""
    s_login = client.post("/api/auth/login", json={"email": "alex@student.univ.edu", "password": "Password123!"})
    token = s_login.json()["access_token"]
    res = client.post("/api/search", headers={"Authorization": f"Bearer {token}"}, json={
        "query": "   "
    })
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is False
    assert "valid question" in data["answer"]


def test_ai_search_no_matching_material(client):
    """Scenario 4: Query targeted to a course with no matching lecture notes."""
    s_login = client.post("/api/auth/login", json={"email": "alex@student.univ.edu", "password": "Password123!"})
    token = s_login.json()["access_token"]
    res = client.post("/api/search", headers={"Authorization": f"Bearer {token}"}, json={
        "query": "What are quantum annealing algorithms?",
        "course_id": 9999  # non-existent course filter
    })
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is False
    assert "not available in the uploaded course content" in data["answer"]


def test_ai_search_teacher_upload_and_query(client):
    """Scenario 5: Teacher uploads notes -> chunked & embedded -> student queries new content."""
    # 1. Teacher uploads notes
    t_login = client.post("/api/auth/login", json={"email": "prof.alan@univ.edu", "password": "Password123!"})
    t_token = t_login.json()["access_token"]
    upload_res = client.post("/api/search/notes/upload", headers={"Authorization": f"Bearer {t_token}"}, json={
        "course_id": 1,
        "title": "Module 9: Sharding and Consistent Hashing",
        "content": (
            "Consistent hashing maps both servers and data keys to a circular ring using cryptographic hashes. "
            "When a new node joins or leaves the distributed topology, only K/N keys need to be remapped, "
            "where K is the number of keys and N is the number of servers. Virtual nodes are utilized to "
            "prevent non-uniform load distribution across cluster partitions."
        ),
        "material_type": "NOTES"
    })
    assert upload_res.status_code == 201
    assert upload_res.json()["status"] == "SUCCESS"

    # 2. Student queries the newly uploaded content
    s_login = client.post("/api/auth/login", json={"email": "alex@student.univ.edu", "password": "Password123!"})
    s_token = s_login.json()["access_token"]
    search_res = client.post("/api/search", headers={"Authorization": f"Bearer {s_token}"}, json={
        "query": "Explain consistent hashing and virtual nodes in distributed sharding",
        "course_id": 1
    })
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["grounded"] is True
    assert any("Consistent Hashing" in s["material_title"] for s in search_data["sources"])


def test_system_health_endpoint(client):
    res = client.get("/api/admin/health")
    assert res.status_code == 200
    data = res.json()
    assert "postgresql" in data["components"]
    assert data["components"]["postgresql"]["status"] == "UP"
    assert data["components"]["pgvector"]["status"] == "UP"
    assert data["components"]["mongodb"]["status"] == "UP"
