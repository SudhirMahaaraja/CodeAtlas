import os
from jinja2 import Template
from backend.app.models.schema import ProjectModel

README_TEMPLATE = """# {{ project.name }}

## Description
{% if project.files and project.files[0].module_docstring %}
{{ project.files[0].module_docstring }}
{% else %}
A project statically analyzed by CodeAtlas.
{% endif %}

## 🛠️ Tech Stack & Frameworks
{% if project.detected_frameworks %}
**Detected Frameworks/Technologies:**
{% for framework in project.detected_frameworks %}
- {{ framework }}
{% endfor %}
{% else %}
No major frameworks detected. Standard codebase.
{% endif %}

### Dependencies
{% if project.dependencies %}
{% for dep in project.dependencies[:15] %}
- `{{ dep.name }}` {% if dep.version %}({{ dep.version }}){% endif %} - via *{{ dep.source }}*
{% endfor %}
{% if project.dependencies|length > 15 %}
- *and {{ project.dependencies|length - 15 }} more...*
{% endif %}
{% else %}
No dependencies detected.
{% endif %}

## 📁 File Structure
```text
{% for file in project.files %}
{{ file.path }} ({{ file.language }}, {{ file.loc }} LOC)
{% endfor %}
```

## 🚀 Setup & Execution
{% if 'FastAPI' in project.detected_frameworks or 'Flask' in project.detected_frameworks or 'Django' in project.detected_frameworks %}
### Python/Backend Project Setup
1. **Create Virtual Environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
   ```
2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run Application:**
   {% if 'FastAPI' in project.detected_frameworks %}
   ```bash
   uvicorn app.main:app --reload
   ```
   {% elif 'Flask' in project.detected_frameworks %}
   ```bash
   flask run
   ```
   {% elif 'Django' in project.detected_frameworks %}
   ```bash
   python manage.py runserver
   ```
   {% endif %}
{% endif %}

{% if 'React' in project.detected_frameworks or 'Next.js' in project.detected_frameworks or 'Express.js' in project.detected_frameworks %}
### Node.js/Frontend Project Setup
1. **Install Dependencies:**
   ```bash
   npm install
   ```
2. **Run Dev Server:**
   ```bash
   npm run dev
   ```
{% endif %}

---
*README generated automatically by [CodeAtlas](https://github.com/your-repo/codeatlas) with zero LLM calls.*
"""

class ReadmeGenerator:
    @staticmethod
    def generate(project: ProjectModel) -> str:
        """
        Generates a README.md content string from ProjectModel.
        """
        template = Template(README_TEMPLATE)
        return template.render(project=project)
