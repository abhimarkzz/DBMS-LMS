# System Architecture Documentation

## AI-Powered Distributed LMS

---

## 1. System Architecture

```mermaid
graph TB
    Client["Frontend (React/Next.js — Phase 2)"]

    subgraph Gateway["API Gateway (FastAPI :8000)"]
        GW_AUTH["JWT Validation"]
        GW_RATE["Rate Limiting (Redis)"]
        GW_ROUTE["Request Router"]
    end

    subgraph Services["Application Services"]
        US["User Service\n(FastAPI :8001)"]
        CS["Course Service\n(Spring Boot :8080)"]
        AS["Assignment Service\n(FastAPI :8002)"]
        RS["Result Service\n(Spring Boot :8081)"]
        NS["Notification Service\n(Node.js :3000)"]
        AI["AI Search Service\n(FastAPI :8003)"]
    end

    subgraph Databases["Data Layer"]
        PG[("PostgreSQL\n+ pgvector")]
        MG[("MongoDB")]
        RD[("Redis")]
    end

    subgraph Monitor["Observability"]
        PR["Prometheus"]
        GR["Grafana"]
    end

    Client --> Gateway
    GW_AUTH --> GW_RATE --> GW_ROUTE
    GW_ROUTE --> US
    GW_ROUTE --> CS
    GW_ROUTE --> AS
    GW_ROUTE --> RS
    GW_ROUTE --> NS
    GW_ROUTE --> AI

    US --> PG
    CS --> PG
    CS --> RD
    AS --> PG
    AS --> NS
    RS --> PG
    RS --> NS
    NS --> MG
    NS --> RD
    AI --> PG
    AI --> RD
    Gateway --> RD

    Services --> PR
    PR --> GR
```

---

## 2. Service Responsibilities

```mermaid
graph LR
    subgraph UserService["User Service (FastAPI)"]
        U1["POST /auth/register"]
        U2["POST /auth/login"]
        U3["GET /auth/me"]
        U4["GET/PATCH /users/:id"]
        U5["Admin user management"]
    end

    subgraph CourseService["Course Service (Spring Boot)"]
        C1["GET/POST /courses"]
        C2["GET/PATCH/DELETE /courses/:id"]
        C3["POST /courses/:id/enroll"]
        C4["GET /students/me/courses"]
        C5["Announcements"]
    end

    subgraph AssignmentService["Assignment Service (FastAPI)"]
        A1["GET/POST /courses/:id/assignments"]
        A2["POST /assignments/:id/submissions"]
        A3["POST /submissions/:id/grade"]
        A4["Quiz management"]
    end

    subgraph ResultService["Result Service (Spring Boot)"]
        R1["GET /results/me"]
        R2["GET /results/me/courses/:id"]
        R3["Result calculation"]
        R4["GPA reporting"]
    end

    subgraph NotificationService["Notification Service (Node.js)"]
        N1["GET /notifications"]
        N2["Socket.IO events"]
        N3["Mark as read"]
    end

    subgraph AISearchService["AI Search Service (FastAPI)"]
        AI1["POST /courses/:id/materials"]
        AI2["POST /materials/:id/index"]
        AI3["POST /search"]
        AI4["Embedding pipeline"]
    end
```

---

## 3. Authentication Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant GW as API Gateway
    participant US as User Service
    participant RD as Redis
    participant PG as PostgreSQL

    C->>GW: POST /api/v1/auth/login {email, password}
    GW->>GW: Rate limit check (Redis)
    GW->>US: Forward request
    US->>PG: SELECT user WHERE email = ?
    PG-->>US: User record
    US->>US: bcrypt.verify(password, hash)
    US->>PG: UPDATE last_login_at
    US->>US: Generate JWT (sub=user_id, role, exp)
    US->>US: Generate refresh token
    US->>PG: INSERT refresh_tokens (hashed)
    US-->>GW: {access_token, refresh_token}
    GW-->>C: {access_token, refresh_token}

    Note over C,PG: Subsequent authenticated request
    C->>GW: GET /api/v1/courses {Authorization: Bearer <token>}
    GW->>GW: Decode + verify JWT signature
    GW->>GW: Check token expiry
    GW->>CS: Forward with X-User-Id, X-User-Role headers
    CS-->>GW: Course list
    GW-->>C: Course list
```

---

## 4. Assignment Submission Flow

```mermaid
sequenceDiagram
    participant S as Student
    participant GW as API Gateway
    participant AS as Assignment Service
    participant NS as Notification Service
    participant PG as PostgreSQL
    participant MG as MongoDB

    S->>GW: POST /api/v1/assignments/{id}/submissions
    GW->>GW: Validate JWT → student role
    GW->>AS: Forward with student context

    AS->>PG: BEGIN TRANSACTION
    AS->>PG: SELECT enrollment WHERE student_id + course_id
    PG-->>AS: Enrollment record (or null)

    alt Not enrolled
        AS-->>GW: 403 Forbidden
    end

    AS->>PG: SELECT assignment WHERE id + status
    PG-->>AS: Assignment (trigger checks status + due_date)

    AS->>PG: INSERT submission
    AS->>PG: INSERT activity_event
    AS->>PG: COMMIT

    AS->>NS: POST /internal/notify {type: SUBMISSION_RECEIVED}
    NS->>MG: Insert notification document
    NS->>NS: Socket.IO emit to teacher's room

    AS-->>GW: 201 {submission_id, status}
    GW-->>S: 201 Created
```

---

## 5. AI Search Flow

```mermaid
sequenceDiagram
    participant T as Teacher
    participant S as Student
    participant AI as AI Search Service
    participant EMB as Embedding Provider
    participant PG as PostgreSQL
    participant RD as Redis

    Note over T,PG: Material Upload + Indexing

    T->>AI: POST /courses/{id}/materials (PDF file)
    AI->>AI: Validate file (type, size, MIME)
    AI->>AI: Generate safe storage_name (UUID-based)
    AI->>PG: INSERT course_materials (status=UPLOADING)
    AI->>AI: Save file to storage
    AI->>PG: UPDATE status=PROCESSING
    AI->>AI: Extract text (PyPDF2/pdfplumber)
    AI->>AI: Clean + split into chunks (512 tokens, 50 overlap)
    AI->>PG: INSERT material_chunks (content, page_number)
    AI->>EMB: embed_batch(chunk_texts)
    EMB-->>AI: List of vectors (dim=384)
    AI->>PG: UPDATE material_chunks SET embedding = ?
    AI->>PG: UPDATE course_materials SET status=READY

    Note over S,RD: Student Semantic Search

    S->>AI: POST /search {query: "What are ACID properties?"}
    AI->>AI: Verify JWT → student role
    AI->>RD: GET student:{id}:courses (authorized course IDs)
    RD-->>AI: Cache miss → PostgreSQL query
    AI->>PG: SELECT course_id FROM enrollments WHERE student_id=?
    AI->>RD: SET student:{id}:courses (TTL: 5min)
    AI->>RD: GET search:{hash(query+course_ids)}
    RD-->>AI: Cache miss
    AI->>EMB: embed_text(query)
    EMB-->>AI: Query vector (dim=384)
    AI->>PG: search_material_chunks_semantic(vector, course_ids, 5, 0.3)
    PG-->>AI: Top 5 chunks with similarity scores
    AI->>AI: Optional: PostgreSQL FTS keyword search
    AI->>AI: Merge + rank results
    AI->>RD: SET search:{hash} (TTL: 1hr)
    AI->>PG: INSERT search_history
    AI-->>S: [{chunk, material, course, similarity_score, page}]
```

---

## 6. Notification Flow

```mermaid
sequenceDiagram
    participant AS as Assignment Service
    participant NS as Notification Service
    participant MG as MongoDB
    participant RD as Redis
    participant SC as Socket.IO Client (Student Browser)

    AS->>NS: POST /internal/events {type: ASSIGNMENT_GRADED, recipientId, metadata}
    NS->>MG: Insert notification document
    NS->>MG: Insert activity_event document
    NS->>RD: GET socket_session:{recipientId}
    RD-->>NS: Socket session ID (if online)

    alt Student is online
        NS->>SC: socket.to(room).emit('notification', payload)
    end

    Note over SC,NS: Student connects to Socket.IO

    SC->>NS: connect (JWT in auth header)
    NS->>NS: Verify JWT
    NS->>SC: socket.join(user_id room)
    SC->>NS: GET /api/v1/notifications (initial load)
    NS->>MG: Find notifications for recipientId
    MG-->>NS: Notification documents
    NS-->>SC: [{id, type, title, message, read, createdAt}]
```

---

## 7. Service Ownership — Database Tables

| Service | Owns These Tables | Communicates With |
|---|---|---|
| User Service | users, roles, user_roles, students, teachers, refresh_tokens | Used by all services via JWT |
| Course Service | courses, enrollments, announcements | User Service (user info) |
| Assignment Service | assignments, submissions, submission_grades, quizzes, quiz_* | Course Service (enrollment check), Notification Service |
| Result Service | course_results, result_components | Assignment Service (grades), Notification Service |
| AI Search Service | course_materials, material_chunks, embedding_jobs, search_cache, search_history | Course Service (enrollment auth) |
| Notification Service | MongoDB: notifications, activity_events | All services (receives events) |

**Cross-service rule:** No service directly reads or writes another service's tables. Data is exchanged through HTTP APIs or JWT claims.
