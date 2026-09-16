from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
import time
from .config import settings
from .proxy import forward_request

app = FastAPI(title="LMS API Gateway", version="1.0.0")

# Redis connection for rate limiting
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "api-gateway"}

async def check_rate_limit(request: Request, service: str):
    client_ip = request.client.host
    current_minute = int(time.time() // 60)
    key = f"rate_limit:{client_ip}:{service}:{current_minute}"
    
    # Simple fixed window rate limiting
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, 60)
        
    limit = settings.RATE_LIMIT_GENERAL
    if service == "users" and "login" in request.url.path:
        limit = settings.RATE_LIMIT_LOGIN
    elif service == "search":
        limit = settings.RATE_LIMIT_AI_SEARCH
        
    if count > limit:
        raise HTTPException(status_code=429, detail="Too Many Requests")

@app.api_route("/api/v1/{service}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@app.api_route("/api/v1/{service}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_all(service: str, request: Request, path: str = ""):
    await check_rate_limit(request, service)
    
    routing_map = {
        "users": settings.USER_SERVICE_URL,
        "courses": settings.COURSE_SERVICE_URL,
        "assignments": settings.ASSIGNMENT_SERVICE_URL,
        "results": settings.RESULT_SERVICE_URL,
        "notifications": settings.NOTIFICATION_SERVICE_URL,
        "search": settings.AI_SEARCH_SERVICE_URL,
        "materials": settings.AI_SEARCH_SERVICE_URL
    }
    
    target_url = routing_map.get(service)
    if not target_url:
        raise HTTPException(status_code=404, detail=f"Service '{service}' not found")
        
    full_downstream_path = f"api/v1/{service}"
    if path:
        full_downstream_path += f"/{path}"
        
    return await forward_request(request, target_url, full_downstream_path)
