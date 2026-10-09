import io
import json
import uuid
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.database.postgres import SessionLocal
from app.models.sql_models import User, Role, Course, Assignment, Submission, Result


@pytest.fixture
def client():
    return TestClient(app)


def get_token(client, email, password):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def test_mcq_automatic_grading(client):
    """Teacher creates an MCQ quiz with questions, options, marks, and explanations. Student submits and score is automatically calculated."""
    teacher_token = get_token(client, "prof.alan@univ.edu", "Password123!")
    student_token = get_token(client, "alex@student.univ.edu", "Password123!")
    t_headers = {"Authorization": f"Bearer {teacher_token}"}
    s_headers = {"Authorization": f"Bearer {student_token}"}

    # 1. Create course
    code = f"MCQ_{uuid.uuid4().hex[:6].upper()}"
    course_res = client.post("/api/courses", headers=t_headers, json={
        "code": code,
        "title": "Database Architecture Quiz Lab",
        "credits": 3,
        "description": "Lab course with auto-graded quizzes"
    })
    course_id = course_res.json()["id"]

    # Enroll Alex
    client.post(f"/api/courses/{course_id}/enroll", headers=s_headers)

    # 2. Create MCQ Assessment with 2 questions (5 pts each = 10 pts max)
    mcq_config = {
        "questions": [
            {
                "id": "q1",
                "question": "Which isolation level prevents phantom reads?",
                "options": [
                    {"key": "A", "text": "Read Committed"},
                    {"key": "B", "text": "Read Uncommitted"},
                    {"key": "C", "text": "Serializable"},
                    {"key": "D", "text": "Repeatable Read"}
                ],
                "correct_answer": "C",
                "marks": 5.0,
                "explanation": "Serializable isolation ensures complete transaction isolation without phantom reads."
            },
            {
                "id": "q2",
                "question": "What is the primary log mechanism in ARIES?",
                "options": [
                    {"key": "A", "text": "Write-Ahead Logging (WAL)"},
                    {"key": "B", "text": "Shadow Paging"},
                    {"key": "C", "text": "Two-Phase Commit"},
                    {"key": "D", "text": "Checkpoint Only"}
                ],
                "correct_answer": "A",
                "marks": 5.0,
                "explanation": "ARIES strictly enforces WAL protocol before updating dirty pages."
            }
        ],
        "shuffle_questions": False,
        "shuffle_options": False
    }

    create_res = client.post("/api/assignments", headers=t_headers, json={
        "course_id": course_id,
        "title": "DBMS Concurrency & Recovery Quiz",
        "description": "Auto-graded multiple-choice assessment on ACID transactions and ARIES.",
        "instructions": "Select one best answer for each question. Submissions are automatically evaluated upon completion.",
        "max_score": 10.0,
        "assessment_type": "MCQ",
        "assessment_config": json.dumps(mcq_config),
        "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat()
    })
    assert create_res.status_code == 201
    assign_id = create_res.json()["id"]
    assert create_res.json()["assessment_type"] == "MCQ"

    # 3. Student submits: Q1 correct ("C"), Q2 wrong ("B") -> expected score: 5.0 / 10.0
    student_answers = {"q1": "C", "q2": "B"}
    sub_res = client.post(f"/api/assignments/{assign_id}/submit", headers=s_headers, json={
        "content": "Submitted my quiz answers",
        "mcq_answers": json.dumps(student_answers),
        "submission_type": "MCQ"
    })
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert sub_data["status"] == "GRADED"
    assert sub_data["grade_status"] == "PUBLISHED"
    assert sub_data["score"] == 5.0
    assert "Automated Quiz Evaluation" in sub_data["feedback"]
    assert "Correct (+5.0 pts)" in sub_data["feedback"]


def test_descriptive_grading_and_rubric_validation(client):
    """Tests descriptive assessment creation with rubrics, manual grading, missing rubric errors, and score bounds."""
    teacher_token = get_token(client, "prof.alan@univ.edu", "Password123!")
    student_token = get_token(client, "alex@student.univ.edu", "Password123!")
    t_headers = {"Authorization": f"Bearer {teacher_token}"}
    s_headers = {"Authorization": f"Bearer {student_token}"}

    # Course
    code = f"DESC_{uuid.uuid4().hex[:6].upper()}"
    c_res = client.post("/api/courses", headers=t_headers, json={
        "code": code,
        "title": "Advanced Distributed Systems",
        "credits": 4,
        "description": "Descriptive case studies"
    })
    course_id = c_res.json()["id"]
    client.post(f"/api/courses/{course_id}/enroll", headers=s_headers)

    # Descriptive assignment with rubric criteria
    rubric = [
        {"id": "c1", "name": "System Architecture & Design", "max_marks": 50.0, "description": "Clarity of partition handling and consensus design."},
        {"id": "c2", "name": "Fault Tolerance & Raft Protocol", "max_marks": 50.0, "description": "Correct implementation of leader election and log replication."}
    ]
    assign_res = client.post("/api/assignments", headers=t_headers, json={
        "course_id": course_id,
        "title": "Distributed Consensus Case Study",
        "description": "Explain how Paxos and Raft achieve linearizability in asynchronous networks.",
        "instructions": "Submit comprehensive technical paper with at least 500 words.",
        "max_score": 100.0,
        "assessment_type": "DESCRIPTIVE",
        "assessment_config": json.dumps({"rubric": rubric})
    })
    assert assign_res.status_code == 201
    assign_id = assign_res.json()["id"]

    # Student submits descriptive text
    sub_res = client.post(f"/api/assignments/{assign_id}/submit", headers=s_headers, json={
        "content": "In Paxos and Raft, safety is prioritized over liveness under network partitions. Raft utilizes randomized election timeouts to prevent split votes...",
        "submission_type": "TEXT"
    })
    assert sub_res.status_code == 200
    submission_id = sub_res.json()["id"]
    assert sub_res.json()["status"] == "SUBMITTED"

    # Test 1: Invalid score < 0
    neg_res = client.post(f"/api/assignments/submissions/{submission_id}/grade", headers=t_headers, json={
        "score": -5.0,
        "feedback": "Negative score is invalid"
    })
    assert neg_res.status_code in [400, 422]

    # Test 2: Invalid score > max_score (105 > 100)
    over_res = client.post(f"/api/assignments/submissions/{submission_id}/grade", headers=t_headers, json={
        "score": 105.0,
        "feedback": "Score exceeds max"
    })
    assert over_res.status_code == 400
    assert "between 0 and 100" in over_res.json()["detail"]

    # Test 3: Missing rubric marks (teacher submits score without scoring required rubric criteria)
    missing_rubric_res = client.post(f"/api/assignments/submissions/{submission_id}/grade", headers=t_headers, json={
        "score": 88.0,
        "feedback": "Good job",
        "rubric_evaluation": json.dumps({"criteria_scores": {"c1": 45.0}})  # missing c2
    })
    assert missing_rubric_res.status_code == 400
    assert "Missing score for rubric criterion" in missing_rubric_res.json()["detail"]

    # Test 4: Valid evaluation with complete rubric
    valid_rubric = {
        "criteria_scores": {"c1": 46.0, "c2": 44.0},
        "criteria_feedback": {"c1": "Thorough linearizability discussion", "c2": "Clear Raft RPC diagrams"}
    }
    grade_res = client.post(f"/api/assignments/submissions/{submission_id}/grade", headers=t_headers, json={
        "score": 90.0,
        "feedback": "Outstanding architectural depth.",
        "rubric_evaluation": json.dumps(valid_rubric),
        "publish": True
    })
    assert grade_res.status_code == 200
    graded_data = grade_res.json()
    assert graded_data["score"] == 90.0
    assert graded_data["status"] == "GRADED"
    assert graded_data["grade_status"] == "PUBLISHED"


def test_file_and_audio_submission_and_streaming(client):
    """Tests file upload (PDF/code) and audio submission with playback streaming endpoint."""
    teacher_token = get_token(client, "prof.alan@univ.edu", "Password123!")
    student_token = get_token(client, "alex@student.univ.edu", "Password123!")
    t_headers = {"Authorization": f"Bearer {teacher_token}"}
    s_headers = {"Authorization": f"Bearer {student_token}"}

    # Course
    code = f"AUD_{uuid.uuid4().hex[:6].upper()}"
    c_res = client.post("/api/courses", headers=t_headers, json={
        "code": code,
        "title": "Audio Signal Processing & Multimedia DBs",
        "credits": 3,
        "description": "Audio and binary file lab assessments"
    })
    course_id = c_res.json()["id"]
    client.post(f"/api/courses/{course_id}/enroll", headers=s_headers)

    # 1. File Submission Assignment (with extensions: [.pdf, .zip])
    file_assign = client.post("/api/assignments", headers=t_headers, json={
        "course_id": course_id,
        "title": "Lab Report File Submission",
        "description": "Upload final PDF report with performance benchmarks.",
        "assessment_type": "FILE",
        "max_score": 50.0,
        "assessment_config": json.dumps({
            "allowed_extensions": [".pdf", ".zip"],
            "max_file_size_mb": 10
        })
    }).json()

    # Upload PDF file
    pdf_bytes = b"%PDF-1.4 Mock PDF Content with database benchmarks"
    file_payload = {"file": ("report.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    sub_file_res = client.post(f"/api/assignments/{file_assign['id']}/submit-file", headers=s_headers, files=file_payload, data={"notes": "Attached benchmark report"})
    assert sub_file_res.status_code == 200
    file_sub = sub_file_res.json()
    assert file_sub["submission_type"] == "FILE"
    assert file_sub["file_name"] == "report.pdf"
    assert file_sub["file_storage_id"] is not None

    # Verify streaming/download endpoint
    stream_res = client.get(f"/api/assignments/submissions/{file_sub['id']}/file", headers=t_headers)
    assert stream_res.status_code == 200
    assert stream_res.content == pdf_bytes

    # 2. Audio Submission Assignment
    audio_assign = client.post("/api/assignments", headers=t_headers, json={
        "course_id": course_id,
        "title": "Audio Oral Defense Recording",
        "description": "Record 3-minute oral defense explaining your database design.",
        "assessment_type": "AUDIO",
        "max_score": 50.0,
        "assessment_config": json.dumps({
            "allowed_audio_formats": [".mp3", ".wav", ".m4a", ".webm"],
            "max_duration_mins": 5
        })
    }).json()

    # Upload Mock MP3 audio
    mock_audio_bytes = b"ID3\x03\x00\x00\x00\x00\x00Mock Audio Binary Recording Stream Data"
    audio_payload = {"file": ("defense.mp3", io.BytesIO(mock_audio_bytes), "audio/mpeg")}
    sub_audio_res = client.post(f"/api/assignments/{audio_assign['id']}/submit-file", headers=s_headers, files=audio_payload, data={"notes": "Oral defense audio"})
    assert sub_audio_res.status_code == 200
    audio_sub = sub_audio_res.json()
    assert audio_sub["submission_type"] == "AUDIO"
    assert audio_sub["file_name"] == "defense.mp3"

    # Verify audio streaming endpoint for browser <audio controls>
    audio_stream_res = client.get(f"/api/assignments/submissions/{audio_sub['id']}/file", headers=t_headers)
    assert audio_stream_res.status_code == 200
    assert audio_stream_res.headers["content-type"].startswith("audio/")
    assert audio_stream_res.content == mock_audio_bytes


def test_draft_saving_vs_publishing_and_regrading(client):
    """Tests Save Grade (draft) which does NOT update student gradebook vs Publish Grade which executes triggers and sends notifications."""
    teacher_token = get_token(client, "prof.alan@univ.edu", "Password123!")
    student_token = get_token(client, "alex@student.univ.edu", "Password123!")
    t_headers = {"Authorization": f"Bearer {teacher_token}"}
    s_headers = {"Authorization": f"Bearer {student_token}"}

    code = f"PUB_{uuid.uuid4().hex[:6].upper()}"
    c_res = client.post("/api/courses", headers=t_headers, json={
        "code": code,
        "title": "Assessment Publishing & Gradebook Workflows",
        "credits": 3,
        "description": "Validating separate draft saving vs publishing"
    })
    course_id = c_res.json()["id"]
    client.post(f"/api/courses/{course_id}/enroll", headers=s_headers)

    assign_res = client.post("/api/assignments", headers=t_headers, json={
        "course_id": course_id,
        "title": "Term Project Milestone 1",
        "description": "Database Schema and ER Diagram",
        "max_score": 100.0,
        "assessment_type": "DESCRIPTIVE"
    })
    assign_id = assign_res.json()["id"]

    # Student submits
    sub_res = client.post(f"/api/assignments/{assign_id}/submit", headers=s_headers, json={
        "content": "ER Model includes 12 entities with 3NF normalized relations and check constraints.",
        "submission_type": "TEXT"
    })
    sub_id = sub_res.json()["id"]

    # 1. Teacher clicks "Save Grade" (publish = False) -> Draft Evaluation
    draft_res = client.post(f"/api/assignments/submissions/{sub_id}/grade", headers=t_headers, json={
        "score": 85.0,
        "feedback": "Solid 3NF normalization. Draft feedback.",
        "publish": False
    })
    assert draft_res.status_code == 200
    draft_sub = draft_res.json()
    assert draft_sub["score"] == 85.0
    assert draft_sub["status"] == "EVALUATED"
    assert draft_sub["grade_status"] == "DRAFT"

    # Verify that results table does NOT have a published result for this course yet
    res_check = client.get("/api/results/my", headers=s_headers)
    my_results = res_check.json()
    draft_result = next((r for r in my_results if r["course_id"] == course_id), None)
    # Draft should not be published or total_score is not counting unapproved draft
    if draft_result:
        assert float(draft_result["total_score"]) == 0.0 or draft_result["grade"] == "F"

    # 2. Regrading while in draft: teacher reviews and updates score to 92.0
    regrade_res = client.post(f"/api/assignments/submissions/{sub_id}/grade", headers=t_headers, json={
        "score": 92.0,
        "feedback": "Reviewed index choices. Upgraded to 92.",
        "publish": False
    })
    assert regrade_res.status_code == 200
    assert regrade_res.json()["score"] == 92.0

    # 3. Teacher clicks "Publish Grade" (or /publish endpoint)
    pub_res = client.post(f"/api/assignments/submissions/{sub_id}/publish", headers=t_headers)
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert pub_data["status"] == "GRADED"
    assert pub_data["grade_status"] == "PUBLISHED"

    # 4. Check results page updates immediately via database calculation
    results_after = client.get("/api/results/my", headers=s_headers).json()
    course_res = next((r for r in results_after if r["course_id"] == course_id), None)
    assert course_res is not None
    assert float(course_res["total_score"]) == 92.0
    assert float(course_res["percentage"]) == 92.0
    assert course_res["grade"] == "A+"

    # 5. Check student received notification after publish
    notifs = client.get("/api/notifications", headers=s_headers).json()
    grade_notif = next((n for n in notifs if "Milestone 1" in n.get("message", "") or "Grade Published" in n.get("title", "")), None)
    assert grade_notif is not None
