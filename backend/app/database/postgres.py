import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

logger = logging.getLogger(__name__)

# Normalize DATABASE_URL for SQLAlchemy
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(
    db_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize relational schema, pgvector extension, views, triggers, and stored procedures."""
    from app.models.sql_models import Role, User, Course, Enrollment, StudyMaterial, NoteChunk, Assignment, Submission, Result
    
    with engine.connect() as conn:
        # 1. Enable pgvector extension
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            logger.info("pgvector extension initialized")
        except Exception as e:
            logger.warning(f"Could not enable pgvector extension: {e}")

    # 2. Create tables
    Base.metadata.create_all(bind=engine)

    # 3. Create views, triggers, and stored procedures
    with engine.connect() as conn:
        # View 1: student_progress_view (Aggregates + Joins)
        view_sql_1 = """
        CREATE OR REPLACE VIEW student_progress_view AS
        SELECT 
            u.id AS student_id,
            u.full_name AS student_name,
            u.email AS student_email,
            c.id AS course_id,
            c.code AS course_code,
            c.title AS course_title,
            COUNT(DISTINCT a.id) AS total_assignments,
            COUNT(DISTINCT s.id) AS submitted_assignments,
            COALESCE(SUM(s.score), 0) AS total_obtained_score,
            COALESCE(SUM(a.max_score), 0) AS total_possible_score,
            CASE 
                WHEN COUNT(DISTINCT a.id) = 0 THEN 0
                ELSE ROUND((COUNT(DISTINCT s.id)::numeric / COUNT(DISTINCT a.id)::numeric) * 100, 2)
            END AS completion_rate,
            r.grade AS published_grade,
            r.percentage AS overall_percentage
        FROM enrollments e
        JOIN users u ON e.student_id = u.id
        JOIN courses c ON e.course_id = c.id
        LEFT JOIN assignments a ON a.course_id = c.id
        LEFT JOIN submissions s ON s.assignment_id = a.id AND s.student_id = u.id AND s.status = 'GRADED'
        LEFT JOIN results r ON r.student_id = u.id AND r.course_id = c.id
        GROUP BY u.id, u.full_name, u.email, c.id, c.code, c.title, r.grade, r.percentage;
        """
        conn.execute(text(view_sql_1))

        # View 2: course_result_summary_view (Course Analytics with Aggregate Metrics)
        view_sql_2 = """
        CREATE OR REPLACE VIEW course_result_summary_view AS
        SELECT 
            c.id AS course_id,
            c.code AS course_code,
            c.title AS course_title,
            t.full_name AS instructor_name,
            COUNT(DISTINCT e.id) AS enrolled_students,
            COUNT(DISTINCT a.id) AS total_assignments,
            COUNT(DISTINCT s.id) AS total_submissions_graded,
            COALESCE(ROUND(AVG(s.score)::numeric, 2), 0) AS average_assignment_score,
            COALESCE(MAX(s.score), 0) AS max_assignment_score,
            COALESCE(MIN(s.score), 0) AS min_assignment_score,
            COALESCE(ROUND(AVG(r.percentage)::numeric, 2), 0) AS course_average_percentage
        FROM courses c
        JOIN users t ON c.teacher_id = t.id
        LEFT JOIN enrollments e ON e.course_id = c.id
        LEFT JOIN assignments a ON a.course_id = c.id
        LEFT JOIN submissions s ON s.assignment_id = a.id AND s.status = 'GRADED'
        LEFT JOIN results r ON r.course_id = c.id
        GROUP BY c.id, c.code, c.title, t.full_name;
        """
        conn.execute(text(view_sql_2))

        # Stored Function: calculate_course_grade (Computes student course grade and updates results table)
        stored_proc_sql = """
        CREATE OR REPLACE FUNCTION calculate_course_grade(
            p_student_id INTEGER,
            p_course_id INTEGER
        ) RETURNS VARCHAR(5) AS $$
        DECLARE
            v_total_obtained NUMERIC := 0;
            v_total_possible NUMERIC := 0;
            v_pct NUMERIC := 0;
            v_grade VARCHAR(5) := 'F';
        BEGIN
            -- Compute sum of graded assignment scores
            SELECT 
                COALESCE(SUM(s.score), 0),
                COALESCE(SUM(a.max_score), 0)
            INTO v_total_obtained, v_total_possible
            FROM assignments a
            LEFT JOIN submissions s ON s.assignment_id = a.id 
                AND s.student_id = p_student_id 
                AND s.status = 'GRADED'
            WHERE a.course_id = p_course_id;

            IF v_total_possible > 0 THEN
                v_pct := ROUND((v_total_obtained / v_total_possible) * 100, 2);
            ELSE
                v_pct := 0;
            END IF;

            -- Grade assignment logic
            IF v_pct >= 90 THEN v_grade := 'A+';
            ELSIF v_pct >= 80 THEN v_grade := 'A';
            ELSIF v_pct >= 70 THEN v_grade := 'B';
            ELSIF v_pct >= 60 THEN v_grade := 'C';
            ELSIF v_pct >= 50 THEN v_grade := 'D';
            ELSE v_grade := 'F';
            END IF;

            -- Upsert into results table
            INSERT INTO results (student_id, course_id, total_score, max_possible, percentage, grade, status, published_at)
            VALUES (p_student_id, p_course_id, v_total_obtained, v_total_possible, v_pct, v_grade, 'PUBLISHED', NOW())
            ON CONFLICT (student_id, course_id)
            DO UPDATE SET 
                total_score = EXCLUDED.total_score,
                max_possible = EXCLUDED.max_possible,
                percentage = EXCLUDED.percentage,
                grade = EXCLUDED.grade,
                status = EXCLUDED.status,
                published_at = NOW();

            RETURN v_grade;
        END;
        $$ LANGUAGE plpgsql;
        """
        conn.execute(text(stored_proc_sql))

        # Trigger: Automatically invoke grade calculation when a submission is marked or updated with a score
        trigger_func_sql = """
        CREATE OR REPLACE FUNCTION trg_func_auto_grade_submission()
        RETURNS TRIGGER AS $$
        DECLARE
            v_course_id INTEGER;
        BEGIN
            IF NEW.score IS NOT NULL THEN
                -- Find course_id for this assignment
                SELECT course_id INTO v_course_id FROM assignments WHERE id = NEW.assignment_id;
                IF v_course_id IS NOT NULL THEN
                    PERFORM calculate_course_grade(NEW.student_id, v_course_id);
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
        conn.execute(text(trigger_func_sql))

        trigger_sql = """
        DROP TRIGGER IF EXISTS trigger_auto_grade_submission ON submissions;
        CREATE TRIGGER trigger_auto_grade_submission
        AFTER INSERT OR UPDATE OF score ON submissions
        FOR EACH ROW
        EXECUTE FUNCTION trg_func_auto_grade_submission();
        """
        conn.execute(text(trigger_sql))

        # HNSW Index for pgvector semantic search if vector table exists
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_note_chunks_embedding 
                ON note_chunks USING hnsw (embedding vector_cosine_ops);
            """))
        except Exception as e:
            logger.info(f"HNSW index notice: {e}")

        conn.commit()
        logger.info("Views, triggers, and stored procedures successfully registered.")
