import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.sql_models import Role, User, Course, Enrollment, StudyMaterial, Assignment, Submission, Result
from app.services.auth_service import hash_password
from app.services.ai_search_service import AISearchService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


async def seed_all_data(db: Session):
    """Seed comprehensive realistic academic demo data."""
    from app.seeds.clean_and_seed_courses import run_clean_and_seed
    await run_clean_and_seed()
    return

    # 1. Roles
    roles = {}
    for role_name, desc in [
        ("ADMIN", "System administrator with complete platform privileges"),
        ("TEACHER", "Course instructor with syllabus, grading, and material control"),
        ("STUDENT", "Enrolled learner with assignment and AI search access")
    ]:
        r = db.query(Role).filter(Role.name == role_name).first()
        if not r:
            r = Role(name=role_name, description=desc)
            db.add(r)
            db.commit()
            db.refresh(r)
        roles[role_name] = r

    # 2. Users
    default_password = hash_password("Password123!")
    users_data = [
        {"email": "admin@univ.edu", "name": "Dean Victoria Vance", "role": "ADMIN", "pw": hash_password("AdminPass123!")},
        {"email": "prof.alan@univ.edu", "name": "Prof. Alan Turing", "role": "TEACHER", "pw": default_password},
        {"email": "dr.sarah@univ.edu", "name": "Dr. Sarah Connor", "role": "TEACHER", "pw": default_password},
        {"email": "alex@student.univ.edu", "name": "Alex Rivera", "role": "STUDENT", "pw": default_password},
        {"email": "priya@student.univ.edu", "name": "Priya Sharma", "role": "STUDENT", "pw": default_password},
        {"email": "marcus@student.univ.edu", "name": "Marcus Vance", "role": "STUDENT", "pw": default_password},
        {"email": "elena@student.univ.edu", "name": "Elena Rostova", "role": "STUDENT", "pw": default_password},
    ]

    created_users = {}
    for ud in users_data:
        u = User(
            email=ud["email"],
            password_hash=ud["pw"],
            full_name=ud["name"],
            role_id=roles[ud["role"]].id,
            is_active=True
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        created_users[ud["email"]] = u

    # 3. Courses
    courses_data = [
        {
            "code": "CS501",
            "title": "Advanced Database Systems & Architecture",
            "description": "Deep-dive into relational storage engines, WAL logs, MVCC, B-Trees, buffer pools, and query optimization.",
            "syllabus": "Unit 1: Storage & Indexing\nUnit 2: Query Processing & Cost Estimation\nUnit 3: ACID Transactions & Concurrency Control\nUnit 4: Distributed DBMS & Replication",
            "teacher_email": "prof.alan@univ.edu"
        },
        {
            "code": "CS502",
            "title": "Distributed Systems & Consensus Protocols",
            "description": "Rigorous exploration of distributed consensus, Raft, Paxos, Vector Clocks, Byzantine Fault Tolerance, and CAP theorem.",
            "syllabus": "Module 1: Time, Clocks, & Ordering\nModule 2: Quorums & State Machine Replication\nModule 3: Raft Consensus In-Depth\nModule 4: Distributed Transactions (2PC vs Sagas)",
            "teacher_email": "prof.alan@univ.edu"
        },
        {
            "code": "CS503",
            "title": "Cloud Computing & Microservices Architecture",
            "description": "Modern cloud architectures, polyglot persistence, API gateways, event-driven streaming, and container orchestration.",
            "syllabus": "Section 1: Microservice Decomposition\nSection 2: Polyglot Persistence & CQRS\nSection 3: Event-Driven Messaging with Redis & Kafka\nSection 4: Resilient Cloud Deployment",
            "teacher_email": "dr.sarah@univ.edu"
        },
        {
            "code": "CS504",
            "title": "Vector Databases & AI Search Systems",
            "description": "Vector embeddings, High-Dimensional Metric Spaces, Approximate Nearest Neighbor (ANN), HNSW, IVF, and Retrieval-Augmented Generation (RAG).",
            "syllabus": "Part 1: Text & Multimodal Embeddings\nPart 2: Vector Distance Metrics (Cosine, Dot, L2)\nPart 3: Graph-Based Indexing (HNSW)\nPart 4: End-to-End RAG Architectures",
            "teacher_email": "dr.sarah@univ.edu"
        }
    ]

    created_courses = {}
    for cd in courses_data:
        c = Course(
            code=cd["code"],
            title=cd["title"],
            description=cd["description"],
            syllabus=cd["syllabus"],
            teacher_id=created_users[cd["teacher_email"]].id,
            is_published=True
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        created_courses[cd["code"]] = c

    # 4. Enrollments (Enroll 4 students across courses)
    student_emails = ["alex@student.univ.edu", "priya@student.univ.edu", "marcus@student.univ.edu", "elena@student.univ.edu"]
    for code, course in created_courses.items():
        for email in student_emails:
            e = Enrollment(
                student_id=created_users[email].id,
                course_id=course.id,
                status="ACTIVE"
            )
            db.add(e)
    db.commit()

    # 5. Study Materials (Rich Technical Content for AI Smart Notes Search)
    materials_data = [
        {
            "course_code": "CS501",
            "title": "Module 3: PostgreSQL MVCC and Concurrency Control",
            "content": (
                "PostgreSQL implements Multi-Version Concurrency Control (MVCC) to ensure readers never block writers "
                "and writers never block readers. Under MVCC, when a row is updated, PostgreSQL does not overwrite the existing data page. "
                "Instead, it writes a new version of the row with an updated xmin (creation transaction ID) and xmax (deletion transaction ID). "
                "Snapshot Isolation determines row visibility: a transaction only reads tuple versions committed before its snapshot read time. "
                "The Vacuum process subsequently cleans up dead tuples that are no longer visible to any active transaction. "
                "PostgreSQL uses the Write-Ahead Log (WAL) to guarantee durability (D in ACID) and crash recovery using ARIES principles."
            )
        },
        {
            "course_code": "CS501",
            "title": "Module 1: B-Tree Index Mechanics and Buffer Management",
            "content": (
                "B-Tree indexes are balanced search trees where leaf pages contain ordered index keys and tuple pointers (TIDs). "
                "B-Trees guarantee O(log N) lookup, insertion, and deletion complexity. "
                "PostgreSQL uses the B-tree variant called Lehman and Yao B-link tree, which adds high keys and right-sibling pointers. "
                "These right-sibling links allow concurrent traversals even when page splits occur during simultaneous write operations, "
                "eliminating the need to lock ancestor nodes during descent. "
                "The database buffer manager maintains an in-memory page pool using the 2Q or Clock-sweep cache replacement algorithm."
            )
        },
        {
            "course_code": "CS502",
            "title": "Lecture 4: Raft Consensus Algorithm and Leader Election",
            "content": (
                "The Raft consensus algorithm decomposes replicated state machine consensus into three independent subproblems: "
                "leader election, log replication, and safety. A Raft cluster contains servers in one of three states: Follower, Candidate, or Leader. "
                "Time is divided into numbered terms of arbitrary duration. If a follower node experiences an election timeout without receiving heartbeats, "
                "it increments its current term, transitions to candidate state, votes for itself, and broadcasts RequestVote RPCs. "
                "A candidate wins the election if it receives votes from a strict quorum (majority) of cluster nodes. "
                "Log safety ensures that if a leader has applied an entry at a given index, no other node can apply a different entry for that index."
            )
        },
        {
            "course_code": "CS502",
            "title": "Lecture 7: Distributed Transactions: Two-Phase Commit vs Sagas",
            "content": (
                "The Two-Phase Commit (2PC) protocol guarantees atomic commit across distributed participants. "
                "In Phase 1 (Prepare), the coordinator asks all participants to prepare and acquire locks. "
                "In Phase 2 (Commit), if all vote YES, coordinator commands commit; if any votes NO or times out, abort. "
                "Limitation of 2PC: It is a blocking protocol; coordinator crashes leave participants holding locks indefinitely. "
                "In contrast, the Saga pattern organizes long-running distributed workflows into a sequence of local transactions. "
                "If any local transaction fails, the Saga executes compensating transactions in reverse order to achieve eventual consistency "
                "without holding distributed lock contention."
            )
        },
        {
            "course_code": "CS504",
            "title": "Lecture 2: Hierarchical Navigable Small World (HNSW) in Vector Search",
            "content": (
                "Hierarchical Navigable Small World (HNSW) is a state-of-the-art graph-based algorithm for Approximate Nearest Neighbor (ANN) search. "
                "HNSW builds multi-layer graphs where upper layers contain sparse long-range links for rapid greedy skip-list navigation, "
                "while the bottom layer contains dense clustered connections for precise local search. "
                "Search begins at the entry point of the top layer, greedily descending until a local minimum is reached, "
                "then moves down to the next finer layer. In PostgreSQL with pgvector, HNSW indexes enable sub-millisecond similarity queries "
                "over high-dimensional embeddings using the cosine distance operator <=> or Euclidean distance <->."
            )
        }
    ]

    ai_service = AISearchService(db)
    for md in materials_data:
        course = created_courses[md["course_code"]]
        sm = StudyMaterial(
            course_id=course.id,
            title=md["title"],
            content=md["content"],
            material_type="NOTES"
        )
        db.add(sm)
        db.commit()
        db.refresh(sm)

        # Chunk, embed, and insert into pgvector note_chunks
        await ai_service.index_study_material(
            material_id=sm.id,
            course_id=course.id,
            content=md["content"]
        )

    # 6. Assignments
    assignments_data = [
        {
            "course_code": "CS501",
            "title": "Assignment 1: Index Performance Analysis & Query Plans",
            "desc": "Analyze sequential scans versus B-Tree and Hash index scans using EXPLAIN ANALYZE on a 100,000-row table.",
            "max_score": 100.0,
            "due_days": 7
        },
        {
            "course_code": "CS502",
            "title": "Assignment 1: Raft State Machine Implementation",
            "desc": "Implement candidate election timers and heartbeat response RPC handling for a 3-node distributed cluster.",
            "max_score": 100.0,
            "due_days": 10
        },
        {
            "course_code": "CS503",
            "title": "Assignment 1: Polyglot Persistence Architecture",
            "desc": "Design a hybrid data storage layer combining PostgreSQL for transactional data and MongoDB for audit event logs.",
            "max_score": 100.0,
            "due_days": 14
        },
        {
            "course_code": "CS504",
            "title": "Assignment 1: Evaluating HNSW vs IVF Index Recall",
            "desc": "Benchmark recall@k and QPS for HNSW and IVFFlat indexes in pgvector across 10,000 document embeddings.",
            "max_score": 100.0,
            "due_days": 12
        }
    ]

    created_assignments = {}
    for ad in assignments_data:
        c = created_courses[ad["course_code"]]
        a = Assignment(
            course_id=c.id,
            title=ad["title"],
            description=ad["desc"],
            max_score=ad["max_score"],
            due_date=datetime.utcnow() + timedelta(days=ad["due_days"])
        )
        db.add(a)
        db.commit()
        db.refresh(a)
        created_assignments[ad["title"]] = a

    # 7. Submissions & Grading
    # Alex submitted and graded 95/100
    a1 = created_assignments["Assignment 1: Index Performance Analysis & Query Plans"]
    sub1 = Submission(
        assignment_id=a1.id,
        student_id=created_users["alex@student.univ.edu"].id,
        content="Here is my EXPLAIN ANALYZE benchmark comparing index scan (cost 0.42..8.44) against seq scan (cost 0.00..1887.00).",
        status="GRADED",
        score=95.0,
        feedback="Excellent query plan breakdown and cost estimation interpretation!",
        graded_at=datetime.utcnow()
    )
    db.add(sub1)

    # Priya submitted and graded 88/100
    sub2 = Submission(
        assignment_id=a1.id,
        student_id=created_users["priya@student.univ.edu"].id,
        content="Attached my query plan analysis showing selective B-Tree lookup vs unindexed seq scan.",
        status="GRADED",
        score=88.0,
        feedback="Strong analysis of random I/O vs sequential disk reads.",
        graded_at=datetime.utcnow()
    )
    db.add(sub2)

    # Marcus submitted (pending evaluation)
    sub3 = Submission(
        assignment_id=a1.id,
        student_id=created_users["marcus@student.univ.edu"].id,
        content="Submitting my benchmark graphs and explain analyze output for grading.",
        status="SUBMITTED",
        score=None,
        feedback=None
    )
    db.add(sub3)

    # Elena submitted and graded 92/100
    sub4 = Submission(
        assignment_id=a1.id,
        student_id=created_users["elena@student.univ.edu"].id,
        content="Comprehensive write-up on B-link concurrent page splits and TID lookups.",
        status="GRADED",
        score=92.0,
        feedback="Very good theoretical depth on Lehman-Yao B-link tree behavior.",
        graded_at=datetime.utcnow()
    )
    db.add(sub4)

    # 8. Results
    cs501 = created_courses["CS501"]
    results_data = [
        {"student": "alex@student.univ.edu", "total": 95.0, "max": 100.0, "pct": 95.0, "grade": "A+"},
        {"student": "elena@student.univ.edu", "total": 92.0, "max": 100.0, "pct": 92.0, "grade": "A+"},
        {"student": "priya@student.univ.edu", "total": 88.0, "max": 100.0, "pct": 88.0, "grade": "A"},
        {"student": "marcus@student.univ.edu", "total": 76.0, "max": 100.0, "pct": 76.0, "grade": "B"},
    ]
    for rd in results_data:
        res = Result(
            student_id=created_users[rd["student"]].id,
            course_id=cs501.id,
            total_score=rd["total"],
            max_possible=rd["max"],
            percentage=rd["pct"],
            grade=rd["grade"],
            status="PUBLISHED",
            published_at=datetime.utcnow()
        )
        db.add(res)
    db.commit()

    # 9. MongoDB Announcements & Notifications
    await NotificationService.create_announcement(
        course_id=cs501.id,
        title="Welcome to CS501: Advanced Database Systems",
        content="Lectures begin this Tuesday. Please check the uploaded notes on PostgreSQL MVCC and B-Tree indexing.",
        author_name="Prof. Alan Turing",
        course_title=cs501.title
    )

    await NotificationService.create_announcement(
        course_id=created_courses["CS504"].id,
        title="AI Smart Search Activated",
        content="Vector embeddings are active for all course lecture notes. Try querying the AI assistant on HNSW indexing.",
        author_name="Dr. Sarah Connor",
        course_title=created_courses["CS504"].title
    )

    # Welcome notification for Alex
    await NotificationService.create_notification(
        user_id=created_users["alex@student.univ.edu"].id,
        title="Assignment 1 Graded",
        message="Your submission for 'Assignment 1: Index Performance Analysis' has been graded: 95/100 (A+).",
        notif_type="GRADE"
    )

    logger.info("Seed data generation finished successfully!")
