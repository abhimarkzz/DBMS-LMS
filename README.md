# AI-Powered Distributed Learning Management System

> Scalable academic learning platform featuring polyglot persistence (PostgreSQL, MongoDB, pgvector, Redis), grounded Retrieval-Augmented Generation (Gemini AI RAG), and role-based academic workflows.

---

## 1. Project Overview & Problem Statement

### The Problem
Traditional Learning Management Systems (LMS) suffer from rigid relational designs that mix high-frequency event streaming with strict transactional academic records, leading to database lock contention. Furthermore, standard keyword search in university repositories fails to comprehend technical domain queries across lecture notes, slides, and syllabus documents, forcing students to manually comb through hundreds of pages of PDF material.

### The Solution
This platform implements an enterprise-grade academic learning architecture separating concerns through **polyglot persistence**:
1. **PostgreSQL** enforces ACID transactional integrity for relational academic data (users, courses, enrollments, assignments, submissions, and official marks).
2. **MongoDB** stores document data, unread notifications, course announcements, and system audit logs.
3. **pgvector** embeds lecture notes into high-dimensional vector space (768-d) and provides sub-millisecond Approximate Nearest Neighbor (ANN) semantic similarity search.
4. **Redis** provides real-time event pub/sub and high-speed cache caching.
5. **Gemini AI RAG Engine** synthesizes grounded academic answers exclusively citing uploaded course materials, with guardrails preventing hallucination.

---

## 2. Architecture & Service Boundaries

```
[ React + TypeScript SPA ]
            │
            ▼  (HTTP / REST / JWT Bearer)
┌────────────────────────────────────────────────────────┐
│           FastAPI API Gateway (Port 8000)              │
│  - CORS, centralized validation & exception handling   │
│  - JWT Verification & Role-Based Access Control (RBAC) │
└───────────┬──────────────┬──────────────┬──────────────┘
            │              │              │
 ┌──────────▼────────┐ ┌───▼───────────┐ ┌▼─────────────────────┐
 │ User Service      │ │Course Service │ │Assignment Service    │
 │ - Auth / RBAC     │ │- Courses      │ │- Assignments         │
 │ - User Directory  │ │- Enrollments  │ │- Submissions & Marks │
 └──────────┬────────┘ └───────┬───────┘ └──────────┬───────────┘
            │                  │                    │
 ┌──────────▼────────┐ ┌───────▼───────┐ ┌──────────▼───────────┐
 │ Result Service    │ │Notification   │ │AI Search Service     │
 │ - Stored Proc     │ │- MongoDB docs │ │- pgvector HNSW       │
 │ - Window Ranks    │ │- Redis PubSub │ │- Grounded Gemini RAG │
 └──────────┬────────┘ └───────┬───────┘ └──────────┬───────────┘
            │                  │                    │
════════════╪══════════════════╪════════════════════╪════════════
                     DATA PERSISTENCE LAYER
  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐
  │ PostgreSQL 18   │  │  MongoDB 7.0     │  │  Redis 7.2     │
  │ + pgvector      │  │  (Document DB)   │  │  (Pub/Sub)     │
  │ - ACID Schema   │  │ - Notifications  │  │ - Event bus    │
  │ - Views/Triggers│  │ - Activity logs  │  │ - Cache TTL    │
  │ - 768-d Vectors │  │ - Announcements  │  │                │
  └─────────────────┘  └──────────────────┘  └────────────────┘
```

---

## 3. Demo Credentials

The platform seeds realistic academic data upon first startup. Use any of the following accounts:

| Role | Email | Password | Full Name | Permissions |
| :--- | :--- | :--- | :--- | :--- |
| **Admin** | `admin@univ.edu` | `AdminPass123!` | Dean Victoria Vance | System health, user directory, global audit |
| **Teacher** | `prof.alan@univ.edu` | `Password123!` | Prof. Alan Turing | Course creation, assignment grading, notes upload |
| **Teacher** | `dr.sarah@univ.edu` | `Password123!` | Dr. Sarah Connor | Course creation, assignment grading, notes upload |
| **Student** | `alex@student.univ.edu` | `Password123!` | Alex Rivera | Enrolled in CS501-CS504, submissions, AI search |
| **Student** | `priya@student.univ.edu` | `Password123!` | Priya Sharma | Enrolled, submissions, AI search |
| **Student** | `marcus@student.univ.edu` | `Password123!` | Marcus Vance | Enrolled, pending submission, AI search |
| **Student** | `elena@student.univ.edu` | `Password123!` | Elena Rostova | Enrolled, submissions, AI search |

---

## 4. Key DBMS Concepts Demonstrated

| Syllabus Topic | Implementation Detail in Project | Source Reference |
| :--- | :--- | :--- |
| **Relational Modeling & DDL** | 9 normalized relational tables with PKs, FKs, CASCADE rules, unique constraints (`uq_student_course_enrollment`, `uq_assignment_student_submission`). | `app/models/sql_models.py` |
| **Relational Views** | `student_progress_view`: aggregates course assignments, submission counts, completion %, and grade.<br>`course_result_summary_view`: instructor summary with avg/max/min score. | `app/database/postgres.py` |
| **Triggers** | `trigger_auto_grade_submission`: executes on submission grading, automatically recalculating student course grades. | `app/database/postgres.py` |
| **Stored Procedures / Functions** | `calculate_course_grade(student_id, course_id)`: plpgsql stored function computing total points, percentage, and letter grade (`A+`, `A`, `B`, `C`, `D`, `F`). | `app/database/postgres.py` |
| **Window Functions** | `RANK() OVER (PARTITION BY course_id ORDER BY percentage DESC)` for class leaderboard standings. | `app/repositories/result_repo.py` |
| **Subqueries** | Query finding students with scores strictly above the course average (`WHERE r.percentage > (SELECT AVG(percentage) FROM results ...)`). | `app/repositories/result_repo.py` |
| **Vector DB (pgvector) & ANN** | 768-dimensional embeddings stored in `note_chunks.embedding` indexed with HNSW and queried using cosine distance (`<=>`). | `app/repositories/note_chunk_repo.py` |
| **Document Store (MongoDB)** | Flexible BSON documents for notifications, announcements, and activity logs with compound indexes on `(user_id, created_at)`. | `app/database/mongo.py` |
| **In-Memory Cache (Redis)** | Redis pub/sub dispatcher for instant notifications (`lms_notifications`) with graceful fallback. | `app/database/redis_client.py` |

---

## 5. AI Smart Notes Search (RAG Flow)

```
Teacher Uploads Notes
         │
         ▼
[Text Chunking] ──▶ Semantic chunks (300-500 chars with overlap)
         │
         ▼
[Vector Embedding] ──▶ 768-dimensional vector (Gemini text-embedding-004 / hash)
         │
         ▼
[pgvector Index] ──▶ Stored in note_chunks table (HNSW index)
         │
────────────────────────────────────────────────────────────────
Student Enters Question
         │
         ▼
[Query Vector] ──▶ Generate 768-d embedding of query
         │
         ▼
[Cosine Distance] ──▶ `nc.embedding <=> CAST(:vec AS vector)`
         │
         ▼
[Top-K Chunks] ──▶ Top relevant chunks retrieved from PostgreSQL
         │
         ▼
[Relevance Filter] ──▶ Guardrail check: if no overlap, return "Not in course content"
         │
         ▼
[Gemini 2.5/3.8 Flash] ──▶ Grounded synthesis citing specific course notes
```

---

## 6. Local Setup & Running

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL with `pgvector`
- MongoDB
- Redis (optional, graceful fallback if offline)

### Step 1: Clone & Configure Environment
```bash
cp .env.example .env
```
Edit `.env` if you wish to configure a live `GEMINI_API_KEY`:
```ini
DATABASE_URL=postgresql://localhost:5432/lms_db
MONGODB_URL=mongodb://localhost:27017
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=supersecret_jwt_key_for_lms_platform_2026_academic
GEMINI_API_KEY=your_key_here
```

### Step 2: Backend Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# Run backend server (auto-seeds demo data on first launch)
PYTHONPATH=backend uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open API Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Step 3: Frontend Setup
In a new terminal:
```bash
cd frontend
npm install
npm run dev
```
Open Web Application: [http://localhost:5173](http://localhost:5173)

---

## 7. Running with Docker Compose

To start the complete polyglot persistence stack in Docker:

```bash
docker compose up --build -d
```

Services exposed:
- **Frontend SPA**: [http://localhost:3000](http://localhost:3000)
- **FastAPI API Gateway & Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **PostgreSQL (with pgvector)**: `localhost:5432`
- **MongoDB**: `localhost:27017`
- **Redis**: `localhost:6379`

To view logs:
```bash
docker compose logs -f backend
```

---

## 8. Verification & Automated Testing

Run the automated backend test suite:
```bash
PYTHONPATH=backend ./venv/bin/pytest backend/tests/test_api.py -v
```

Run the frontend TypeScript & production build check:
```bash
cd frontend && npm run build
```

---

## 9. Cloud Deployment (Railway / Render)

### Deployment to Railway:
1. Push repository to GitHub.
2. Create a new Railway project from your GitHub repo.
3. Provision **PostgreSQL** (enable `vector` extension) and **MongoDB** add-ons in Railway.
4. Set Environment Variables in Railway:
   - `DATABASE_URL`: `${{Postgres.DATABASE_URL}}`
   - `MONGODB_URL`: `${{MongoDB.MONGO_URL}}`
   - `REDIS_URL`: `${{Redis.REDIS_URL}}`
   - `JWT_SECRET`: Generate a secure random 32-character string.
   - `GEMINI_API_KEY`: Your Gemini API key.
5. Deploy `backend` and `frontend` services using their respective `Dockerfile`s.
6. Verify `/api/admin/health` returns `status: HEALTHY`.

---

## 10. Project Directory Structure

```
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI workflow
├── backend/
│   ├── app/
│   │   ├── database/
│   │   │   ├── postgres.py      # PostgreSQL engine, session, views, triggers, stored proc
│   │   │   ├── mongo.py         # MongoDB Motor client & collection indexes
│   │   │   └── redis_client.py  # Redis cache & pub/sub event helper
│   │   ├── models/
│   │   │   ├── sql_models.py    # SQLAlchemy tables (pgvector NoteChunk)
│   │   │   └── mongo_models.py  # MongoDB schemas
│   │   ├── repositories/        # Database access layer (User, Course, Assignment, Result, NoteChunk)
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── services/            # Business logic (Auth, User, Course, Assignment, Result, AI RAG)
│   │   ├── routers/             # FastAPI REST endpoints
│   │   ├── seeds/
│   │   │   └── seed_data.py     # Demo academic seed data
│   │   ├── config.py            # Pydantic Settings
│   │   └── main.py              # FastAPI app & API Gateway
│   ├── tests/
│   │   └── test_api.py          # Automated test suite (10 test cases)
│   ├── requirements.txt         # Pinned backend dependencies
│   └── Dockerfile               # Backend Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api.ts               # Typed API client
│   │   ├── App.tsx              # Main UI with Student, Teacher, Admin dashboards
│   │   ├── index.css            # Dignified university LMS design system
│   │   └── main.tsx
│   ├── Dockerfile               # Production multi-stage Dockerfile
│   ├── nginx.conf               # Nginx reverse proxy
│   └── vite.config.ts           # Vite proxy configuration
├── docker-compose.yml           # Complete polyglot infrastructure
├── .env.example                 # Environment template
└── README.md                    # Project documentation
```

---

## 11. Known Limitations & Future Improvements
1. **Self-hosted LLM fallback**: Currently uses Google GenAI Gemini models (`gemini-2.5-flash` / `gemini-3.8-flash`) with deterministic semantic fallback; local Ollama / vLLM integration can be added.
2. **Document formats**: Supports raw text and markdown note uploads; PDF text extraction (PyMuPDF / pdfplumber) can be attached for direct PDF ingestion.
3. **Two-Phase Commit (2PC) comparison**: The architecture demonstrates Saga-style event compensation with Redis pub/sub; 2PC is documented in course material but not enforced globally to avoid distributed lock contention.
