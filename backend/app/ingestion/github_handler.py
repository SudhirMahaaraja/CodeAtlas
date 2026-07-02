import os
import re
import subprocess
import logging
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class GitHubHandler:
    GITHUB_URL_REGEX = re.compile(
        r'^https?://(www\.)?github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)(/|$)'
    )

    @classmethod
    def validate_url(cls, url: str) -> bool:
        """Validate if the URL is a valid public GitHub repository URL."""
        return bool(cls.GITHUB_URL_REGEX.match(url))

    @classmethod
    def clone(cls, repo_url: str, clone_to: str, timeout_seconds: int = 60) -> list[str]:
        """
        Shallow clones a public GitHub repository.
        Returns a list of cloned file absolute paths.
        """
        if not cls.validate_url(repo_url):
            raise ValueError("Invalid GitHub repository URL. Must be a public https://github.com/owner/repo URL.")

        # Clean repository URL to ensure standard format
        match = cls.GITHUB_URL_REGEX.match(repo_url)
        if not match:
            raise ValueError("Invalid URL format.")
            
        owner = match.group("owner")
        repo = match.group("repo")
        # Remove .git suffix if present in regex capture
        if repo.endswith(".git"):
            repo = repo[:-4]
            
        clean_url = f"https://github.com/{owner}/{repo}.git"

        logger.info(f"Cloning {clean_url} into {clone_to}...")

        try:
            # Run git clone --depth 1
            result = subprocess.run(
                ["git", "clone", "--depth", "1", clean_url, "."],
                cwd=clone_to,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_seconds
            )
            
            if result.returncode != 0:
                logger.error(f"Git clone failed: {result.stderr}")
                raise RuntimeError(f"Failed to clone repository: {result.stderr.strip()}")
                
        except subprocess.TimeoutExpired:
            logger.error("Git clone timed out.")
            raise RuntimeError("Repository clone operation timed out.")
        except Exception as e:
            logger.error(f"Error cloning repository: {e}")
            raise RuntimeError(f"Failed to clone repository: {str(e)}")

        # Collect files
        cloned_files = []
        exclude_dirs = {".git", "__pycache__", "venv", ".venv", "node_modules", "dist", "build"}

        for root, dirs, files in os.walk(clone_to):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                _, ext = os.path.splitext(file)
                if ext.lower() not in settings.ALLOWED_EXTENSIONS:
                    continue
                    
                full_path = os.path.join(root, file)
                
                # Check file size limit
                try:
                    file_size = os.path.getsize(full_path)
                    if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
                        continue
                except OSError:
                    continue
                    
                cloned_files.append(full_path)

        if len(cloned_files) > settings.MAX_FILE_COUNT:
            raise ValueError(f"Repository contains too many files ({len(cloned_files)}). Limit is {settings.MAX_FILE_COUNT}.")

        logger.info(f"Successfully cloned {len(cloned_files)} files from {clean_url}")
        return cloned_files
