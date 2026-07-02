import os
import sys
import logging
from contextlib import asynccontextmanager

# Ensure root of CodeAtlas is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import Database
from backend.app.api.routes_analyze import router as analyze_router
from backend.app.api.routes_jobs import router as jobs_router

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing application startup...")
    # Initialize MongoDB connection
    Database.connect()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Static Code Analysis & Documentation Generator",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for local react frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    """Simple API health check endpoint."""
    return {
        "status": "healthy",
        "database": "fallback_in_memory" if Database.use_fallback else "mongodb"
    }

# Include API routers
app.include_router(analyze_router)
app.include_router(jobs_router)

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*50)
    print("CodeAtlas Local Server Details:")
    print("- API Server: http://127.0.0.1:8000")
    print("- API Documentation: http://127.0.0.1:8000/docs")
    print("- API Health Check: http://127.0.0.1:8000/health")
    print("="*50 + "\n")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
