"""
readme_generator.py
====================
Renders readme_template.md.j2 from a ProjectModel.

Usage
-----
    gen = ReadmeGenerator(templates_dir="path/to/templates")
    markdown = gen.render(project_model)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.app.models.schema import ProjectModel, FileModel, DependencyInfo


# ── Supporting dataclasses ────────────────────────────────────────────────────

@dataclass
class RouteParam:
    name: str
    type: str
    required: bool = True
    description: str = ""
    default: Optional[str] = None


@dataclass
class RouteBody:
    content_type: str = "application/json"
    example: str = "{}"


@dataclass
class ApiRoute:
    method: str
    path: str
    handler: str
    file: str
    description: str = ""
    is_async: bool = False
    auth: str = ""
    params: list[RouteParam] = field(default_factory=list)
    body: Optional[RouteBody] = None


@dataclass
class EnvVar:
    name: str
    example_value: str = ""
    description: str = ""


@dataclass
class ConfigFile:
    path: str
    purpose: str


@dataclass
class KeyFile:
    path: str
    purpose: str


@dataclass
class Feature:
    name: str
    description: str


@dataclass
class ReadmeContext:
    """All variables the README template may reference."""

    project: ProjectModel

    # Computed fields — populated by ReadmeGenerator.build_context()
    python_version: str = "3.11+"
    license: str = "MIT"
    license_text: str = ""
    total_loc: int = 0
    dir_count: int = 0
    folder_tree: str = ""
    entry_points: list[str] = field(default_factory=list)
    has_tests: bool = False
    test_framework: str = "pytest"
    test_dirs: list[str] = field(default_factory=list)
    coverage_tool: str = ""
    source_dir: str = "."
    has_requirements_txt: bool = False
    has_pyproject_toml: bool = False
    has_package_json: bool = False
    has_yarn_lock: bool = False
    has_dotenv: bool = False
    has_app_factory: bool = False
    has_alembic: bool = False
    main_module: str = "app"
    celery_app: str = "app"
    api_routes: list[ApiRoute] = field(default_factory=list)
    env_vars: list[EnvVar] = field(default_factory=list)
    config_files: list[ConfigFile] = field(default_factory=list)
    key_files: list[KeyFile] = field(default_factory=list)
    features: list[Feature] = field(default_factory=list)
    npm_scripts: dict = field(default_factory=dict)
    run_notes: str = ""
    tech_keywords: list[str] = field(default_factory=list)
    model_files: list[str] = field(default_factory=list)


# ── Generator ─────────────────────────────────────────────────────────────────

class ReadmeGenerator:
    """
    Builds a ReadmeContext from a ProjectModel and renders the Jinja2 template.

    Parameters
    ----------
    templates_dir : str | Path
        Directory containing ``readme_template.md.j2``.
    """

    FRAMEWORK_ENTRY_HINTS: dict[str, str] = {
        "FastAPI": "main.py",
        "Flask":   "app.py",
        "Django":  "manage.py",
    }

    def __init__(self, templates_dir: str | Path = "templates"):
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(disabled_extensions=("md.j2",)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        # Custom filters used in the template
        self._env.filters["title_case"] = self._title_case
        self._env.filters["urlencode"] = self._urlencode

    # ── Compatibility entry point ─────────────────────────────────────────────

    @classmethod
    def generate(cls, project: ProjectModel, workspace_path: str = ".") -> str:
        """
        Class method matching the original interface. Dynamically resolves templates dir.
        """
        current_dir = Path(__file__).parent.parent
        templates_dir = current_dir / "templates"
        gen = cls(templates_dir=templates_dir)
        return gen.render(project, Path(workspace_path))

    # ── Public entry point ────────────────────────────────────────────────────

    def render(self, project: ProjectModel, workspace_root: Path) -> str:
        """
        Render the README template and return the markdown string.

        Parameters
        ----------
        project : ProjectModel
            The parsed structural model.
        workspace_root : Path
            Root directory of the extracted/cloned repo (for file inspection).

        Returns
        -------
        str
            Fully rendered README.md content.
        """
        ctx = self.build_context(project, workspace_root)
        template = self._env.get_template("readme_template.md.j2")
        return template.render(**ctx.__dict__)

    # ── Context builder ───────────────────────────────────────────────────────

    def build_context(self, project: ProjectModel, root: Path) -> ReadmeContext:
        """
        Walk the ProjectModel and workspace files to populate a ReadmeContext.
        """
        ctx = ReadmeContext(project=project)

        ctx.total_loc = sum(f.loc for f in project.files)
        ctx.dir_count = len({str(Path(f.path).parent) for f in project.files})

        # ── Presence flags (inspect real files on disk) ────────────────────
        ctx.has_requirements_txt = (root / "requirements.txt").exists()
        ctx.has_pyproject_toml   = (root / "pyproject.toml").exists()
        ctx.has_package_json     = (root / "package.json").exists()
        ctx.has_yarn_lock        = (root / "yarn.lock").exists()
        ctx.has_dotenv           = self._package_in_deps(project, "python-dotenv")
        ctx.has_alembic          = (root / "alembic").is_dir()

        # ── License ───────────────────────────────────────────────────────
        license_file = next((root / n for n in ("LICENSE", "LICENSE.md", "LICENSE.txt")
                             if (root / n).exists()), None)
        if license_file:
            ctx.license_text = f"See [{license_file.name}]({license_file.name}) for details."

        # ── Python version (from pyproject.toml or fallback) ──────────────
        ctx.python_version = self._detect_python_version(root)

        # ── Entry points ──────────────────────────────────────────────────
        ctx.entry_points = project.entry_points or self._infer_entry_points(project, root)

        # ── Main module name (for uvicorn/flask run commands) ──────────────
        ctx.main_module = self._infer_main_module(ctx.entry_points)

        # ── Test detection ────────────────────────────────────────────────
        test_dirs = [d for d in ("tests", "test") if (root / d).is_dir()]
        ctx.has_tests = bool(test_dirs)
        ctx.test_dirs = test_dirs
        ctx.test_framework = self._detect_test_framework(project)
        ctx.coverage_tool = (
            "pytest-cov" if self._package_in_deps(project, "pytest-cov") else ""
        )
        ctx.source_dir = self._detect_source_dir(project, root)

        # ── Folder tree ───────────────────────────────────────────────────
        ctx.folder_tree = self._build_folder_tree(project, root)

        # ── Key files ─────────────────────────────────────────────────────
        ctx.key_files = self._build_key_files(project, root)

        # ── Features ──────────────────────────────────────────────────────
        ctx.features = self._extract_features(project)

        # ── npm scripts ───────────────────────────────────────────────────
        ctx.npm_scripts = self._read_npm_scripts(root)

        # ── Environment variables (scan for os.environ / getenv calls) ────
        ctx.env_vars = self._scan_env_vars(project, root)

        # ── Config files ──────────────────────────────────────────────────
        ctx.config_files = self._detect_config_files(root)

        # ── API routes (collected from the model if a framework was found) ─
        ctx.api_routes = self._collect_api_routes(project)

        # ── App factory detection ─────────────────────────────────────────
        ctx.has_app_factory = self._detect_app_factory(project)

        # ── Misc keywords for conditional blocks ──────────────────────────
        ctx.tech_keywords = [d.name.lower() for d in project.dependencies]

        return ctx

    # ── Private helpers ───────────────────────────────────────────────────────

    def _detect_python_version(self, root: Path) -> str:
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            text = pyproject.read_text(errors="replace")
            m = re.search(r'python_requires\s*=\s*"([^"]+)"', text)
            if m:
                return m.group(1)
        return "3.11+"

    def _detect_test_framework(self, project: ProjectModel) -> str:
        dep_names = [d.name.lower() for d in project.dependencies]
        if "pytest" in dep_names:
            return "pytest"
        # Check if any test file uses unittest directly
        for f in project.files:
            for imp in f.imports:
                if imp == "unittest":
                    return "unittest"
        return "pytest"

    def _detect_source_dir(self, project: ProjectModel, root: Path) -> str:
        """Return the main source directory (e.g. 'src', 'app', project name)."""
        candidates = ["src", "app", project.name.lower().replace("-", "_")]
        for c in candidates:
            if (root / c).is_dir():
                return c
        return "."

    def _infer_entry_points(self, project: ProjectModel, root: Path) -> list[str]:
        """Fallback: look for common entry-point filenames."""
        hints = ["main.py", "app.py", "run.py", "manage.py", "server.py", "wsgi.py"]
        return [h for h in hints if (root / h).exists()]

    def _infer_main_module(self, entry_points: list[str]) -> str:
        """Convert 'app/main.py' → 'app.main' for uvicorn-style strings."""
        if not entry_points:
            return "app"
        ep = entry_points[0].replace("/", ".").removesuffix(".py")
        return ep

    def _package_in_deps(self, project: ProjectModel, name: str) -> bool:
        return any(d.name.lower() == name.lower() for d in project.dependencies)

    def _build_folder_tree(self, project: ProjectModel, root: Path) -> str:
        """
        Build a text folder tree from the file paths in the model,
        skipping common noise directories.
        """
        SKIP = {".git", "__pycache__", "node_modules", ".venv", "venv",
                "dist", "build", ".mypy_cache", ".pytest_cache"}

        tree: dict = {}
        for file_model in project.files:
            parts = Path(file_model.path).parts
            node = tree
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = None

        def render_node(d: dict, prefix: str = "") -> str:
            lines = []
            items = sorted(d.items(), key=lambda x: (x[1] is None, x[0]))
            for i, (name, subtree) in enumerate(items):
                if name in SKIP:
                    continue
                connector = "└── " if i == len(items) - 1 else "├── "
                if subtree is None:
                    lines.append(f"{prefix}{connector}{name}")
                else:
                    lines.append(f"{prefix}{connector}{name}/")
                    extension = "    " if i == len(items) - 1 else "│   "
                    lines.append(render_node(subtree, prefix + extension))
            return "\n".join(lines)

        return render_node(tree)

    def _build_key_files(self, project: ProjectModel, root: Path) -> list[KeyFile]:
        PURPOSE_MAP = {
            "main.py":        "Application entry point",
            "app.py":         "Application factory / entry point",
            "manage.py":      "Django management CLI",
            "settings.py":    "Application settings",
            "config.py":      "Configuration loader",
            "models.py":      "Data models",
            "schema.py":      "Pydantic schema definitions",
            "routes.py":      "Route / URL definitions",
            "urls.py":        "URL configuration (Django)",
            "views.py":       "Request handlers / views",
            "serializers.py": "DRF serializers",
            "tasks.py":       "Background task definitions (Celery)",
            "utils.py":       "Shared utility helpers",
            "constants.py":   "Project-wide constants",
            "conftest.py":    "pytest fixtures and test configuration",
            "Dockerfile":     "Container image definition",
            "docker-compose.yml": "Multi-service container orchestration",
            "requirements.txt": "Python dependency list",
            "pyproject.toml":   "Project metadata and build config",
            "package.json":     "npm dependency list and scripts",
        }
        result = []
        for name, purpose in PURPOSE_MAP.items():
            matches = [f for f in project.files if Path(f.path).name == name]
            for f in matches:
                result.append(KeyFile(path=f.path, purpose=purpose))
        return result

    def _extract_features(self, project: ProjectModel) -> list[Feature]:
        """
        Infer feature bullet points from module/class/function docstrings.
        Returns a list; may be empty (template falls back to raw symbol listing).
        """
        features = []
        for file in project.files:
            if file.module_docstring:
                first_line = file.module_docstring.strip().splitlines()[0]
                if len(first_line) > 10:
                    features.append(Feature(
                        name=Path(file.path).stem.replace("_", " ").title(),
                        description=first_line.rstrip("."),
                    ))
        return features[:8]  # cap at 8 to avoid wall-of-text

    def _scan_env_vars(self, project: ProjectModel, root: Path) -> list[EnvVar]:
        """
        Scan Python files for os.environ['KEY'] and os.getenv('KEY') calls,
        and .env files, to build a list of environment variables.
        """
        env_vars: dict[str, EnvVar] = {}

        patterns = [
            re.compile(r'os\.environ\[[\'"]([\w]+)[\'"]\]'),
            re.compile(r'os\.getenv\([\'"]([\w]+)[\'"]\s*(?:,\s*[\'"][^\'"]*[\'"])?\)'),
            re.compile(r'os\.environ\.get\([\'"]([\w]+)[\'"]\)'),
        ]

        for file in project.files:
            if file.language != "python":
                continue
            full_path = root / file.path
            if not full_path.exists():
                continue
            text = full_path.read_text(errors="replace")
            for pattern in patterns:
                for match in pattern.finditer(text):
                    key = match.group(1)
                    if key not in env_vars:
                        env_vars[key] = EnvVar(
                            name=key,
                            example_value=self._guess_env_example(key),
                            description=self._guess_env_description(key),
                        )

        # Also read .env.example if present
        example_file = root / ".env.example"
        if example_file.exists():
            for line in example_file.read_text(errors="replace").splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    k = k.strip()
                    if k not in env_vars:
                        env_vars[k] = EnvVar(name=k, example_value=v.strip())

        return list(env_vars.values())

    def _guess_env_example(self, key: str) -> str:
        k = key.lower()
        if "secret" in k or "key" in k:
            return "your-secret-key-here"
        if "url" in k or "uri" in k:
            return "postgresql://user:pass@localhost/dbname"
        if "host" in k:
            return "localhost"
        if "port" in k:
            return "8000"
        if "debug" in k:
            return "false"
        if "token" in k:
            return "your-token-here"
        return ""

    def _guess_env_description(self, key: str) -> str:
        k = key.lower()
        if "secret" in k:
            return "Application secret key — keep private"
        if "database" in k or "db_url" in k:
            return "Full database connection string"
        if "debug" in k:
            return "Set to 'true' for development mode"
        if "host" in k:
            return "Host the application listens on"
        if "port" in k:
            return "Port the application listens on"
        if "redis" in k:
            return "Redis connection URL"
        return ""

    def _detect_config_files(self, root: Path) -> list[ConfigFile]:
        KNOWN = {
            ".flake8":        "Flake8 linter config",
            ".pylintrc":      "Pylint config",
            "mypy.ini":       "MyPy type-checker config",
            "pyproject.toml": "Build and tool config (PEP 517/518)",
            "setup.cfg":      "Setuptools config",
            ".pre-commit-config.yaml": "Pre-commit hooks",
            "Makefile":       "Build / task automation",
            ".github/workflows": "CI/CD workflow definitions",
            "alembic.ini":    "Alembic database migration config",
            "celeryconfig.py": "Celery configuration module",
        }
        result = []
        for path_str, purpose in KNOWN.items():
            p = root / path_str
            if p.exists():
                result.append(ConfigFile(path=path_str, purpose=purpose))
        return result

    def _read_npm_scripts(self, root: Path) -> dict:
        pkg = root / "package.json"
        if not pkg.exists():
            return {}
        try:
            import json
            data = json.loads(pkg.read_text(errors="replace"))
            return data.get("scripts", {})
        except Exception:
            return {}

    def _collect_api_routes(self, project: ProjectModel) -> list[ApiRoute]:
        """
        Collect routes from the structural model.

        For Phase 1 this returns routes inferred from decorator names on functions
        (e.g. @app.get, @router.post). A full route parser would also read
        the path string from the decorator arguments — that lives in the parser,
        not here; the parser stores it on FunctionModel.decorators for now.
        """
        routes = []
        HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}

        for file in project.files:
            for fn in file.functions:
                for dec in fn.decorators:
                    # Match patterns like @app.get, @router.post, @bp.route
                    m = re.match(r'(\w+)\.(get|post|put|patch|delete|route)\(', dec)
                    if m:
                        method_hint = m.group(2).upper()
                        if method_hint == "ROUTE":
                            method_hint = "GET"
                        routes.append(ApiRoute(
                            method=method_hint,
                            path=self._extract_path_from_decorator(dec),
                            handler=fn.name,
                            file=file.path,
                            description=fn.docstring.split(".")[0] if fn.docstring else "",
                            is_async=fn.is_async,
                        ))
        return routes

    def _extract_path_from_decorator(self, decorator: str) -> str:
        """Pull the first string argument from a decorator string like @app.get('/users')."""
        m = re.search(r'[\'"]([/\w{}<>:_-]+)[\'"]', decorator)
        return m.group(1) if m else "/unknown"

    def _detect_app_factory(self, project: ProjectModel) -> bool:
        """True if a function named create_app or make_app exists."""
        for file in project.files:
            for fn in file.functions:
                if fn.name in ("create_app", "make_app", "create_application"):
                    return True
        return False

    # ── Jinja2 custom filters ─────────────────────────────────────────────────

    @staticmethod
    def _title_case(value: str) -> str:
        return value.replace("-", " ").replace("_", " ").title()

    @staticmethod
    def _urlencode(value: str) -> str:
        from urllib.parse import quote
        return quote(value, safe=" ").replace(" ", "%20")
