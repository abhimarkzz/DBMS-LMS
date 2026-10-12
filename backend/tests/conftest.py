import re
import asyncio
import pytest
from app.database.postgres import SessionLocal, init_db
from app.seeds.seed_data import seed_all_data
from app.models.sql_models import Course, User, NoteChunk, StudyMaterial, Assignment, Submission, Result, Enrollment
from app.config import settings
from pymongo import MongoClient

CANONICAL_COURSES = {'CS201', 'CS301', 'CS305', 'LANG101', 'CS401'}
CANONICAL_EMAILS = {
    'admin@univ.edu',
    'prof.alan@univ.edu',
    'dr.sarah@univ.edu',
    'alex@student.univ.edu',
    'priya@student.univ.edu',
    'marcus@student.univ.edu',
    'elena@student.univ.edu',
}


def cleanup_test_artifacts():
    # 1. Clean PostgreSQL
    db = SessionLocal()
    canonical_uids = set()
    try:
        # Non-canonical test courses
        test_courses = db.query(Course).filter(~Course.code.in_(CANONICAL_COURSES)).all()
        for tc in test_courses:
            db.delete(tc)
        
        # Non-canonical test users
        test_users = db.query(User).filter(~User.email.in_(CANONICAL_EMAILS)).all()
        for tu in test_users:
            db.delete(tu)
        
        db.commit()

        # Capture valid canonical IDs for mongo cleanup
        canon_users = db.query(User).filter(User.email.in_(CANONICAL_EMAILS)).all()
        canonical_uids = {u.id for u in canon_users}
    except Exception:
        db.rollback()
    finally:
        db.close()

    # 2. Clean MongoDB test notifications
    try:
        client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=2000)
        mongo_db = client[settings.MONGODB_DB_NAME]
        test_patterns = [
            r'AUD_', r'PUB_', r'MCQ_', r'DESC_', r'QA\d+', r'SCR_', r'SEC_', r'CA4655',
            r'Term Project Milestone 1', r'Strict Score Test', r'Assignment in Course A',
            r'Audio Oral Defense Recording', r'Lab Report File Submission',
            r'Distributed Consensus Case Study', r'DBMS Concurrency & Recovery Quiz',
            r'reindex_target', r'unique_lecture_notes', r'deadlock_detection',
            r'query_optimization_slides', r'postgres_internals', r'Classified Notes',
            r'Bulk Notif', r'Alert \d+', r'Direct Notification Test', r'Test Enrollee',
            r'Course A Security Test', r'Score Limit Verification', r'Material Security Course',
            r'Restricted Quantum Security'
        ]
        pattern = re.compile('|'.join(test_patterns))
        
        mongo_db.notifications.delete_many({
            '$or': [
                {'user_id': {'$nin': list(canonical_uids)}},
                {'title': {'$regex': pattern}},
                {'message': {'$regex': pattern}}
            ]
        })
        mongo_db.announcements.delete_many({
            '$or': [
                {'title': {'$regex': pattern}},
                {'content': {'$regex': pattern}}
            ]
        })
    except Exception:
        pass


@pytest.fixture(scope="session", autouse=True)
def setup_and_cleanup_test_database():
    """Ensure database schema and canonical seed data exist, then cleanup test artifacts."""
    # 1. Initialize schema and pgvector
    try:
        init_db()
    except Exception:
        pass

    # 2. Ensure canonical users and courses exist
    try:
        with SessionLocal() as db:
            asyncio.run(seed_all_data(db))
    except Exception:
        pass

    # Pre-test cleanup
    cleanup_test_artifacts()
    yield
    # Post-test cleanup
    cleanup_test_artifacts()
