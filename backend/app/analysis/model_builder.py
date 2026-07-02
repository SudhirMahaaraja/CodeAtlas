import os
import logging
from typing import List, Dict
from backend.app.models.schema import ProjectModel, FileModel
from backend.app.parsers.python_parser import PythonParser
from backend.app.parsers.js_parser import JSParser
from backend.app.parsers.html_parser import HTMLParser
from backend.app.parsers.css_parser import CSSParser
from backend.app.analysis.metadata_detector import MetadataDetector

logger = logging.getLogger(__name__)

class ModelBuilder:
    @staticmethod
    def build(workspace_path: str, project_name: str) -> ProjectModel:
        """
        Walks workspace, parses files, detects dependencies, resolves imports,
        and constructs the final ProjectModel.
        """
        file_models: List[FileModel] = []
        workspace_path = os.path.realpath(workspace_path)
        
        # 1. Walk workspace and parse files
        for root, _, files in os.walk(workspace_path):
            for file in files:
                full_path = os.path.join(root, file)
                # Compute relative path using forward slashes for cross-platform standard
                rel_path = os.path.relpath(full_path, workspace_path).replace("\\", "/")
                
                _, ext = os.path.splitext(file)
                ext = ext.lower()
                
                parsed_file = None
                if ext == ".py":
                    parsed_file = PythonParser.parse_file(full_path, rel_path)
                elif ext in (".js", ".jsx", ".ts", ".tsx"):
                    parsed_file = JSParser.parse_file(full_path, rel_path)
                elif ext == ".html":
                    parsed_file = HTMLParser.parse_file(full_path, rel_path)
                elif ext == ".css":
                    parsed_file = CSSParser.parse_file(full_path, rel_path)
                    
                if parsed_file:
                    file_models.append(parsed_file)

        # 2. Detect project-level info
        dependencies, detected_frameworks = MetadataDetector.detect(workspace_path)

        # 3. Resolve imports and build the import graph
        import_graph = ModelBuilder._build_import_graph(file_models)

        # 4. Detect entry points (common entry files like main.py, app.py, index.js, index.html)
        entry_points = []
        entry_candidates = {"main.py", "app.py", "wsgi.py", "index.js", "index.jsx", "index.tsx", "index.html"}
        for f in file_models:
            if os.path.basename(f.path) in entry_candidates:
                entry_points.append(f.path)

        return ProjectModel(
            name=project_name,
            root_path=workspace_path.replace("\\", "/"),
            detected_frameworks=detected_frameworks,
            dependencies=dependencies,
            entry_points=entry_points,
            files=file_models,
            import_graph=import_graph
        )

    @staticmethod
    def _match_python_import(file_path_no_ext: str, import_str: str) -> bool:
        """
        Determines if a python import matches a workspace file path.
        e.g. import_str = 'controllers.task_controller.get_tasks'
             file_path_no_ext = 'controllers/task_controller'
             -> Returns True
        """
        file_segs = file_path_no_ext.replace("\\", "/").split("/")
        import_segs = import_str.split(".")
        
        file_segs = [s for s in file_segs if s]
        import_segs = [s for s in import_segs if s]
        
        if not file_segs or not import_segs:
            return False
            
        n = len(file_segs)
        if len(import_segs) >= n:
            if import_segs[:n] == file_segs:
                return True
                
        import_module_segs = import_segs[:-1] if len(import_segs) > 1 else import_segs
        m = len(import_module_segs)
        if len(file_segs) >= m:
            if file_segs[-m:] == import_module_segs:
                return True
                
        if import_segs == file_segs:
            return True
            
        return False

    @staticmethod
    def _build_import_graph(files: List[FileModel]) -> Dict[str, List[str]]:
        """
        Builds a dictionary mapping file path -> list of file paths imported by it.
        """
        import_graph: Dict[str, List[str]] = {}
        file_paths = {f.path: f for f in files}

        for file in files:
            resolved_imports = []
            
            for imp in file.imports:
                # Resolve Python imports (e.g., 'app.core.config' or 'backend.app.core.config')
                if file.language == "python":
                    for path in file_paths:
                        if path.endswith(".py") and path != file.path:
                            path_no_ext = path[:-3]
                            if ModelBuilder._match_python_import(path_no_ext, imp):
                                resolved_imports.append(path)
                                
                # Resolve JS/TS imports (e.g., './components/Button' or '../App')
                elif file.language == "javascript":
                    if imp.startswith("."):
                        # Relative path resolution
                        dir_name = os.path.dirname(file.path)
                        # Join and normalize paths
                        target_rel = os.path.normpath(os.path.join(dir_name, imp)).replace("\\", "/")
                        
                        # Match extensionless imports
                        for path in file_paths:
                            path_no_ext = os.path.splitext(path)[0]
                            if path == target_rel or path_no_ext == target_rel:
                                resolved_imports.append(path)
                    else:
                        # Non-relative package import, check if it matches a path in the workspace
                        for path in file_paths:
                            if imp in path:
                                resolved_imports.append(path)
                                
                # Resolve HTML src/hrefs
                elif file.language == "html":
                    # Check if standard file link matches workspace files
                    for path in file_paths:
                        if imp.endswith(path) or path.endswith(imp):
                            resolved_imports.append(path)
            
            # Deduplicate and store
            import_graph[file.path] = list(set(resolved_imports))

        return import_graph
