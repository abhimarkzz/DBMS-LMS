from fastapi import FastAPI
from app.routers import search

app = FastAPI(title="AI Search Service")

app.include_router(search.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ai-search-service"}
