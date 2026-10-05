import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.database.postgres import init_db, SessionLocal
from app.database.mongo import init_mongo_indexes
from app.database.redis_client import get_redis_client
from app.routers import (
    auth_router,
    user_router,
    course_router,
    assignment_router,
    result_router,
    notification_router,
    ai_search_router,
    admin_router
)

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("lms.gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    logger.info("Starting up LMS Gateway and Modular Services...")
    try:
        init_db()
        logger.info("PostgreSQL & pgvector initialized.")
    except Exception as e:
        logger.error(f"PostgreSQL initialization error: {e}")

    try:
        await init_mongo_indexes()
        logger.info("MongoDB initialized.")
    except Exception as e:
        logger.warning(f"MongoDB initialization warning: {e}")

    try:
        await get_redis_client()
        logger.info("Redis client initialized.")
    except Exception as e:
        logger.warning(f"Redis initialization warning: {e}")

    # Seed initial demo data if database is fresh
    try:
        from app.seeds.seed_data import seed_all_data
        with SessionLocal() as db:
            await seed_all_data(db)
            logger.info("Demo seed data verified and ready.")
    except Exception as e:
        logger.error(f"Seed data error: {e}")

    yield

    # Shutdown sequence
    logger.info("Shutting down LMS services...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Distributed Learning Management System with Polyglot Persistence (PostgreSQL, MongoDB, pgvector, Redis) and Grounded Gemini AI RAG Search.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Centralized Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "details": exc.errors(),
            "path": request.url.path
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error processing {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": str(exc) if "prod" not in settings.PROJECT_NAME.lower() else "An unexpected error occurred.",
            "path": request.url.path
        }
    )


# Register Modular Service Routers
app.include_router(auth_router.router)
app.include_router(user_router.router)
app.include_router(course_router.router)
app.include_router(assignment_router.router)
app.include_router(result_router.router)
app.include_router(notification_router.router)
app.include_router(ai_search_router.router)
app.include_router(admin_router.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "ONLINE",
        "docs": "/docs",
        "health": "/api/admin/health"
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "UP"}
