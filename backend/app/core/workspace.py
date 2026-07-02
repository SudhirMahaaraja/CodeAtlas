import os
import shutil
import uuid
import logging
from typing import Generator
from contextlib import contextmanager
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class WorkspaceManager:
    @staticmethod
    def create_workspace_dir() -> str:
        """Create a new temporary workspace directory."""
        os.makedirs(settings.WORKSPACE_DIR, exist_ok=True)
        unique_id = str(uuid.uuid4())
        workspace_path = os.path.join(settings.WORKSPACE_DIR, unique_id)
        os.makedirs(workspace_path, exist_ok=True)
        logger.info(f"Created temporary workspace at: {workspace_path}")
        return workspace_path

    @staticmethod
    def cleanup(workspace_path: str) -> None:
        """Clean up the workspace directory."""
        if not workspace_path or not os.path.exists(workspace_path):
            return
        
        # Security check: Ensure workspace_path is inside workspace_temp
        real_workspace_dir = os.path.realpath(settings.WORKSPACE_DIR)
        real_target_dir = os.path.realpath(workspace_path)
        if not real_target_dir.startswith(real_workspace_dir):
            logger.warning(f"Prevented cleanup of directory outside workspace_temp: {workspace_path}")
            return
            
        try:
            shutil.rmtree(workspace_path, ignore_errors=True)
            logger.info(f"Cleaned up workspace at: {workspace_path}")
        except Exception as e:
            logger.error(f"Error during workspace cleanup: {e}", exc_info=True)

    @classmethod
    @contextmanager
    def session(cls) -> Generator[str, None, None]:
        """Context manager for workspace lifecycle."""
        path = cls.create_workspace_dir()
        try:
            yield path
        finally:
            cls.cleanup(path)
