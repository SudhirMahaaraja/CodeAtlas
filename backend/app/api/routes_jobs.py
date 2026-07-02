import io
import zipfile
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, PlainTextResponse
from backend.app.core.database import Database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.get("/{job_id}")
async def get_job_status(job_id: str):
    """Retrieve job metadata and current analysis status."""
    jobs_col = Database.get_collection("jobs")
    job = jobs_col.find_one({"_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # Remove large document content from status response to keep payload small
    job_info = dict(job)
    job_info.pop("readme_content", None)
    job_info.pop("devdoc_content", None)
    
    return job_info

@router.get("/{job_id}/readme")
async def get_job_readme(job_id: str):
    """Fetch the generated README.md content."""
    jobs_col = Database.get_collection("jobs")
    job = jobs_col.find_one({"_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.get("status") != "done":
        raise HTTPException(status_code=400, detail=f"Job is not completed yet. Current status: {job.get('status')}")
        
    readme_content = job.get("readme_content", "")
    return PlainTextResponse(readme_content)

@router.get("/{job_id}/devdoc")
async def get_job_devdoc(job_id: str):
    """Fetch the generated DEVELOPER.md content."""
    jobs_col = Database.get_collection("jobs")
    job = jobs_col.find_one({"_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.get("status") != "done":
        raise HTTPException(status_code=400, detail=f"Job is not completed yet. Current status: {job.get('status')}")
        
    devdoc_content = job.get("devdoc_content", "")
    return PlainTextResponse(devdoc_content)

@router.get("/{job_id}/download")
async def download_job_docs(job_id: str):
    """Download a ZIP archive containing both generated documentation files."""
    jobs_col = Database.get_collection("jobs")
    job = jobs_col.find_one({"_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.get("status") != "done":
        raise HTTPException(status_code=400, detail=f"Job is not completed yet. Current status: {job.get('status')}")
        
    readme_content = job.get("readme_content", "")
    devdoc_content = job.get("devdoc_content", "")
    project_name = job.get("project_name", "project")
    
    # Create in-memory zip archive
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.writestr("README.md", readme_content)
        zip_file.writestr("DEVELOPER.md", devdoc_content)
        
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={
            "Content-Disposition": f"attachment; filename={project_name}_docs.zip"
        }
    )
