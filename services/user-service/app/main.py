"""
User Service — FastAPI Application Entry Point

Responsibilities:
  - User registration and profile management
  - Authentication (login, logout, token refresh)
  - JWT issuance and refresh token rotation
  - Role-based access control enforcement
  - Rate limiting on sensitive endpoints

This service is the authority on user identity. All other services
validate tokens by verifying the JWT signature (shared secret), not
by calling this service on every request. This keeps auth stateless
and avoids a network hop for every API call.
"""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.exceptions import AppException
from app.db.session import init_db
from app.routers import auth, users, admin

# Structured logging setup
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup and shutdown tasks."""
    logger.info("User Service starting up...")
    await init_db()
    logger.info("Database connection pool ready.")
    yield
    logger.info("User Service shutting down.")


app = FastAPI(
    title="LMS User Service",
    description="Handles user registration, authentication, and profile management.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — allow the frontend and API gateway
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Attach a unique request_id to every incoming request.
# This propagates through logs and downstream service calls for tracing.
@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Global handler for our custom application exceptions.
# Converts them to consistent JSON error responses.
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
        },
    )


# Catch-all for unexpected errors — log the details but return a safe message
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred.",
            },
        },
    )


# Prometheus metrics — exposes /metrics endpoint for Prometheus scraping
Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
).instrument(app).expose(app)


# ---- Routers ----
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])


# ---- Health endpoints ----

@app.get("/health", tags=["Health"], include_in_schema=False)
async def health():
    """Liveness check — service is running."""
    return {"status": "ok", "service": "user-service"}


@app.get("/ready", tags=["Health"], include_in_schema=False)
async def readiness():
    """
    Readiness check — verifies the database is reachable.
    Returns 503 if the DB is unavailable so the load balancer
    can stop sending traffic to this instance.
    """
    from app.db.session import check_db_connection

    db_ok = await check_db_connection()
    if not db_ok:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "reason": "database unreachable"},
        )
    return {"status": "ready"}
