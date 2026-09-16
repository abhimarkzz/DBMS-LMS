# API Documentation

The system is deployed across multiple microservices accessible via a centralized API Gateway running on port `8000`.

## API Gateway
**Base URL:** `http://localhost:8000/api/v1`

The gateway forwards requests based on the first path segment.

### Services and Base Paths:
| Service | Technology | Port | Path |
| --- | --- | --- | --- |
| User Service | FastAPI | 8001 | `/users` |
| Course Service | Spring Boot | 8080 | `/courses` |
| Assignment Service | FastAPI | 8002 | `/assignments` |
| Result Service | Spring Boot | 8081 | `/results` |
| Notification Service | Node.js | 3000 | `/notifications` |
| AI Search Service | FastAPI | 8003 | `/search`, `/materials` |

## Common Endpoints (Through Gateway)

### Auth & Users
- `POST /api/v1/users/auth/register` - Create an account
- `POST /api/v1/users/auth/login` - Obtain JWT Token
- `GET /api/v1/users/me` - Get profile

### Courses
- `GET /api/v1/courses` - List courses (Pagination supported)
- `POST /api/v1/courses` - Create course (Teacher only)
- `POST /api/v1/courses/{course_id}/enroll` - Student enrolls

### Assignments
- `GET /api/v1/assignments/course/{course_id}` - Get assignments
- `POST /api/v1/assignments` - Create assignment
- `POST /api/v1/assignments/{id}/submissions` - Submit work

### AI Search & Materials
- `POST /api/v1/materials/courses/{course_id}/materials` - Upload PDF for RAG
- `POST /api/v1/search` - Query for semantic study material

### Notifications (REST + Socket.IO)
- `GET /api/v1/notifications` - Get unread notifications
- Socket.IO available at `ws://localhost:3000`

## Error Handling
Standardized JSON error format across all services:
```json
{
  "success": false,
  "error": {
    "code": "COURSE_NOT_FOUND",
    "message": "Course with given ID does not exist"
  }
}
```
