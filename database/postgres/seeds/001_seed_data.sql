-- =============================================================================
-- Seed Data — Development Only
-- =============================================================================
-- WARNING: These are FAKE development credentials.
-- NEVER use these in production.
-- Passwords below are bcrypt hashes of the strings shown in comments.
-- Use the seed script (database/postgres/seeds/run_seeds.sh) to load this.
--
-- Development accounts:
--   admin@example.com        / AdminPass@123
--   teacher1@example.com     / TeachPass@123
--   teacher2@example.com     / TeachPass@123
--   student1@example.com     / StudPass@123
--   student2@example.com     / StudPass@123
--   student3@example.com     / StudPass@123
--
-- Bcrypt hashes generated with cost factor 12.
-- Replace with fresh hashes before any non-development deployment.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------
-- Users
-- -----------------------------------------------------------------------

INSERT INTO users (user_id, email, password_hash, first_name, last_name, phone, role, is_active) VALUES
(
    'a0000000-0000-0000-0000-000000000001',
    'admin@example.com',
    -- AdminPass@123
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3oZ8I6P4Ny',
    'System', 'Administrator', '9000000001', 'ADMIN', TRUE
),
(
    'b0000000-0000-0000-0000-000000000001',
    'teacher1@example.com',
    -- TeachPass@123
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    'Rajesh', 'Kumar', '9000000002', 'TEACHER', TRUE
),
(
    'b0000000-0000-0000-0000-000000000002',
    'teacher2@example.com',
    -- TeachPass@123
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    'Priya', 'Sharma', '9000000003', 'TEACHER', TRUE
),
(
    'c0000000-0000-0000-0000-000000000001',
    'student1@example.com',
    -- StudPass@123
    '$2b$12$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LnS7lgX.e3i',
    'Arjun', 'Patel', '9000000004', 'STUDENT', TRUE
),
(
    'c0000000-0000-0000-0000-000000000002',
    'student2@example.com',
    -- StudPass@123
    '$2b$12$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LnS7lgX.e3i',
    'Sneha', 'Reddy', '9000000005', 'STUDENT', TRUE
),
(
    'c0000000-0000-0000-0000-000000000003',
    'student3@example.com',
    -- StudPass@123
    '$2b$12$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LnS7lgX.e3i',
    'Mohammed', 'Ali', '9000000006', 'STUDENT', TRUE
);

-- -----------------------------------------------------------------------
-- Assign roles in user_roles table (mirrors the users.role column)
-- -----------------------------------------------------------------------

INSERT INTO user_roles (user_id, role_id, assigned_by)
SELECT
    u.user_id,
    r.role_id,
    (SELECT user_id FROM users WHERE role = 'ADMIN' LIMIT 1)
FROM users u
JOIN roles r ON r.role_name = u.role;

-- -----------------------------------------------------------------------
-- Teacher profiles
-- -----------------------------------------------------------------------

INSERT INTO teachers (teacher_id, user_id, employee_id, department, designation) VALUES
(
    'd0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    'EMP-2024-001',
    'Computer Science and Engineering',
    'Associate Professor'
),
(
    'd0000000-0000-0000-0000-000000000002',
    'b0000000-0000-0000-0000-000000000002',
    'EMP-2024-002',
    'Computer Science and Engineering',
    'Assistant Professor'
);

-- -----------------------------------------------------------------------
-- Student profiles
-- -----------------------------------------------------------------------

INSERT INTO students (student_id, user_id, registration_number, department, semester, section, admission_year) VALUES
(
    'e0000000-0000-0000-0000-000000000001',
    'c0000000-0000-0000-0000-000000000001',
    'CSE2022001',
    'Computer Science and Engineering',
    5, 'A', 2022
),
(
    'e0000000-0000-0000-0000-000000000002',
    'c0000000-0000-0000-0000-000000000002',
    'CSE2022002',
    'Computer Science and Engineering',
    5, 'A', 2022
),
(
    'e0000000-0000-0000-0000-000000000003',
    'c0000000-0000-0000-0000-000000000003',
    'CSE2022003',
    'Computer Science and Engineering',
    5, 'B', 2022
);

-- -----------------------------------------------------------------------
-- Courses
-- -----------------------------------------------------------------------

INSERT INTO courses (course_id, course_code, course_name, description, credits, department, semester, teacher_id, status) VALUES
(
    'f0000000-0000-0000-0000-000000000001',
    'CS501',
    'Database Management Systems',
    'Covers relational databases, SQL, normalization, transactions, and NoSQL.',
    4,
    'Computer Science and Engineering',
    5,
    'd0000000-0000-0000-0000-000000000001',
    'ACTIVE'
),
(
    'f0000000-0000-0000-0000-000000000002',
    'CS502',
    'Computer Networks',
    'Study of network architecture, protocols, TCP/IP, routing, and security.',
    4,
    'Computer Science and Engineering',
    5,
    'd0000000-0000-0000-0000-000000000001',
    'ACTIVE'
),
(
    'f0000000-0000-0000-0000-000000000003',
    'CS503',
    'Machine Learning',
    'Introduction to supervised, unsupervised learning, and neural networks.',
    3,
    'Computer Science and Engineering',
    5,
    'd0000000-0000-0000-0000-000000000002',
    'ACTIVE'
);

-- -----------------------------------------------------------------------
-- Enrollments
-- -----------------------------------------------------------------------

-- Student 1 enrolled in CS501 and CS502
INSERT INTO enrollments (student_id, course_id, status) VALUES
('e0000000-0000-0000-0000-000000000001', 'f0000000-0000-0000-0000-000000000001', 'ENROLLED'),
('e0000000-0000-0000-0000-000000000001', 'f0000000-0000-0000-0000-000000000002', 'ENROLLED'),
-- Student 2 enrolled in all three
('e0000000-0000-0000-0000-000000000002', 'f0000000-0000-0000-0000-000000000001', 'ENROLLED'),
('e0000000-0000-0000-0000-000000000002', 'f0000000-0000-0000-0000-000000000002', 'ENROLLED'),
('e0000000-0000-0000-0000-000000000002', 'f0000000-0000-0000-0000-000000000003', 'ENROLLED'),
-- Student 3 enrolled in CS501 and CS503
('e0000000-0000-0000-0000-000000000003', 'f0000000-0000-0000-0000-000000000001', 'ENROLLED'),
('e0000000-0000-0000-0000-000000000003', 'f0000000-0000-0000-0000-000000000003', 'ENROLLED');

-- -----------------------------------------------------------------------
-- Announcements
-- -----------------------------------------------------------------------

INSERT INTO announcements (course_id, posted_by, title, content, is_pinned) VALUES
(
    'f0000000-0000-0000-0000-000000000001',
    'd0000000-0000-0000-0000-000000000001',
    'Welcome to DBMS!',
    'Welcome to CS501 - Database Management Systems. Please review the syllabus document uploaded in course materials.',
    TRUE
),
(
    'f0000000-0000-0000-0000-000000000001',
    'd0000000-0000-0000-0000-000000000001',
    'Assignment 1 Released',
    'Assignment 1 on ER Modeling is now available. Due date is 2 weeks from now. Read the instructions carefully.',
    FALSE
);

-- -----------------------------------------------------------------------
-- Assignments
-- -----------------------------------------------------------------------

INSERT INTO assignments (assignment_id, course_id, title, description, instructions, total_marks, due_date, status, max_attempts, created_by) VALUES
(
    'g0000000-0000-0000-0000-000000000001',
    'f0000000-0000-0000-0000-000000000001',
    'ER Diagram Assignment',
    'Design an Entity-Relationship diagram for a Hospital Management System.',
    'Create an ER diagram with at least 5 entities, their attributes, and relationships. Show cardinality. Submit as PDF.',
    20.00,
    NOW() + INTERVAL '14 days',
    'PUBLISHED',
    1,
    'd0000000-0000-0000-0000-000000000001'
),
(
    'g0000000-0000-0000-0000-000000000002',
    'f0000000-0000-0000-0000-000000000001',
    'SQL Queries Assignment',
    'Write SQL queries demonstrating joins, aggregates, and subqueries.',
    'Solve all 10 SQL problems. Export query results as screenshots. Submit a single PDF.',
    30.00,
    NOW() + INTERVAL '21 days',
    'PUBLISHED',
    2,
    'd0000000-0000-0000-0000-000000000001'
),
(
    'g0000000-0000-0000-0000-000000000003',
    'f0000000-0000-0000-0000-000000000002',
    'Network Protocol Analysis',
    'Use Wireshark to capture and analyze network packets.',
    'Capture 100 packets on your local network. Identify protocols used. Write a 2-page analysis report.',
    25.00,
    NOW() + INTERVAL '10 days',
    'PUBLISHED',
    1,
    'd0000000-0000-0000-0000-000000000001'
);

-- -----------------------------------------------------------------------
-- Submissions
-- -----------------------------------------------------------------------

INSERT INTO submissions (submission_id, assignment_id, student_id, submission_text, submitted_at, status, attempt_number) VALUES
(
    'h0000000-0000-0000-0000-000000000001',
    'g0000000-0000-0000-0000-000000000001',
    'e0000000-0000-0000-0000-000000000001',
    'I have designed the ER diagram for Hospital Management System with entities: Patient, Doctor, Ward, Treatment, and Appointment.',
    NOW() - INTERVAL '2 days',
    'SUBMITTED',
    1
),
(
    'h0000000-0000-0000-0000-000000000002',
    'g0000000-0000-0000-0000-000000000001',
    'e0000000-0000-0000-0000-000000000002',
    'ER Diagram submitted. Entities include: Patient, Doctor, Nurse, Department, and MedicalRecord with all relationships and cardinality.',
    NOW() - INTERVAL '1 day',
    'SUBMITTED',
    1
),
(
    'h0000000-0000-0000-0000-000000000003',
    'g0000000-0000-0000-0000-000000000001',
    'e0000000-0000-0000-0000-000000000003',
    'Submitted ER diagram. Used crow''s foot notation. Entities: Patient, Doctor, Appointment, Prescription, Room.',
    NOW() - INTERVAL '3 hours',
    'SUBMITTED',
    1
);

-- -----------------------------------------------------------------------
-- Submission Grades
-- Inserting grades will fire the trigger that:
--   1. Updates submission status to GRADED
--   2. Calls generate_student_course_result()
--   3. Updates enrollment completion_percentage
-- -----------------------------------------------------------------------

INSERT INTO submission_grades (submission_id, evaluator_id, marks_obtained, feedback, graded_at) VALUES
(
    'h0000000-0000-0000-0000-000000000001',
    'd0000000-0000-0000-0000-000000000001',
    17.00,
    'Good work on identifying entities. Cardinality could be more precise for the Treatment-Doctor relationship.',
    NOW() - INTERVAL '1 day'
),
(
    'h0000000-0000-0000-0000-000000000002',
    'd0000000-0000-0000-0000-000000000001',
    19.00,
    'Excellent ER diagram. All relationships are correctly represented with proper cardinality notation.',
    NOW() - INTERVAL '12 hours'
);

-- -----------------------------------------------------------------------
-- Quizzes
-- -----------------------------------------------------------------------

INSERT INTO quizzes (quiz_id, course_id, title, description, total_marks, duration_minutes, status, created_by) VALUES
(
    'i0000000-0000-0000-0000-000000000001',
    'f0000000-0000-0000-0000-000000000001',
    'Chapter 1 Quiz: DBMS Fundamentals',
    'Quiz on database concepts, ACID properties, and normalization basics.',
    10.00,
    20,
    'PUBLISHED',
    'd0000000-0000-0000-0000-000000000001'
);

INSERT INTO quiz_questions (question_id, quiz_id, question_text, question_type, marks, question_order) VALUES
(
    'j0000000-0000-0000-0000-000000000001',
    'i0000000-0000-0000-0000-000000000001',
    'Which of the following is NOT an ACID property?',
    'SINGLE_CHOICE',
    2.00, 1
),
(
    'j0000000-0000-0000-0000-000000000002',
    'i0000000-0000-0000-0000-000000000001',
    'What does normalization primarily aim to eliminate?',
    'SINGLE_CHOICE',
    2.00, 2
),
(
    'j0000000-0000-0000-0000-000000000003',
    'i0000000-0000-0000-0000-000000000001',
    'Which normal form eliminates transitive dependencies?',
    'SINGLE_CHOICE',
    2.00, 3
);

INSERT INTO quiz_options (question_id, option_text, is_correct, option_order) VALUES
-- Q1 options
('j0000000-0000-0000-0000-000000000001', 'Atomicity',   FALSE, 1),
('j0000000-0000-0000-0000-000000000001', 'Consistency',  FALSE, 2),
('j0000000-0000-0000-0000-000000000001', 'Availability', TRUE,  3),   -- Correct
('j0000000-0000-0000-0000-000000000001', 'Durability',   FALSE, 4),
-- Q2 options
('j0000000-0000-0000-0000-000000000002', 'Data redundancy',   TRUE,  1),  -- Correct
('j0000000-0000-0000-0000-000000000002', 'Data retrieval',    FALSE, 2),
('j0000000-0000-0000-0000-000000000002', 'Data encryption',   FALSE, 3),
('j0000000-0000-0000-0000-000000000002', 'Query optimization', FALSE, 4),
-- Q3 options
('j0000000-0000-0000-0000-000000000003', '1NF', FALSE, 1),
('j0000000-0000-0000-0000-000000000003', '2NF', FALSE, 2),
('j0000000-0000-0000-0000-000000000003', '3NF', TRUE,  3),   -- Correct
('j0000000-0000-0000-0000-000000000003', 'BCNF', FALSE, 4);

-- -----------------------------------------------------------------------
-- Course Materials (metadata only — no actual files in seed data)
-- -----------------------------------------------------------------------

INSERT INTO course_materials (material_id, course_id, uploaded_by, title, material_type, content_type, file_name, storage_name, file_url, file_size_bytes, mime_type, description, status) VALUES
(
    'k0000000-0000-0000-0000-000000000001',
    'f0000000-0000-0000-0000-000000000001',
    'd0000000-0000-0000-0000-000000000001',
    'DBMS Chapter 1 - Introduction to Databases',
    'PDF',
    'PDF',
    'DBMS_Chapter1.pdf',
    'k0000000-0000-0000-0000-000000000001_DBMS_Chapter1.pdf',
    '/uploads/f0000000-0000-0000-0000-000000000001/k0000000-0000-0000-0000-000000000001_DBMS_Chapter1.pdf',
    1048576,   -- 1 MB
    'application/pdf',
    'Introduction to database concepts, DBMS architecture, and data models.',
    'READY'
);

-- Sample chunks for the material (as if text was extracted from the PDF)
INSERT INTO material_chunks (material_id, chunk_number, content, page_number, token_count, embedding_model, embedding_provider, embedding_dimension) VALUES
(
    'k0000000-0000-0000-0000-000000000001',
    1,
    'A database is an organized collection of structured information or data, typically stored electronically in a computer system. A database is usually controlled by a database management system (DBMS).',
    1, 42, 'all-MiniLM-L6-v2', 'sentence_transformers', 384
),
(
    'k0000000-0000-0000-0000-000000000001',
    2,
    'ACID properties ensure reliable database transactions. Atomicity means all operations in a transaction succeed or all are rolled back. Consistency ensures the database moves from one valid state to another. Isolation means concurrent transactions do not interfere. Durability guarantees that committed transactions persist even after system failure.',
    2, 68, 'all-MiniLM-L6-v2', 'sentence_transformers', 384
),
(
    'k0000000-0000-0000-0000-000000000001',
    3,
    'Database normalization is the process of organizing a relational database to reduce data redundancy and improve data integrity. The normal forms are 1NF, 2NF, 3NF, BCNF, 4NF, and 5NF. Most practical databases aim for 3NF.',
    3, 52, 'all-MiniLM-L6-v2', 'sentence_transformers', 384
);

-- Activity events for the seeded actions
INSERT INTO activity_events (actor_id, event_type, entity_type, entity_id, metadata) VALUES
(
    'b0000000-0000-0000-0000-000000000001',
    'COURSE_CREATED',
    'courses',
    'f0000000-0000-0000-0000-000000000001',
    '{"course_code": "CS501", "course_name": "Database Management Systems"}'
),
(
    'b0000000-0000-0000-0000-000000000001',
    'ASSIGNMENT_CREATED',
    'assignments',
    'g0000000-0000-0000-0000-000000000001',
    '{"title": "ER Diagram Assignment", "course_code": "CS501"}'
),
(
    'c0000000-0000-0000-0000-000000000001',
    'ASSIGNMENT_SUBMITTED',
    'submissions',
    'h0000000-0000-0000-0000-000000000001',
    '{"assignment_id": "g0000000-0000-0000-0000-000000000001", "attempt_number": 1}'
);

COMMIT;
