import os
from jinja2 import Template
from backend.app.models.schema import ProjectModel

DEVDOC_TEMPLATE = """# Architecture & Developer Documentation

## 🏗️ System Architecture & Import Graph
This diagram shows the relationship and import dependencies between modules in the codebase.

```mermaid
graph TD
{% if project.import_graph and project.import_graph.items()|length > 0 %}
  {% for source, targets in project.import_graph.items() %}
    {% for target in targets %}
  {{ source | replace("/", "_") | replace(".", "_") | replace("-", "_") }}["{{ source }}"] --> {{ target | replace("/", "_") | replace(".", "_") | replace("-", "_") }}["{{ target }}"]
    {% endfor %}
  {% endfor %}
{% else %}
  No cross-file import relationships detected.
{% endif %}
```

---

## 📁 File Reference Catalog

{% for file in project.files %}
### 📄 `{{ file.path }}`
- **Language:** {{ file.language }}
- **Lines of Code:** {{ file.loc }}
{% if file.module_docstring %}
- **Details:** {{ file.module_docstring }}
{% endif %}

{% if file.classes %}
#### Classes
| Class Name | Line | Inherits From | Description |
|---|---|---|---|
{% for cls in file.classes %}
| `{{ cls.name }}` | {{ cls.line_number }} | {{ cls.base_classes | join(", ") }} | {{ cls.docstring or "No description." }} |
{% endfor %}

{% for cls in file.classes %}
{% if cls.methods %}
##### Methods inside `{{ cls.name }}`
| Method Name | Line | Async | Arguments | Return Type |
|---|---|---|---|---|
{% for method in cls.methods %}
| `{{ method.name }}` | {{ method.line_number }} | {{ method.is_async }} | {% for param in method.params %}`{{ param.name }}`{% if param.type_hint %}: {{ param.type_hint }}{% endif %}{% if not loop.last %}, {% endif %}{% endfor %} | `{{ method.return_type or 'Any' }}` |
{% endfor %}
{% endif %}
{% endfor %}
{% endif %}

{% if file.functions %}
#### Functions
| Function Name | Line | Async | Arguments | Return Type | Description |
|---|---|---|---|---|---|
{% for func in file.functions %}
| `{{ func.name }}` | {{ func.line_number }} | {{ func.is_async }} | {% for param in func.params %}`{{ param.name }}`{% if param.type_hint %}: {{ param.type_hint }}{% endif %}{% if not loop.last %}, {% endif %}{% endfor %} | `{{ func.return_type or 'Any' }}` | {{ func.docstring or "No description." }} |
{% endfor %}
{% endif %}

---
{% endfor %}

---
*DEVELOPER.md generated automatically by [CodeAtlas](https://github.com/your-repo/codeatlas) with zero LLM calls.*
"""

class DevdocGenerator:
    @staticmethod
    def generate(project: ProjectModel) -> str:
        """
        Generates DEVELOPER.md content string from ProjectModel.
        """
        template = Template(DEVDOC_TEMPLATE)
        # Helper filter to replace chars for safe Mermaid IDs
        return template.render(project=project)
