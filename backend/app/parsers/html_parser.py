import re
import logging
from typing import Optional
from backend.app.models.schema import FileModel

logger = logging.getLogger(__name__)

class HTMLParser:
    LINK_REGEX = re.compile(r'<(?:link|script|a)\s+[^>]*(?:href|src)=["\']([^"\']+)["\']', re.IGNORECASE)
    FORM_REGEX = re.compile(r'<form\s+[^>]*action=["\']([^"\']+)["\']', re.IGNORECASE)

    @staticmethod
    def parse_file(file_path: str, relative_path: str) -> Optional[FileModel]:
        """
        Parses an HTML file to extract structural details.
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            loc = len(content.splitlines())
            
            # Find all linked resources (scripts, links, hrefs)
            links = list(set(HTMLParser.LINK_REGEX.findall(content)))
            forms = list(set(HTMLParser.FORM_REGEX.findall(content)))
            
            # Simple document summary
            docstring = f"HTML Document. Links: {len(links)}, Forms: {len(forms)}"

            return FileModel(
                path=relative_path.replace("\\", "/"),
                language="html",
                module_docstring=docstring,
                imports=links,
                classes=[],
                functions=[],
                loc=loc
            )
        except Exception as e:
            logger.error(f"Error parsing HTML file {file_path}: {e}", exc_info=True)
            return None
