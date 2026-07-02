import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import Database

# Initialize database in-memory fallback for testing
Database.connect()
Database.use_fallback = True

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] in ("mongodb", "fallback_in_memory")

def test_jobs_not_found():
    response = client.get("/api/jobs/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"
