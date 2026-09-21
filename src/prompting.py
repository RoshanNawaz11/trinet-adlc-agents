"""Tiny Jinja2 wrapper, used by any node that renders a prompts/*.jinja file
before calling the model. Kept as one function (rather than each node
re-implementing `Template(path.read_text()).render(...)`) so template loading
behaves identically everywhere.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Template


def render_prompt(path: Path, **variables: object) -> str:
    return Template(path.read_text()).render(**variables)
