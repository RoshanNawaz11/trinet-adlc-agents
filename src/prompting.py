"""Render Jinja2 prompt templates for orchestrator/planner nodes."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def render_prompt(path: Path, **kwargs: object) -> str:
    path = Path(path)
    env = Environment(
        loader=FileSystemLoader(str(path.parent)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env.get_template(path.name).render(**kwargs)
