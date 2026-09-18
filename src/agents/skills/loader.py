"""
Reads skill bundles from the skills directory and returns a list of skill names
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from agents.graph.states import Step

SKILLS_DIR = Path(__file__).parent
_SKIP_DIR_NAMES = {"__pycache__", ".cache"}
_SKIP_SUFFIXES = {".py", ".pyc", ".pyo"}


# List available skill bundle directory names.
def list_bundle_names() -> list[str]:
    names: list[str] = []
    for path in sorted(SKILLS_DIR.iterdir()):
        if path.name in _SKIP_DIR_NAMES or not path.is_dir():
            continue
        if any(child.name.lower() == 'skill.md' for child in path.iterdir() if child.is_file()):
            names.append(path.name)
    return names


#read those skill files
# Read the skill bundle files
async def read_bundle_files(bundle_name: str) -> list[tuple[str, str]]:
    bundle_dir = SKILLS_DIR / bundle_name

    if not bundle_dir.is_dir():
        raise ValueError(f"Bundle directory {bundle_dir} does not exist")

    files: list[tuple[str, str]] = []

    for abs_path in sorted(bundle_dir.rglob("*")):
        if not abs_path.is_file():
            continue

        if abs_path.suffix.lower() in _SKIP_SUFFIXES:
            continue

        relative_path = abs_path.relative_to(bundle_dir)

        # Skip files inside excluded directories
        if any(part in _SKIP_DIR_NAMES for part in relative_path.parts[:-1]):
            continue

        rel_name = relative_path.as_posix()

        try:
            content = abs_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = abs_path.read_bytes().decode("latin-1")

        files.append((rel_name, content))

    return normalize_skill_md(files, bundle_name)


"""
renaming the file to SKILL.md and adding the mandatory frontmatter as its required to process the skill file via anthropic
"""
def normalize_skill_md(files: list[tuple[str, str]], bundle_name: str) -> list[tuple[str, str]]:
    has_upper = any(name == "SKILL.md" for name, _ in files)
    if has_upper:
        return [(n, c) for n, c in files if n == "SKILL.md" or n.lower() != "skill.md"]

    skill_entry: tuple[str, str] | None = None
    for name, content in files:
        if name.lower() == "skill.md":
            skill_entry = (name, content)
            break
    if skill_entry is None:
        raise FileNotFoundError(f"No skill.md / SKILL.md in bundle {bundle_name}")

    _, content = skill_entry
    if not content.lstrip().startswith("---"):
        content = (
            f"---\n"
            f"name: {bundle_name}\n"
            f"description: {bundle_name} skill\n"
            f"---\n\n"
            f"{content}"
        )
    rest = [(n, c) for n, c in files if n.lower() != "skill.md"]
    rest.append(("SKILL.md", content))
    return rest


def format_for_skill(step: Step) -> str:
    """User-message body for the published skill (same role as FAWM format_for_skill)."""
    payload: dict[str, Any] = dict(step.get("input") or {})
    skill = step["skill"]
    if skill == "classify":
        payload["content"] = content_as_text(payload.get("content"))
    body = {
        "step_id": step["step_id"],
        "skill": skill,
        "input": payload,
    }
    return json.dumps(body, indent=2, ensure_ascii=False)


def content_as_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        parts = [str(content.get("summary") or "")]
        key_points = content.get("key_points") or []
        if isinstance(key_points, list):
            parts.extend(str(point) for point in key_points)
        return "\n".join(part for part in parts if part)
    return ""
