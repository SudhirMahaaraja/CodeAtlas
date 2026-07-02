import os
import zipfile
import logging
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class ZipHandler:
    @staticmethod
    def extract(zip_path: str, extract_to: str) -> list[str]:
        """
        Extracts zip file to the target directory.
        Returns a list of extracted file absolute paths.
        Enforces limits on file count, size, and filters out excluded paths.
        """
        extracted_files = []
        exclude_dirs = {".git", "__pycache__", "venv", ".venv", "node_modules", "dist", "build"}
        
        if not zipfile.is_zipfile(zip_path):
            raise ValueError("The uploaded file is not a valid ZIP archive.")
            
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            infolist = zip_ref.infolist()
            
            # 1. Check file count limit
            if len(infolist) > settings.MAX_FILE_COUNT:
                raise ValueError(f"ZIP contains too many files ({len(infolist)}). Limit is {settings.MAX_FILE_COUNT}.")
                
            # 2. Extract files one by one with validation
            for member in infolist:
                # Prevent directory traversal
                filename = member.filename
                # Clean path segments to verify they aren't trying to traverse out
                normalized_path = os.path.normpath(filename)
                if normalized_path.startswith("..") or normalized_path.startswith("/"):
                    logger.warning(f"Skipping potentially malicious path in zip: {filename}")
                    continue
                    
                # Split paths and check if any directory segment is in excluded list
                path_parts = set(normalized_path.split(os.sep))
                if path_parts.intersection(exclude_dirs):
                    continue
                    
                # Skip directories themselves, we only care about files
                if member.is_dir():
                    continue
                    
                # Check individual file size limit
                if member.file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
                    logger.warning(f"Skipping large file: {filename} ({member.file_size} bytes)")
                    continue
                    
                # Verify file extension (skip binaries/images etc. unless allowed)
                _, ext = os.path.splitext(filename)
                if ext.lower() not in settings.ALLOWED_EXTENSIONS:
                    # Skip unallowed extensions to avoid binary noise
                    continue
                    
                # Safe target path
                target_path = os.path.join(extract_to, normalized_path)
                # Create directories if they don't exist
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
                # Write file safely
                with zip_ref.open(member) as source, open(target_path, "wb") as target:
                    target.write(source.read())
                    
                extracted_files.append(target_path)
                
        logger.info(f"Successfully extracted {len(extracted_files)} files from ZIP to {extract_to}")
        return extracted_files
