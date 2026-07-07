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

def test_chatbot_endpoints():
    # Insert mock done job
    jobs_col = Database.get_collection("jobs")
    mock_job = {
        "_id": "test-job-id",
        "status": "done",
        "project_name": "TestProject",
        "dependencies": [{"name": "fastapi", "version": "0.111.0", "source": "requirements.txt"}],
        "frameworks": ["FastAPI"],
        "project_model": {
            "name": "TestProject",
            "root_path": "/workspace",
            "detected_frameworks": ["FastAPI"],
            "dependencies": [{"name": "fastapi", "version": "0.111.0", "source": "requirements.txt"}],
            "entry_points": ["main.py"],
            "files": [
                {
                    "path": "main.py",
                    "language": "python",
                    "module_docstring": "Entry point file.",
                    "imports": ["fastapi"],
                    "classes": [],
                    "functions": [
                        {
                            "name": "read_root",
                            "docstring": "Root API endpoint.",
                            "params": [],
                            "return_type": "dict",
                            "decorators": ["app.get('/')"],
                            "is_async": True,
                            "line_number": 10,
                            "calls": []
                        }
                    ],
                    "loc": 15
                },
                {
                    "path": "frontend/App.jsx",
                    "language": "javascript",
                    "module_docstring": "React main component.",
                    "imports": ["react"],
                    "classes": [],
                    "functions": [
                        {
                            "name": "App",
                            "docstring": "Main UI component.",
                            "params": [],
                            "line_number": 5
                        }
                    ],
                    "loc": 50
                },
                {
                    "path": "frontend/styles.css",
                    "language": "css",
                    "module_docstring": "UI stylesheet.",
                    "imports": [".button", ".chat-box"],
                    "classes": [],
                    "functions": [],
                    "loc": 30
                }
            ],
            "import_graph": {}
        }
    }
    jobs_col.insert_one(mock_job)

    # Test frontend UI query
    response = client.post("/api/jobs/test-job-id/chat", json={
        "question": "Tell me about the frontend UI components and styles",
        "history": []
    })
    assert response.status_code == 200
    # Stream response
    content = b"".join(response.iter_bytes()).decode("utf-8")
    assert "Frontend UI & Style Architecture" in content
    assert "App" in content
    assert "styles.css" in content

    # Test dependency query
    response = client.post("/api/jobs/test-job-id/chat", json={
        "question": "What dependencies are used?",
        "history": []
    })
    assert response.status_code == 200
    content = b"".join(response.iter_bytes()).decode("utf-8")
    assert "fastapi" in content

    # Test custom token search
    response = client.post("/api/jobs/test-job-id/chat", json={
        "question": "Where is the read_root function?",
        "history": []
    })
    assert response.status_code == 200
    content = b"".join(response.iter_bytes()).decode("utf-8")
    assert "read_root" in content
    assert "main.py" in content

    # Test "files overview" query (checking that "overview" doesn't trigger "view" in frontend router)
    response = client.post("/api/jobs/test-job-id/chat", json={
        "question": "Show me the files overview of this repository.",
        "history": []
    })
    assert response.status_code == 200
    content = b"".join(response.iter_bytes()).decode("utf-8")
    assert "Codebase Files Overview" in content
    assert "main.py" in content
    assert "Frontend UI & Style Architecture" not in content


