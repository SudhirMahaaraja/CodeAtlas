import re
import logging
from typing import Optional
from backend.app.models.schema import FileModel

logger = logging.getLogger(__name__)

class CSSParser:
    # Regex to find selectors (anything before { except media queries)
    SELECTOR_REGEX = re.compile(r'([^{]+)\s*\{')

    @staticmethod
    def parse_file(file_path: str, relative_path: str) -> Optional[FileModel]:
        """
        Parses a CSS file to extract structural details.
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            loc = len(content.splitlines())
            
            # Simple selector list extraction
            selectors = []
            for match in CSSParser.SELECTOR_REGEX.finditer(content):
                selector = match.group(1).strip()
                if selector and not selector.startswith("@"):
                    # Clean multi-line selectors
                    selector_clean = " ".join(selector.split())
                    selectors.append(selector_clean)
                    
            selectors = list(set(selectors))[:20]  # Cap at 20 major selectors for visual overview
            docstring = f"CSS Stylesheet. Unique Selectors: {len(selectors)}"

            return FileModel(
                path=relative_path.replace("\\", "/"),
                language="css",
                module_docstring=docstring,
                imports=selectors, # Map selector list to imports field for simple metadata display
                classes=[],
                functions=[],
                loc=loc
            )
        except Exception as e:
            logger.error(f"Error parsing CSS file {file_path}: {e}", exc_info=True)
            return None
