import os
import json
import logging
from typing import List, Tuple, Optional
from backend.app.models.schema import DependencyInfo

# Try importing standard tomllib (python 3.11+), else fallback to tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

logger = logging.getLogger(__name__)

class MetadataDetector:
    FRAMEWORK_MAPPINGS = {
        "fastapi": "FastAPI",
        "flask": "Flask",
        "django": "Django",
        "pyramid": "Pyramid",
        "bottle": "Bottle",
        "tornado": "Tornado",
        "sqlalchemy": "SQLAlchemy (ORM)",
        "pymongo": "PyMongo (MongoDB)",
        "motor": "Motor (Async MongoDB)",
        "react": "React",
        "vue": "Vue",
        "angular": "Angular",
        "next": "Next.js",
        "express": "Express.js",
        "tailwindcss": "TailwindCSS",
        "bootstrap": "Bootstrap CSS",
        "pandas": "Pandas (Data Science)",
        "numpy": "NumPy (Scientific)",
        "tensorflow": "TensorFlow (AI/ML)",
        "torch": "PyTorch (AI/ML)",
        "langchain": "LangChain",
        "langgraph": "LangGraph",
        "faiss": "FAISS (Vector DB)",
        "chromadb": "ChromaDB"
    }

    @classmethod
    def detect(cls, workspace_path: str) -> Tuple[List[DependencyInfo], List[str]]:
        """
        Walks the workspace directory looking for requirements.txt, pyproject.toml, package.json.
        Returns a list of DependencyInfo objects and a list of detected frameworks.
        """
        dependencies = []
        frameworks = set()

        # Look for requirements.txt
        req_path = os.path.join(workspace_path, "requirements.txt")
        if os.path.exists(req_path):
            try:
                with open(req_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or line.startswith("-"):
                            continue
                        
                        # Simple split on ==, >=, <=, etc.
                        parts = None
                        for sep in ("==", ">=", "<=", "~=", ">", "<"):
                            if sep in line:
                                parts = line.split(sep, 1)
                                name = parts[0].strip()
                                version = parts[1].strip()
                                break
                        else:
                            name = line
                            version = None
                            
                        # Clean package names like package[extra]
                        name_clean = name.split("[")[0].strip()
                        if name_clean:
                            dependencies.append(DependencyInfo(
                                name=name_clean,
                                version=version,
                                source="requirements.txt"
                            ))
                            
                            # Check framework
                            fw = cls._match_framework(name_clean)
                            if fw:
                                frameworks.add(fw)
            except Exception as e:
                logger.error(f"Error parsing requirements.txt: {e}")

        # Look for pyproject.toml
        toml_path = os.path.join(workspace_path, "pyproject.toml")
        if os.path.exists(toml_path) and tomllib:
            try:
                with open(toml_path, "rb") as f:
                    data = tomllib.load(f)
                    
                # Parse poetry dependencies
                # [tool.poetry.dependencies]
                poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
                for name, value in poetry_deps.items():
                    if name.lower() == "python":
                        continue
                    version = value if isinstance(value, str) else str(value.get("version", ""))
                    dependencies.append(DependencyInfo(
                        name=name,
                        version=version,
                        source="pyproject.toml"
                    ))
                    fw = cls._match_framework(name)
                    if fw:
                        frameworks.add(fw)
                        
                # Parse standard [project.dependencies]
                project_deps = data.get("project", {}).get("dependencies", [])
                if isinstance(project_deps, list):
                    for dep in project_deps:
                        # e.g., "fastapi>=0.100.0"
                        # Simple clean name
                        name_clean = dep.split(">=")[0].split("==")[0].split("<=")[0].strip()
                        if name_clean:
                            dependencies.append(DependencyInfo(
                                name=name_clean,
                                version=None,
                                source="pyproject.toml"
                            ))
                            fw = cls._match_framework(name_clean)
                            if fw:
                                frameworks.add(fw)
            except Exception as e:
                logger.error(f"Error parsing pyproject.toml: {e}")

        # Look for package.json
        pkg_path = os.path.join(workspace_path, "package.json")
        if os.path.exists(pkg_path):
            try:
                with open(pkg_path, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                    
                # Check dependencies and devDependencies
                for dep_key in ("dependencies", "devDependencies"):
                    deps = data.get(dep_key, {})
                    if isinstance(deps, dict):
                        for name, val in deps.items():
                            dependencies.append(DependencyInfo(
                                name=name,
                                version=str(val),
                                source="package.json"
                            ))
                            fw = cls._match_framework(name)
                            if fw:
                                frameworks.add(fw)
            except Exception as e:
                logger.error(f"Error parsing package.json: {e}")

        return dependencies, list(frameworks)

    @classmethod
    def _match_framework(cls, package_name: str) -> Optional[str]:
        name_lower = package_name.lower()
        for key, framework in cls.FRAMEWORK_MAPPINGS.items():
            if key in name_lower:
                return framework
        return None
