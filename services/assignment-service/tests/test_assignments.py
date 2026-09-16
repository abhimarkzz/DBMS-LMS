import uuid
from jose import jwt
from httpx import AsyncClient

from app.core.config import settings

def create_mock_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access"
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

async def test_create_assignment(client: AsyncClient):
    teacher_id = str(uuid.uuid4())
    course_id = str(uuid.uuid4())
    token = create_mock_token(teacher_id, "TEACHER")

    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "title": "Homework 1",
        "description": "Do problems 1-10",
        "total_marks": 100.0,
        "due_date": "2027-12-31T23:59:59Z",
        "course_id": course_id,
        "max_attempts": 2
    }

    response = await client.post("/api/v1/assignments", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Homework 1"
    assert data["course_id"] == course_id
    assert data["created_by"] == teacher_id
    assert "assignment_id" in data

    # Test that a student cannot create an assignment
    student_token = create_mock_token(str(uuid.uuid4()), "STUDENT")
    response_student = await client.post(
        "/api/v1/assignments",
        json=payload,
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert response_student.status_code == 403

async def test_submit_assignment(client: AsyncClient):
    teacher_id = str(uuid.uuid4())
    course_id = str(uuid.uuid4())
    teacher_token = create_mock_token(teacher_id, "TEACHER")

    # 1. Create an assignment (status defaults to DRAFT)
    payload = {
        "title": "Homework 1",
        "total_marks": 100.0,
        "due_date": "2027-12-31T23:59:59Z",
        "course_id": course_id,
    }
    response = await client.post("/api/v1/assignments", json=payload, headers={"Authorization": f"Bearer {teacher_token}"})
    assignment_id = response.json()["assignment_id"]

    # 2. Publish it
    await client.patch(
        f"/api/v1/assignments/{assignment_id}",
        json={"status": "PUBLISHED"},
        headers={"Authorization": f"Bearer {teacher_token}"}
    )

    # 3. Submit as a student
    student_id = str(uuid.uuid4())
    student_token = create_mock_token(student_id, "STUDENT")

    sub_payload = {
        "submission_text": "Here is my homework.",
    }
    sub_response = await client.post(
        f"/api/v1/assignments/{assignment_id}/submissions",
        json=sub_payload,
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert sub_response.status_code == 201
    sub_data = sub_response.json()
    assert sub_data["status"] == "SUBMITTED"
    assert sub_data["attempt_number"] == 1
    assert sub_data["student_id"] == student_id
    submission_id = sub_data["submission_id"]

    # 4. Grade it
    grade_payload = {
        "marks_awarded": 95.0,
        "teacher_feedback": "Great job!",
        "status": "GRADED"
    }
    grade_response = await client.patch(
        f"/api/v1/assignments/submissions/{submission_id}/grade",
        json=grade_payload,
        headers={"Authorization": f"Bearer {teacher_token}"}
    )
    assert grade_response.status_code == 200
    grade_data = grade_response.json()
    assert float(grade_data["marks_awarded"]) == 95.0
    assert grade_data["status"] == "GRADED"
