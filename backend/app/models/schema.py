from pydantic import BaseModel
from typing import Optional, List, Dict

class ParamModel(BaseModel):
    name: str
    type_hint: Optional[str] = None
    default: Optional[str] = None

class FunctionModel(BaseModel):
    name: str
    docstring: Optional[str] = None
    params: List[ParamModel] = []
    return_type: Optional[str] = None
    decorators: List[str] = []
    is_async: bool = False
    line_number: int
    calls: List[str] = []

class ClassModel(BaseModel):
    name: str
    docstring: Optional[str] = None
    base_classes: List[str] = []
    methods: List[FunctionModel] = []
    line_number: int

class FileModel(BaseModel):
    path: str
    language: str                   # "python" | "javascript" | "html" | "css"
    module_docstring: Optional[str] = None
    imports: List[str] = []
    classes: List[ClassModel] = []
    functions: List[FunctionModel] = []
    loc: int

class DependencyInfo(BaseModel):
    name: str
    version: Optional[str] = None
    source: str                     # "requirements.txt" | "pyproject.toml" | "package.json"

class ProjectModel(BaseModel):
    name: str
    root_path: str
    detected_frameworks: List[str] = []
    dependencies: List[DependencyInfo] = []
    entry_points: List[str] = []
    files: List[FileModel] = []
    import_graph: Dict[str, List[str]] = {}
