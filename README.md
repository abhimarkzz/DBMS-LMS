# AI-Powered Distributed Learning Management System

> Enterprise-grade academic learning management platform featuring polyglot persistence (PostgreSQL + pgvector, MongoDB, Redis), grounded Retrieval-Augmented Generation (Gemini AI RAG), and role-based academic workflows.

---

## 1. Project Overview & Problem Statement

### The Problem
Traditional Learning Management Systems (LMS) suffer from rigid single-database architectures that mix high-frequency event streaming with strict transactional academic records, leading to severe lock contention and unscalable search. Standard keyword search across university course material fails to grasp semantic intent, forcing students to manually comb through hundreds of pages of lecture notes and slides.

### The Solution
This platform implements an enterprise-grade academic learning architecture with **polyglot persistence**:
1. **PostgreSQL** enforces ACID transactional integrity for relational academic data (users, courses, enrollments, assignments, submissions, official marks, views, triggers, and stored procedures).
2. **MongoDB** stores unstructured document data, user notifications, course announcements, and system audit trails.
3. **pgvector** embeds lecture notes into high-dimensional vector space (768-d) and provides sub-millisecond Approximate Nearest Neighbor (ANN) semantic similarity search via cosine distance (`<=>`).
4. **Redis** provides real-time event pub/sub and high-speed cache with automatic graceful in-memory fallback if Redis is offline.
5. **Gemini AI RAG Engine** synthesizes grounded academic answers exclusively citing retrieved course note chunks, with guardrails preventing hallucination.

---

## 2. Architecture & Service Boundaries

```
[ React + TypeScript SPA (Vite) ]
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
 │ - Stored Proc     │ │- MongoDB docs │ │- pgvector Cosine     │
 │ - Window Ranks    │ │- Redis PubSub │ │- Grounded Gemini RAG │
 └──────────┬────────┘ └───────┬───────┘ └──────────┬───────────┘
            │                  │                    │
 ═══════════╪══════════════════╪════════════════════╪════════════
                      DATA PERSISTENCE LAYER
   ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐
   │ PostgreSQL      │  │  MongoDB         │  │  Redis         │
   │ + pgvector      │  │  (Document DB)   │  │  (Pub/Sub)     │
   │ - ACID Schema   │  │ - Notifications  │  │ - Event bus    │
   │ - Views/Triggers│  │ - Activity logs  │  │ - Cache TTL    │
   │ - 768-d Vectors │  │ - Announcements  │  │ - Auto Fallback│
   └─────────────────┘  └──────────────────┘  └────────────────┘
```

---

## 3. Demo Credentials

The system seeds realistic academic data upon first startup. Use any of the following accounts:

| Role | Email | Password | Full Name | Permissions |
| :--- | :--- | :--- | :--- | :--- |
| **Admin** | `admin@univ.edu` | `AdminPass123!` | Dean Victoria Vance | System health, user directory, global audit overview |
| **Teacher** | `prof.alan@univ.edu` | `Password123!` | Prof. Alan Turing | Course creation, assignment grading, notes upload & chunking |
| **Teacher** | `dr.sarah@univ.edu` | `Password123!` | Dr. Sarah Connor | Course creation, assignment grading, notes upload & chunking |
| **Student** | `alex@student.univ.edu` | `Password123!` | Alex Rivera | Enrolled in CS501-CS504, assignment submissions, AI search |
| **Student** | `priya@student.univ.edu` | `Password123!` | Priya Sharma | Enrolled, submitted assignments, leaderboard rank |
| **Student** | `marcus@student.univ.edu` | `Password123!` | Marcus Vance | Enrolled, assignment submissions, leaderboard rank |
| **Student** | `elena@student.univ.edu` | `Password123!` | Elena Rostova | Enrolled, assignment submissions, leaderboard rank |

---

## 4. Key DBMS Concepts Demonstrated

| Syllabus Topic | Implementation Detail in Project | Source Reference |
| :--- | :--- | :--- |
| **Relational Modeling & DDL** | 9 normalized relational tables with PKs, FKs, CASCADE rules, unique constraints (`uq_student_course_enrollment`, `uq_assignment_student_submission`). | `backend/app/models/sql_models.py` |
| **Relational Views** | `student_progress_view`: aggregates course assignments, submission counts, completion %, and grade.<br>`course_result_summary_view`: instructor summary with avg/max/min score. | `backend/app/database/postgres.py` |
| **Triggers** | `trigger_auto_grade_submission`: executes on submission grading, automatically recalculating student course grades. | `backend/app/database/postgres.py` |
| **Stored Procedures / Functions** | `calculate_course_grade(student_id, course_id)`: plpgsql stored function computing total points, percentage, and letter grade (`A+`, `A`, `B`, `C`, `D`, `F`). | `backend/app/database/postgres.py` |
| **Window Functions** | `RANK() OVER (PARTITION BY course_id ORDER BY percentage DESC)` for class leaderboard standings. | `backend/app/repositories/result_repo.py` |
| **Subqueries** | Query finding students with scores strictly above the course average (`WHERE r.percentage > (SELECT AVG(percentage) FROM results ...)`). | `backend/app/repositories/result_repo.py` |
| **Vector DB (pgvector) & ANN** | 768-dimensional embeddings stored in `note_chunks.embedding` indexed and queried using cosine distance (`<=>`). | `backend/app/repositories/note_chunk_repo.py` |
| **Document Store (MongoDB)** | Flexible BSON documents for notifications, announcements, and activity logs with compound indexes on `(user_id, created_at)`. | `backend/app/database/mongo.py` |
| **In-Memory Cache (Redis)** | Redis pub/sub dispatcher for instant notifications (`lms_notifications`) with graceful in-memory fallback. | `backend/app/database/redis_client.py` |

---

## 5. AI Smart Notes Search (RAG Flow)

```
Teacher Uploads Notes
         │
         ▼
[Text Chunking] ──▶ Semantic chunks (300-500 chars with overlap)
         │
         ▼
[Vector Embedding] ──▶ 768-dimensional vector (Gemini text-embedding-004 / fallback)
         │
         ▼
[pgvector Index] ──▶ Stored in note_chunks table in PostgreSQL
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
[Relevance Filter] ──▶ Guardrail check: if no overlap, refuse hallucination
         │
         ▼
[Gemini 2.5 Flash] ──▶ Grounded synthesis citing specific course notes
```

---

## 6. Environment Variables Configuration

Copy `.env.example` to `.env` and configure with your service URLs:

```ini
# Database Configuration (PostgreSQL with pgvector)
DATABASE_URL=postgresql://postgres:postgrespassword@localhost:5432/lms_db

# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=lms_mongo_db

# Redis Configuration (Optional: system auto-falls back to in-memory if offline)
REDIS_URL=redis://localhost:6379/0

# Security / JWT
JWT_SECRET=supersecret_jwt_key_for_lms_platform_2026_academic
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# AI / Gemini API (Optional: deterministic semantic fallback enabled if unset)
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=text-embedding-004

# Server Configuration
PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173
```

---

## 7. Local Setup & Running

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL (with `pgvector` extension)
- MongoDB
- Redis (optional, graceful fallback provided)

### Step 1: Backend Setup
```bash
# From repository root
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# Run backend API server (auto-seeds demo data on first launch)
PYTHONPATH=backend uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Documentation (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/api/admin/health](http://localhost:8000/api/admin/health)

### Step 2: Frontend Setup
In a new terminal:
```bash
cd frontend
npm install
npm run dev
```
- Web Application: [http://localhost:5173](http://localhost:5173)

---

## 8. Verification & Automated Testing

### Run Backend Tests (33 Integration & E2E Tests)
```bash
PYTHONPATH=backend pytest backend/tests/ -v
```

### Run Frontend Production Build & Typecheck
```bash
cd frontend
npm run build
```

---

## 9. Cloud Deployment (Normal Cloud Hosting)

This application is architected without container orchestration dependencies. It can be deployed to standard cloud providers:

### Backend Deployment (Render, Railway, Fly.io, AWS EC2, Heroku)
1. **Set Build Command**:
   ```bash
   pip install -r backend/requirements.txt
   ```
2. **Set Start Command**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir backend
   ```
3. **Set Environment Variables**:
   - `DATABASE_URL`: Cloud PostgreSQL URI (e.g. Supabase, Neon, AWS RDS with `vector` extension enabled)
   - `MONGODB_URL`: Cloud MongoDB URI (e.g. MongoDB Atlas)
   - `REDIS_URL`: Cloud Redis URI (e.g. Upstash, AWS ElastiCache)
   - `JWT_SECRET`: Random 32+ character secret string
   - `GEMINI_API_KEY`: Google AI Studio API key
   - `CORS_ORIGINS`: Comma-separated frontend domain URLs

### Frontend Deployment (Vercel, Netlify, Cloudflare Pages, Render Static)
1. **Root Directory**: `frontend`
2. **Build Command**: `npm run build`
3. **Output Directory**: `dist`
4. **Environment Variables**:
   - `VITE_API_URL`: Your deployed backend URL (e.g., `https://lms-api.example.com`)

---

## 10. Project Directory Structure

```
.
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI workflow (tests & build)
├── backend/
│   ├── app/
│   │   ├── config.py            # Pydantic Settings & environment variables
│   │   ├── main.py              # FastAPI application & API Gateway
│   │   ├── database/
│   │   │   ├── mongo.py         # MongoDB Motor client & collection indexes
│   │   │   ├── postgres.py      # PostgreSQL engine, views, triggers, stored proc
│   │   │   └── redis_client.py  # Redis cache, pub/sub & graceful fallback
│   │   ├── models/
│   │   │   └── sql_models.py    # SQLAlchemy tables (User, Course, NoteChunk, etc.)
│   │   ├── repositories/        # Database data access layer
│   │   ├── routers/             # FastAPI REST endpoints
│   │   ├── schemas/             # Pydantic request & response schemas
│   │   ├── seeds/
│   │   │   └── seed_data.py     # Initial demo academic seed data
│   │   └── services/            # Core business logic & Gemini AI RAG engine
│   ├── requirements.txt         # Pinned backend dependencies
│   └── tests/
│       ├── test_api.py          # Functional API tests
│       └── test_qa_exhaustive.py# Comprehensive QA integration tests
├── frontend/
│   ├── index.html               # HTML entry point with academic branding
│   ├── package.json             # Pinned frontend dependencies
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── tsconfig.app.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts           # Vite development and proxy configuration
│   └── src/
│       ├── api.ts               # Typed API client
│       ├── App.tsx              # Student, Teacher, and Admin dashboards
│       ├── index.css            # Professional academic LMS design system
│       └── main.tsx             # React DOM entry point
├── .env.example                 # Cloud-ready environment variable template
├── .gitignore                   # Comprehensive ignore rules
└── README.md                    # Project documentation & deployment guide
```

---

## 11. Known Limitations & Future Improvements
1. **Document Formats**: Supports text and markdown note uploads for chunking and embedding. PDF parsing (`pypdf` / `pdfplumber`) can be added for direct multi-page PDF document ingestion.
2. **LLM Provider Extensibility**: Native support for Google Gemini 2.5 Flash with built-in semantic vector fallback. Can be extended to local Ollama / vLLM deployments.
3. **Distributed Transactions**: The system demonstrates Saga event compensation with Redis pub/sub. Two-Phase Commit (2PC) is documented in course materials but avoided across independent cloud datastores to minimize latency and distributed locking.
