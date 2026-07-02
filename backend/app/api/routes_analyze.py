import os
import uuid
import shutil
import logging
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException
from pydantic import BaseModel, HttpUrl

from backend.app.core.database import Database
from backend.app.core.workspace import WorkspaceManager
from backend.app.ingestion.zip_handler import ZipHandler
from backend.app.ingestion.github_handler import GitHubHandler
from backend.app.analysis.model_builder import ModelBuilder
from backend.app.generators.readme_generator import ReadmeGenerator
from backend.app.generators.devdoc_generator import DevdocGenerator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analyze", tags=["analyze"])

class GitHubAnalyzeRequest(BaseModel):
    url: str

def run_analysis_task(job_id: str, workspace_path: str, source_type: str, source_detail: str, zip_file_path: str = None):
    """
    Background worker function that performs codebase extraction, parsing, model building,
    and document generation. Stores results in MongoDB / in-memory DB.
    """
    jobs_col = Database.get_collection("jobs")
    jobs_col.update_one({"_id": job_id}, {"$set": {"status": "running"}})
    
    try:
        if source_type == "zip":
            # Extract zip
            if not zip_file_path or not os.path.exists(zip_file_path):
                raise FileNotFoundError("Uploaded zip archive file not found on disk.")
            ZipHandler.extract(zip_file_path, workspace_path)
            # Remove temp zip upload
            try:
                os.remove(zip_file_path)
            except Exception:
                pass
        elif source_type == "github":
            # Clone public repository
            GitHubHandler.clone(source_detail, workspace_path)
            
        # Build model
        project_name = os.path.basename(source_detail.rstrip("/\\"))
        if not project_name or project_name == ".":
            project_name = "analyzed_project"
            
        project_model = ModelBuilder.build(workspace_path, project_name)
        
        # Generate docs
        readme_md = ReadmeGenerator.generate(project_model)
        devdoc_md = DevdocGenerator.generate(project_model)
        
        # Save to database
        jobs_col.update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": "done",
                    "completed_at": datetime.utcnow().isoformat() + "Z",
                    "project_name": project_model.name,
                    "frameworks": project_model.detected_frameworks,
                    "dependencies": [dep.dict() for dep in project_model.dependencies],
                    "file_count": len(project_model.files),
                    "total_loc": sum(f.loc for f in project_model.files),
                    "readme_content": readme_md,
                    "devdoc_content": devdoc_md
                }
            }
        )
        logger.info(f"Job {job_id} successfully completed analysis.")
        
    except Exception as e:
        logger.error(f"Error executing analysis job {job_id}: {e}", exc_info=True)
        jobs_col.update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": "error",
                    "error_message": str(e),
                    "completed_at": datetime.utcnow().isoformat() + "Z"
                }
            }
        )
    finally:
        # Clean up workspace files
        WorkspaceManager.cleanup(workspace_path)

@router.post("/zip")
async def analyze_zip(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload a multipart ZIP codebase file for analysis."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only standard ZIP archive files are allowed.")
        
    job_id = str(uuid.uuid4())
    workspace_path = WorkspaceManager.create_workspace_dir()
    
    # Save the file temporarily
    temp_zip_dir = os.path.join(workspace_path, "_upload")
    os.makedirs(temp_zip_dir, exist_ok=True)
    temp_zip_path = os.path.join(temp_zip_dir, file.filename)
    
    try:
        with open(temp_zip_path, "wb") as f:
            f.write(await file.read())
    except Exception as e:
        WorkspaceManager.cleanup(workspace_path)
        raise HTTPException(status_code=500, detail=f"Failed to write uploaded file: {e}")
        
    # Insert job record
    jobs_col = Database.get_collection("jobs")
    jobs_col.insert_one({
        "_id": job_id,
        "status": "pending",
        "source_type": "zip",
        "source_detail": file.filename,
        "created_at": datetime.utcnow().isoformat() + "Z"
    })
    
    # Run analysis as a background task
    background_tasks.add_task(
        run_analysis_task,
        job_id=job_id,
        workspace_path=workspace_path,
        source_type="zip",
        source_detail=file.filename,
        zip_file_path=temp_zip_path
    )
    
    return {"status": "success", "job_id": job_id}

@router.post("/github")
async def analyze_github(request: GitHubAnalyzeRequest, background_tasks: BackgroundTasks):
    """Submit a public GitHub repository URL for analysis."""
    if not GitHubHandler.validate_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid GitHub URL. Must be a public https://github.com/owner/repo URL.")
        
    job_id = str(uuid.uuid4())
    workspace_path = WorkspaceManager.create_workspace_dir()
    
    # Insert job record
    jobs_col = Database.get_collection("jobs")
    jobs_col.insert_one({
        "_id": job_id,
        "status": "pending",
        "source_type": "github",
        "source_detail": request.url,
        "created_at": datetime.utcnow().isoformat() + "Z"
    })
    
    # Run analysis as a background task
    background_tasks.add_task(
        run_analysis_task,
        job_id=job_id,
        workspace_path=workspace_path,
        source_type="github",
        source_detail=request.url
    )
    
    return {"status": "success", "job_id": job_id}
