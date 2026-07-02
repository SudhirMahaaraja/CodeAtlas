import ast
import logging
from typing import Optional, List
from backend.app.models.schema import FileModel, ClassModel, FunctionModel, ParamModel

logger = logging.getLogger(__name__)

class PythonParser:
    @staticmethod
    def parse_file(file_path: str, relative_path: str) -> Optional[FileModel]:
        """
        Parses a python file using the AST module.
        Returns a FileModel or None if parsing fails.
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
            loc = len(content.splitlines())
            tree = ast.parse(content, filename=file_path)
            
            # Module docstring
            module_doc = ast.get_docstring(tree)
            
            imports = []
            classes = []
            functions = []
            
            # Helper to extract calls inside a node
            def extract_calls(node) -> List[str]:
                calls = []
                for subnode in ast.walk(node):
                    if isinstance(subnode, ast.Call):
                        if isinstance(subnode.func, ast.Name):
                            calls.append(subnode.func.id)
                        elif isinstance(subnode.func, ast.Attribute):
                            calls.append(subnode.func.attr)
                return list(set(calls))

            # Helper to parse arguments/parameters
            def parse_params(arguments: ast.arguments) -> List[ParamModel]:
                params = []
                
                # Check for standard arguments
                # Note: arguments.args matches standard positional/keyword arguments
                for arg in arguments.args:
                    type_hint = None
                    if arg.annotation:
                        type_hint = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else None
                        
                    params.append(ParamModel(
                        name=arg.arg,
                        type_hint=type_hint,
                        default=None # We could parse defaults, but type-hints and names are primary
                    ))
                return params

            # Helper to parse function/method definition
            def parse_function_def(node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionModel:
                docstring = ast.get_docstring(node)
                params = parse_params(node.args)
                
                return_type = None
                if node.returns:
                    return_type = ast.unparse(node.returns) if hasattr(ast, 'unparse') else None
                    
                decorators = []
                for dec in node.decorator_list:
                    try:
                        decorators.append(ast.unparse(dec) if hasattr(ast, 'unparse') else getattr(dec, 'id', ''))
                    except Exception:
                        pass
                        
                calls = extract_calls(node)
                is_async = isinstance(node, ast.AsyncFunctionDef)
                
                return FunctionModel(
                    name=node.name,
                    docstring=docstring,
                    params=params,
                    return_type=return_type,
                    decorators=decorators,
                    is_async=is_async,
                    line_number=node.lineno,
                    calls=calls
                )

            # Walk first level to get imports, classes, functions
            for node in tree.body:
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for name in node.names:
                        imports.append(f"{module}.{name.name}" if module else name.name)
                        
                elif isinstance(node, ast.ClassDef):
                    class_doc = ast.get_docstring(node)
                    base_classes = []
                    for base in node.bases:
                        try:
                            base_classes.append(ast.unparse(base) if hasattr(ast, 'unparse') else getattr(base, 'id', ''))
                        except Exception:
                            pass
                            
                    methods = []
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            methods.append(parse_function_def(item))
                            
                    classes.append(ClassModel(
                        name=node.name,
                        docstring=class_doc,
                        base_classes=base_classes,
                        methods=methods,
                        line_number=node.lineno
                    ))
                    
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append(parse_function_def(node))
                    
            return FileModel(
                path=relative_path.replace("\\", "/"),
                language="python",
                module_docstring=module_doc,
                imports=imports,
                classes=classes,
                functions=functions,
                loc=loc
            )
            
        except SyntaxError as se:
            logger.warning(f"Syntax error parsing {file_path}: {se}")
            # Degrade gracefully by returning basic file info with 0 loc
            return FileModel(
                path=relative_path.replace("\\", "/"),
                language="python",
                module_docstring=f"Syntax Error: Could not parse python file. {str(se)}",
                imports=[],
                classes=[],
                functions=[],
                loc=0
            )
        except Exception as e:
            logger.error(f"Error parsing python file {file_path}: {e}", exc_info=True)
            return None
