import re
import psycopg2
from pymongo import MongoClient

CANONICAL_COURSES = ('CS201', 'CS301', 'CS305', 'LANG101', 'CS401')
CANONICAL_UIDS = (1, 2, 3, 4, 5, 6, 7)

def execute_cleanup():
    print("Starting Safe Data Cleanup...")
    # 1. PostgreSQL Cleanup
    conn = psycopg2.connect('postgresql://localhost:5432/lms_db')
    cur = conn.cursor()

    # Get test course IDs
    cur.execute("SELECT id, code, title FROM courses WHERE code NOT IN %s", (CANONICAL_COURSES,))
    test_courses = cur.fetchall()
    test_course_ids = [c[0] for c in test_courses]
    print(f"Found {len(test_courses)} test courses: {test_courses}")

    if test_course_ids:
        # Note chunks
        cur.execute("""
            DELETE FROM note_chunks 
            WHERE material_id IN (SELECT id FROM study_materials WHERE course_id = ANY(%s))
        """, (test_course_ids,))
        chunks_deleted = cur.rowcount
        print(f"Deleted {chunks_deleted} orphaned note_chunks.")

        # Study materials
        cur.execute("DELETE FROM study_materials WHERE course_id = ANY(%s)", (test_course_ids,))
        mats_deleted = cur.rowcount
        print(f"Deleted {mats_deleted} test study_materials.")

        # Submissions
        cur.execute("""
            DELETE FROM submissions 
            WHERE assignment_id IN (SELECT id FROM assignments WHERE course_id = ANY(%s))
        """, (test_course_ids,))
        subs_deleted = cur.rowcount
        print(f"Deleted {subs_deleted} test submissions.")

        # Results
        cur.execute("DELETE FROM results WHERE course_id = ANY(%s)", (test_course_ids,))
        res_deleted = cur.rowcount
        print(f"Deleted {res_deleted} test results.")

        # Assignments
        cur.execute("DELETE FROM assignments WHERE course_id = ANY(%s)", (test_course_ids,))
        asg_deleted = cur.rowcount
        print(f"Deleted {asg_deleted} test assignments.")

        # Enrollments
        cur.execute("DELETE FROM enrollments WHERE course_id = ANY(%s)", (test_course_ids,))
        enr_deleted = cur.rowcount
        print(f"Deleted {enr_deleted} test enrollments.")

        # Courses
        cur.execute("DELETE FROM courses WHERE id = ANY(%s)", (test_course_ids,))
        courses_deleted = cur.rowcount
        print(f"Deleted {courses_deleted} test courses.")

    # Clean up non-canonical test users and their residual records
    cur.execute("SELECT id, email FROM users WHERE id NOT IN %s", (CANONICAL_UIDS,))
    test_users = cur.fetchall()
    test_uids = [u[0] for u in test_users]
    print(f"Found {len(test_users)} test users to clean up.")

    if test_uids:
        cur.execute("DELETE FROM submissions WHERE student_id = ANY(%s)", (test_uids,))
        print(f"Deleted {cur.rowcount} submissions by test users.")

        cur.execute("DELETE FROM results WHERE student_id = ANY(%s)", (test_uids,))
        print(f"Deleted {cur.rowcount} results for test users.")

        cur.execute("DELETE FROM enrollments WHERE student_id = ANY(%s)", (test_uids,))
        print(f"Deleted {cur.rowcount} enrollments by test users.")

        cur.execute("DELETE FROM users WHERE id = ANY(%s)", (test_uids,))
        print(f"Deleted {cur.rowcount} test users.")

    conn.commit()
    cur.close()
    conn.close()
    print("PostgreSQL cleanup completed successfully.")

    # 2. MongoDB Cleanup
    client = MongoClient('mongodb://localhost:27017')
    db = client['lms_mongo_db']

    test_patterns = [
        r'AUD_', r'PUB_', r'MCQ_', r'DESC_', r'QA\d+', r'SCR_', r'SEC_', r'CA4655',
        r'Term Project Milestone 1', r'Strict Score Test', r'Assignment in Course A',
        r'reindex_target', r'unique_lecture_notes', r'deadlock_detection',
        r'query_optimization_slides', r'postgres_internals', r'Classified Notes',
        r'Bulk Notif', r'Alert \d+', r'Direct Notification Test', r'Test Enrollee',
        r'Course A Security Test', r'Score Limit Verification', r'Material Security Course',
        r'Restricted Quantum Security'
    ]
    pattern = re.compile('|'.join(test_patterns))

    # A. Delete test / orphan notifications
    initial_notifs = db.notifications.count_documents({})
    all_notifs = list(db.notifications.find().sort('_id', -1))
    
    seen_keys = set()
    to_delete_ids = []
    
    for n in all_notifs:
        nid = n['_id']
        uid = n.get('user_id')
        title = n.get('title', '')
        msg = n.get('message', '')

        # Filter out if belonging to test user or matching test patterns
        if uid not in CANONICAL_UIDS or pattern.search(title) or pattern.search(msg):
            to_delete_ids.append(nid)
            continue

        # Deduplicate identical notifications for the same user
        dedup_key = (uid, title, msg)
        if dedup_key in seen_keys:
            to_delete_ids.append(nid)
        else:
            seen_keys.add(dedup_key)

    if to_delete_ids:
        del_res = db.notifications.delete_many({'_id': {'$in': to_delete_ids}})
        print(f"Deleted {del_res.deleted_count} test / duplicate notifications in MongoDB. Remaining: {initial_notifs - del_res.deleted_count}")

    # B. Deduplicate announcements
    initial_announcements = db.announcements.count_documents({})
    announcements = list(db.announcements.find().sort('_id', -1))
    seen_ann_keys = set()
    to_delete_ann_ids = []

    for a in announcements:
        aid = a['_id']
        title = a.get('title', '')
        content = a.get('content', '')
        cid = a.get('course_id')

        if pattern.search(title) or pattern.search(content):
            to_delete_ann_ids.append(aid)
            continue

        ann_key = (cid, title)
        if ann_key in seen_ann_keys:
            to_delete_ann_ids.append(aid)
        else:
            seen_ann_keys.add(ann_key)

    if to_delete_ann_ids:
        del_ann_res = db.announcements.delete_many({'_id': {'$in': to_delete_ann_ids}})
        print(f"Deleted {del_ann_res.deleted_count} duplicate/test announcements. Remaining: {initial_announcements - del_ann_res.deleted_count}")

    # C. Activity Logs
    initial_logs = db.activity_logs.count_documents({})
    del_logs_res = db.activity_logs.delete_many({
        '$or': [
            {'user_id': {'$nin': list(CANONICAL_UIDS)}},
            {'action': {'$regex': '|'.join(test_patterns)}}
        ]
    })
    print(f"Deleted {del_logs_res.deleted_count} test activity logs. Remaining: {initial_logs - del_logs_res.deleted_count}")

    print("Safe Data Cleanup finished successfully.")

if __name__ == "__main__":
    execute_cleanup()
