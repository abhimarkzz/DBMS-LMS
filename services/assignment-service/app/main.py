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
from app.routers import assignments

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Assignment Service starting up...")
    await init_db()
    yield
    logger.info("Assignment Service shutting down.")

app = FastAPI(
    title="LMS Assignment Service",
    description="Manages course assignments and student submissions",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {"code": exc.code, "message": exc.message},
        },
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred."},
        },
    )

Instrumentator(should_group_status_codes=False, should_ignore_untemplated=True).instrument(app).expose(app)

app.include_router(assignments.router, prefix="/api/v1/assignments", tags=["Assignments"])

@app.get("/health", tags=["Health"], include_in_schema=False)
async def health():
    return {"status": "ok", "service": "assignment-service"}

@app.get("/ready", tags=["Health"], include_in_schema=False)
async def readiness():
    from app.db.session import check_db_connection
    db_ok = await check_db_connection()
    if not db_ok:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "reason": "database unreachable"},
        )
    return {"status": "ready"}
