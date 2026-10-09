import io
import pytest
import pypdf
import docx
import pptx
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import create_access_token
from app.database.postgres import SessionLocal
from app.models.sql_models import User, Course, StudyMaterial, NoteChunk, Role

client = TestClient(app)


from sqlalchemy.orm import joinedload

def get_token_for_user(email: str) -> str:
    db = SessionLocal()
    user = db.query(User).options(joinedload(User.role)).filter(User.email == email).first()
    assert user is not None, f"User {email} not found"
    role_name = user.role.name if user.role else "STUDENT"
    token = create_access_token({"sub": str(user.id), "email": user.email, "role": role_name})
    db.close()
    return token


@pytest.fixture(scope="module")
def teacher_auth():
    token = get_token_for_user("prof.alan@univ.edu")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def student_auth():
    token = get_token_for_user("alex@student.univ.edu")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def other_teacher_auth():
    token = get_token_for_user("dr.sarah@univ.edu")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def target_course_id():
    db = SessionLocal()
    teacher = db.query(User).filter(User.email == "prof.alan@univ.edu").first()
    course = db.query(Course).filter(Course.teacher_id == teacher.id).first() if teacher else None
    if not course:
        course = db.query(Course).first()
    course_id = course.id
    db.close()
    return course_id


@pytest.fixture(autouse=True)
def cleanup_test_materials(target_course_id):
    def _clean():
        db = SessionLocal()
        test_filenames = [
            "consensus_raft.txt", "btree_guide.md", "postgres_internals.docx",
            "query_optimization_slides.pptx", "deadlock_detection.pdf",
            "unique_lecture_notes.txt", "reindex_target.txt", "corrupt_sample.pdf"
        ]
        materials = db.query(StudyMaterial).filter(
            StudyMaterial.course_id == target_course_id,
            StudyMaterial.original_filename.in_(test_filenames)
        ).all()
        for m in materials:
            db.delete(m)
        db.commit()
        db.close()
    _clean()
    yield
    _clean()


def test_study_material_unsupported_format(teacher_auth, target_course_id):
    """Attempting to upload an unsupported format (.xyz / .exe) must return 400 Bad Request."""
    file_bytes = b"Some random binary executable data"
    files = {"files": ("malicious_program.exe", file_bytes, "application/octet-stream")}
    res = client.post(f"/api/courses/{target_course_id}/materials/upload", files=files, headers=teacher_auth)
    assert res.status_code == 400
    assert "Unsupported file format" in res.json()["detail"]


def test_study_material_empty_file(teacher_auth, target_course_id):
    """Uploading an empty file (0 bytes) must return 400 Bad Request."""
    files = {"files": ("empty_notes.txt", b"", "text/plain")}
    res = client.post(f"/api/courses/{target_course_id}/materials/upload", files=files, headers=teacher_auth)
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()


def test_study_material_course_ownership(other_teacher_auth, target_course_id):
    """A teacher who does not instruct the course cannot upload materials (403 Forbidden)."""
    files = {"files": ("unauthorized_notes.txt", b"Lecture content for other class", "text/plain")}
    res = client.post(f"/api/courses/{target_course_id}/materials/upload", files=files, headers=other_teacher_auth)
    assert res.status_code == 403
    assert "permission" in res.json()["detail"].lower()


def test_upload_txt_study_material(teacher_auth, target_course_id):
    """Upload TXT file: should parse, clean, store in MongoDB, chunk and index in pgvector."""
    content = "Distributed Consensus Algorithms\n\nRAFT is a consensus algorithm that is designed to be easy to understand."
    files = {"files": ("consensus_raft.txt", content.encode("utf-8"), "text/plain")}
    res = client.post(f"/api/courses/{target_course_id}/materials/upload", files=files, headers=teacher_auth)
    assert res.status_code == 201
    data = res.json()
    assert len(data) == 1
    item = data[0]
    assert item["file_type"] == "TXT"
    assert item["original_filename"] == "consensus_raft.txt"
    assert item["status"] == "INDEXED"
    assert item["chunk_count"] > 0
    mat_id = item["id"]

    # Verify download
    res_dl = client.get(f"/api/courses/{target_course_id}/materials/{mat_id}/download", headers=teacher_auth)
    assert res_dl.status_code == 200
    assert b"Distributed Consensus" in res_dl.content

    # Cleanup
    client.delete(f"/api/courses/{target_course_id}/materials/{mat_id}", headers=teacher_auth)


def test_upload_md_study_material(teacher_auth, target_course_id):
    """Upload Markdown file: should parse, chunk, and index."""
    md_content = "# B-Tree Indexing\n\nB-Trees keep data sorted and allow searches, sequential access, insertions, and deletions in logarithmic time."
    files = {"files": ("btree_guide.md", md_content.encode("utf-8"), "text/markdown")}
    res = client.post(f"/api/courses/{target_course_id}/materials/upload", files=files, headers=teacher_auth)
    assert res.status_code == 201
    item = res.json()[0]
    assert item["file_type"] == "MD"
    assert item["status"] == "INDEXED"
    assert item["chunk_count"] > 0

    # Cleanup
    client.delete(f"/api/courses/{target_course_id}/materials/{item['id']}", headers=teacher_auth)


def test_upload_docx_study_material(teacher_auth, target_course_id):
    """Upload DOCX file: should parse paragraphs and index."""
    doc = docx.Document()
    doc.add_heading("PostgreSQL Storage Internals", level=1)
    doc.add_paragraph("PostgreSQL uses a multi-version concurrency control (MVCC) model to ensure transaction isolation.")
    doc_io = io.BytesIO()
    doc.save(doc_io)
    docx_bytes = doc_io.getvalue()

    files = {"files": ("postgres_internals.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    res = client.post(f"/api/courses/{target_course_id}/materials/upload", files=files, headers=teacher_auth)
    assert res.status_code == 201
    item = res.json()[0]
    assert item["file_type"] == "DOCX"
    assert item["status"] == "INDEXED"
    assert item["chunk_count"] > 0

    # Cleanup
    client.delete(f"/api/courses/{target_course_id}/materials/{item['id']}", headers=teacher_auth)


def test_upload_pptx_study_material(teacher_auth, target_course_id):
    """Upload PPTX presentation: should parse slide titles/text and index."""
    prs = pptx.Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "Relational Algebra & Query Trees"
    slide.placeholders[1].text = "Selection, Projection, Join, Set Union, and Cartesian Product are fundamental relational operators."
    pptx_io = io.BytesIO()
    prs.save(pptx_io)
    pptx_bytes = pptx_io.getvalue()

    files = {"files": ("query_optimization_slides.pptx", pptx_bytes, "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
    res = client.post(f"/api/courses/{target_course_id}/materials/upload", files=files, headers=teacher_auth)
    assert res.status_code == 201
    item = res.json()[0]
    assert item["file_type"] == "PPTX"
    assert item["status"] == "INDEXED"
    assert item["chunk_count"] > 0

    # Cleanup
    client.delete(f"/api/courses/{target_course_id}/materials/{item['id']}", headers=teacher_auth)


def test_upload_pdf_study_material(teacher_auth, target_course_id):
    """Upload PDF document: should extract page text and index."""
    pdf_content = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 67 >> stream
BT
/F1 12 Tf
72 712 Td
(Concurrency Control and Deadlock Detection Techniques) Tj
ET
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000242 00000 n 
0000000360 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
437
%%EOF"""

    files = {"files": ("deadlock_detection.pdf", pdf_content, "application/pdf")}
    res = client.post(f"/api/courses/{target_course_id}/materials/upload", files=files, headers=teacher_auth)
    assert res.status_code == 201
    item = res.json()[0]
    assert item["file_type"] == "PDF"
    assert item["status"] == "INDEXED"
    assert item["chunk_count"] > 0

    # Cleanup
    client.delete(f"/api/courses/{target_course_id}/materials/{item['id']}", headers=teacher_auth)


def test_duplicate_upload_rejection(teacher_auth, target_course_id):
    """Attempting to upload a file with the same filename twice in the same course must return 409 Conflict."""
    files = {"files": ("unique_lecture_notes.txt", b"Unique lecture content.", "text/plain")}
    res1 = client.post(f"/api/courses/{target_course_id}/materials/upload", files=files, headers=teacher_auth)
    assert res1.status_code == 201
    mat_id = res1.json()[0]["id"]

    try:
        # Second upload with identical filename
        files_dup = {"files": ("unique_lecture_notes.txt", b"Duplicate upload attempt.", "text/plain")}
        res2 = client.post(f"/api/courses/{target_course_id}/materials/upload", files=files_dup, headers=teacher_auth)
        assert res2.status_code == 409
        assert "already exists" in res2.json()["detail"]
    finally:
        client.delete(f"/api/courses/{target_course_id}/materials/{mat_id}", headers=teacher_auth)


def test_reindexing_flow(teacher_auth, target_course_id):
    """Reindexing a material refreshes vector chunks and updates status."""
    files = {"files": ("reindex_target.txt", b"Initial notes text to be re-indexed later.", "text/plain")}
    res = client.post(f"/api/courses/{target_course_id}/materials/upload", files=files, headers=teacher_auth)
    assert res.status_code == 201
    mat_id = res.json()[0]["id"]

    try:
        # Trigger reindex
        res_reindex = client.post(f"/api/courses/{target_course_id}/materials/{mat_id}/reindex", headers=teacher_auth)
        assert res_reindex.status_code == 200
        assert res_reindex.json()["status"] == "INDEXED"
        assert res_reindex.json()["chunk_count"] > 0
    finally:
        client.delete(f"/api/courses/{target_course_id}/materials/{mat_id}", headers=teacher_auth)


def test_indexing_failure_graceful_handling(teacher_auth, target_course_id):
    """Corrupt or textless PDF should be handled gracefully: status='FAILED' without 500 error."""
    # A corrupt PDF that pypdf cannot extract text from
    corrupt_pdf = b"%PDF-1.4\ncorrupt header content without xref or pages"
    files = {"files": ("corrupt_sample.pdf", corrupt_pdf, "application/pdf")}
    res = client.post(f"/api/courses/{target_course_id}/materials/upload", files=files, headers=teacher_auth)
    assert res.status_code == 201
    item = res.json()[0]
    assert item["status"] == "FAILED"
    assert item["error_message"] is not None
    assert item["chunk_count"] == 0

    client.delete(f"/api/courses/{target_course_id}/materials/{item['id']}", headers=teacher_auth)
