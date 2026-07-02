import re
import logging
from typing import Optional
from backend.app.models.schema import FileModel, ClassModel, FunctionModel

logger = logging.getLogger(__name__)

class JSParser:
    # Regexes for ES imports, functions, classes, React components, and hooks
    IMPORT_REGEX = re.compile(r'import\s+(?:[\w*\s{},]*\s+from\s+)?[\'"]([^\'"]+)[\'"]')
    FUNCTION_REGEX = re.compile(r'(?:export\s+)?(?:async\s+)?function\s+(?P<name>\w+)\s*\((?P<args>[^)]*)\)')
    ARROW_FUNCTION_REGEX = re.compile(r'(?:const|let|var)\s+(?P<name>\w+)\s*=\s*(?:async\s*)?\((?P<args>[^)]*)\)\s*=>')
    CLASS_REGEX = re.compile(r'class\s+(?P<name>\w+)(?:\s+extends\s+(?P<base>\w+))?')
    HOOK_USE_REGEX = re.compile(r'\b(use[A-Z]\w*)')

    @staticmethod
    def parse_file(file_path: str, relative_path: str) -> Optional[FileModel]:
        """
        Parses a JS/JSX/TS/TSX file using regex to identify structure.
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            lines = content.splitlines()
            loc = len(lines)
            
            imports = []
            classes = []
            functions = []
            
            # Simple line-by-line parsing to collect imports, functions, classes, and hooks
            for idx, line in enumerate(lines, start=1):
                # Imports
                imp_match = JSParser.IMPORT_REGEX.search(line)
                if imp_match:
                    imports.append(imp_match.group(1))
                    
                # Class definition
                class_match = JSParser.CLASS_REGEX.search(line)
                if class_match:
                    classes.append(ClassModel(
                        name=class_match.group("name"),
                        docstring="Javascript Class",
                        base_classes=[class_match.group("base")] if class_match.group("base") else [],
                        methods=[],
                        line_number=idx
                    ))
                    
                # Functions
                func_match = JSParser.FUNCTION_REGEX.search(line)
                if func_match:
                    functions.append(FunctionModel(
                        name=func_match.group("name"),
                        docstring="Standard Javascript Function",
                        params=[],
                        line_number=idx,
                        calls=[]
                    ))
                    
                # Arrow functions
                arrow_match = JSParser.ARROW_FUNCTION_REGEX.search(line)
                if arrow_match:
                    functions.append(FunctionModel(
                        name=arrow_match.group("name"),
                        docstring="Arrow Function",
                        params=[],
                        line_number=idx,
                        calls=[]
                    ))

            # Framework detection: React hook checks or React patterns
            # Find hooks in content
            hooks = list(set(JSParser.HOOK_USE_REGEX.findall(content)))
            module_docstring = f"JavaScript File. Detected Hooks: {', '.join(hooks)}" if hooks else "JavaScript File"

            return FileModel(
                path=relative_path.replace("\\", "/"),
                language="javascript",
                module_docstring=module_docstring,
                imports=imports,
                classes=classes,
                functions=functions,
                loc=loc
            )
        except Exception as e:
            logger.error(f"Error parsing JS file {file_path}: {e}", exc_info=True)
            return None
