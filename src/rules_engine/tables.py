"""Decision tables (rules/tables/*.yaml): the row matching a case's keys
becomes facts. Every name a table uses must be in rules/facts.yaml."""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Any

import yaml

RULES_DIR = Path(__file__).resolve().parents[2] / "rules"


@cache
def catalogue() -> dict[str, Any]:
    return yaml.safe_load((RULES_DIR / "facts.yaml").read_text(encoding="utf-8"))


@cache
def load_table(name: str) -> dict[str, Any]:
    table = yaml.safe_load((RULES_DIR / "tables" / f"{name}.yaml").read_text(encoding="utf-8"))
    if unknown := [n for n in (*table["keys"], *table["values"]) if n not in catalogue()]:
        raise ValueError(f"tables.{name} uses facts not in facts.yaml: {unknown}")
    return table


def lookup(name: str, facts: dict[str, Any]) -> dict[str, Any]:
    """The values of the row whose keys match the facts — all None when no row
    matches, never another row's values."""
    table = load_table(name)
    for row in table["rows"]:
        if all(row[k] == facts.get(k) for k in table["keys"]):
            return {v: row[v] for v in table["values"]}
    return dict.fromkeys(table["values"])
