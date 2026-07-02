"""
devdoc_generator.py
====================
Renders devdoc_template.md.j2 from a ProjectModel.

Usage
-----
    gen = DevdocGenerator(templates_dir="path/to/templates")
    markdown = gen.render(project_model)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.app.models.schema import ProjectModel, FileModel


@dataclass
class DevdocContext:
    """All variables the DEVELOPER template may reference."""

    project: ProjectModel
    total_loc: int = 0
    total_classes: int = 0
    total_functions: int = 0


class DevdocGenerator:
    """
    Builds a DevdocContext from a ProjectModel and renders the Jinja2 template.

    Parameters
    ----------
    templates_dir : str | Path
        Directory containing ``devdoc_template.md.j2``.
    """

    def __init__(self, templates_dir: str | Path = "templates"):
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(disabled_extensions=("md.j2",)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    # ── Compatibility entry point ─────────────────────────────────────────────

    @classmethod
    def generate(cls, project: ProjectModel, workspace_path: str = ".") -> str:
        """
        Class method matching the original interface. Dynamically resolves templates dir.
        """
        current_dir = Path(__file__).parent.parent
        templates_dir = current_dir / "templates"
        gen = cls(templates_dir=templates_dir)
        return gen.render(project)

    # ── Public entry point ────────────────────────────────────────────────────

    def render(self, project: ProjectModel) -> str:
        """
        Render the DEVELOPER template and return the markdown string.

        Parameters
        ----------
        project : ProjectModel
            The parsed structural model.

        Returns
        -------
        str
            Fully rendered DEVELOPER.md content.
        """
        ctx = self.build_context(project)
        template = self._env.get_template("devdoc_template.md.j2")
        return template.render(**ctx.__dict__)

    # ── Context builder ───────────────────────────────────────────────────────

    def build_context(self, project: ProjectModel) -> DevdocContext:
        """
        Walk the ProjectModel to populate a DevdocContext.
        """
        ctx = DevdocContext(project=project)

        ctx.total_loc = sum(f.loc for f in project.files)
        
        # Calculate counts
        for file in project.files:
            ctx.total_classes += len(file.classes)
            ctx.total_functions += len(file.functions)

        return ctx
