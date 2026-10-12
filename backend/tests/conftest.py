import re
import pytest
from app.database.postgres import SessionLocal
from app.models.sql_models import Course, User, NoteChunk, StudyMaterial, Assignment, Submission, Result, Enrollment
from pymongo import MongoClient

CANONICAL_COURSES = {'CS201', 'CS301', 'CS305', 'LANG101', 'CS401'}
CANONICAL_UIDS = {1, 2, 3, 4, 5, 6, 7}

def cleanup_test_artifacts():
    # 1. Clean PostgreSQL
    db = SessionLocal()
    try:
        # Test courses
        test_courses = db.query(Course).filter(~Course.code.in_(CANONICAL_COURSES)).all()
        for tc in test_courses:
            db.delete(tc)
        
        # Test users
        test_users = db.query(User).filter(~User.id.in_(CANONICAL_UIDS)).all()
        for tu in test_users:
            db.delete(tu)
        
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

    # 2. Clean MongoDB test notifications
    try:
        client = MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=2000)
        mongo_db = client['lms_mongo_db']
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
                {'user_id': {'$nin': list(CANONICAL_UIDS)}},
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
def auto_cleanup_test_artifacts():
    # Pre-test cleanup
    cleanup_test_artifacts()
    yield
    # Post-test cleanup
    cleanup_test_artifacts()
