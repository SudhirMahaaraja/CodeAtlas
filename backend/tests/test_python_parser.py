import os
import tempfile
import pytest
from backend.app.parsers.python_parser import PythonParser
from backend.app.models.schema import FileModel

def test_parse_simple_python_code():
    code_content = '''"""
Module docstring here.
"""
import sys
from os import path

class Calculator:
    """A simple calculator class."""
    def add(self, a: int, b: int = 0) -> int:
        return a + b

def calculate_sum(numbers: list) -> int:
    calc = Calculator()
    return calc.add(1, 2)
'''

    # Write to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as temp_file:
        temp_file.write(code_content)
        temp_file_path = temp_file.name

    try:
        # Parse using PythonParser
        file_model = PythonParser.parse_file(temp_file_path, "temp_calc.py")
        
        assert file_model is not None
        assert file_model.path == "temp_calc.py"
        assert file_model.language == "python"
        assert "Module docstring here." in file_model.module_docstring
        assert "sys" in file_model.imports
        assert "os.path" in file_model.imports
        
        # Test Class Model
        assert len(file_model.classes) == 1
        cls = file_model.classes[0]
        assert cls.name == "Calculator"
        assert "A simple calculator class." in cls.docstring
        assert len(cls.methods) == 1
        
        # Test Method Model
        method = cls.methods[0]
        assert method.name == "add"
        assert len(method.params) == 3 # self, a, b
        assert method.params[1].name == "a"
        assert method.params[1].type_hint == "int"
        
        # Test Function Model
        assert len(file_model.functions) == 1
        func = file_model.functions[0]
        assert func.name == "calculate_sum"
        assert func.return_type == "int"
        assert "add" in func.calls

    finally:
        os.remove(temp_file_path)
