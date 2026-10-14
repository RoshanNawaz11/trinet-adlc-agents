"""Every rule file loads, has the agreed shape, and uses only facts that
rules/facts.yaml defines (or that the rule itself works out)."""

import ast
from pathlib import Path

import pytest
import yaml

from rules_engine.evaluate import STANDARD, _helpers
from rules_engine.tables import RULES_DIR, catalogue

RULE_FILES = sorted(p for p in RULES_DIR.glob("*/*.yaml") if p.parent.name != "tables")

TOP_KEYS = {"id", "version", "agent", "worker", "purpose", "applies_to", "inputs", "judgement", "lines",
            "compute", "checks", "cases", "outputs", "not_included", "to_confirm"}
CASE_TYPES = {"state", "pay_group", "employment_type", "termination_type"}
FUNCTIONS = set(_helpers({}))


def expr_names(text: str) -> set[str]:
    """Fact names an expression reads — its names, and missing_of's quoted ones."""
    tree = ast.parse(text, mode="eval")
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    unknown = {c.func.id for c in calls if isinstance(c.func, ast.Name)} - FUNCTIONS
    assert not unknown, f"unknown functions {unknown} in {text!r}"
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} - FUNCTIONS
    for call in (c for c in calls if getattr(c.func, "id", None) == "missing_of"):
        names |= {a.value for a in call.args if isinstance(a, ast.Constant)}
    return names


def when_names(when) -> set[str]:
    assert when is True or isinstance(when, str), f"a when is an expression or true: {when!r}"
    return set() if when is True else expr_names(when)


def then_names(value) -> set[str]:
    """Facts a `then` reads: its `=` expressions."""
    if isinstance(value, str):
        return expr_names(value[1:].strip()) if value.startswith("=") else set()
    if isinstance(value, dict):
        for flag in [value.get("flag")] + list(value.get("flags") or []):
            if flag:
                assert flag["kind"] in ("input", "check", "decision"), flag
        return set().union(*(then_names(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(*(then_names(v) for v in value))
    return set()


def check_rule(rule: dict, facts: dict) -> list[str]:
    errors = [f"unknown key {k!r}" for k in rule if k not in TOP_KEYS]
    errors += [f"applies_to: {k!r} is not a case type" for k in rule.get("applies_to", {}) if k not in CASE_TYPES]

    local: set[str] = set()      # names the rule works out itself
    used: set[str] = set(rule.get("inputs", []))
    for line in rule.get("lines", []):
        used |= {line["for_each"], *line["each"]}
        for case in line.get("checks", []) + line["cases"]:
            local |= set(case["then"]) - STANDARD
            used |= when_names(case["when"]) | then_names(case["then"])
        for name, total in line["total"].items():
            local.add(name)
            assert len(set(total) & {"sum", "count", "collect"}) == 1, total
            if "where" in total:
                used |= expr_names(total["where"])
    for item in rule.get("compute", []):
        (name, expression), = item.items()
        used |= expr_names(expression)
        local.add(name)
    for case in rule.get("checks", []) + rule["cases"]:
        assert set(case) <= {"when", "then", "why"}, case
        used |= when_names(case["when"]) | then_names(case["then"])
        local |= set(case["then"]) - STANDARD

    errors += [f"uses {n!r}, which facts.yaml doesn't define" for n in sorted(used - local - set(facts))]
    errors += [f"outputs {n!r}, which facts.yaml doesn't define" for n in rule.get("outputs", [])
               if n not in facts and n not in STANDARD]
    return errors


def test_fact_entries_have_only_known_keys():
    """An unquoted comma in a one-line entry splits it into a junk key."""
    keys = {"meaning", "type", "values", "source", "per", "unit", "note", "item_facts"}
    assert [n for n, e in catalogue().items() if isinstance(e, dict) and set(e) - keys] == []


@pytest.mark.parametrize("path", RULE_FILES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_rule_is_well_formed(path: Path):
    rule = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert rule["id"] == f"{path.parent.name}.{path.stem}"
    assert rule["cases"][-1]["when"] is True, "the last case should always hold (when: true)"
    assert check_rule(rule, catalogue()) == []
