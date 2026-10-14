"""Runs a rule (rules/<folder>/<name>.yaml) against a case's facts. The rule
format is described in rules/README.md; expressions are evaluated by
simpleeval, which allows only maths, comparisons and the helpers below.

    record = evaluate(load_rule("payroll.leave-payout"), facts)
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from functools import cache
from typing import Any

import yaml
from simpleeval import EvalWithCompoundTypes

from rules_engine.tables import RULES_DIR

Facts = dict[str, Any]
STANDARD = {"result", "outcome", "reason", "provisional", "note", "flag", "flags"}


# ── loading and choosing rules ────────────────────────────────────────────

@cache
def load_rule(rule_id: str) -> dict[str, Any]:
    folder, name = rule_id.split(".", 1)
    return yaml.safe_load((RULES_DIR / folder / f"{name}.yaml").read_text(encoding="utf-8"))


def all_rules() -> list[dict[str, Any]]:
    return [load_rule(f"{p.parent.name}.{p.stem}")
            for p in sorted(RULES_DIR.glob("*/*.yaml")) if p.parent.name != "tables"]


def applies(rule: dict[str, Any], facts: Facts) -> bool:
    """Every case type in applies_to is `any` or holds the case's value."""
    return all(allowed == "any" or facts.get(t) in allowed for t, allowed in rule.get("applies_to", {}).items())


def rules_for(agent: str, worker: str | None, facts: Facts) -> list[dict[str, Any]]:
    return [r for r in all_rules() if r.get("agent") == agent and r.get("worker") == worker and applies(r, facts)]


# ── expressions ───────────────────────────────────────────────────────────

def _due_date(form, amount, start, next_payday=None, period_end=None):
    """Applies a deadline form from tables/state (facts.yaml → due)."""
    if form is None or start is None:
        return None
    if form in ("within_hours", "calendar_days", "business_days") and amount is None:
        return None
    if form == "immediately":
        return start
    if form == "within_hours":
        return start + timedelta(days=math.ceil(amount / 24))
    if form == "calendar_days":
        return start + timedelta(days=amount)
    if form in ("next_business_day", "business_days"):
        d, left = start, 1 if form == "next_business_day" else amount
        while left:
            d += timedelta(days=1)
            left -= d.weekday() < 5
        return d
    return {"next_regular_payday": next_payday, "end_of_pay_period": period_end}.get(form)


def _helpers(facts: Facts) -> dict[str, Any]:
    def present(values):
        return [v for v in values if v is not None]

    def largest_difference(**pairs):
        diffs = {k: abs(a - b) for k, (a, b) in pairs.items() if a is not None and b is not None and abs(a - b) > 0.005}
        return max(diffs, key=diffs.get) if diffs else None

    def smallest(**values):
        values = {k: v for k, v in values.items() if v is not None}
        return min(values, key=values.get) if values else None

    return {
        "min": lambda *xs: min(present(xs), default=None),
        "max": lambda *xs: max(present(xs), default=None),
        "round": round, "abs": abs, "len": len,
        "within": lambda a, b, tolerance: None if a is None or b is None else abs(a - b) <= tolerance + 1e-9,
        "missing": lambda *xs: any(x is None for x in xs),
        "missing_of": lambda *names: [n for n in names if facts.get(n) is None],
        "mentions": lambda text, words: isinstance(text, str) and any(w.lower() in text.lower() for w in words),
        "lower": lambda text: text.lower() if isinstance(text, str) else text,
        "first": lambda xs: xs[0] if xs else None,
        "days_between": lambda a, b: None if a is None or b is None else (b - a).days,
        "hours_between": lambda a, b: None if a is None or b is None else (b - a).total_seconds() / 3600,
        "add_days": lambda d, n: None if d is None or n is None else d + timedelta(days=n),
        "due_date": _due_date,
        "largest_difference": largest_difference,
        "smallest": smallest,
    }


def calc(expression: str, facts: Facts) -> Any:
    """An expression's value — None (not available) when it uses a fact that isn't."""
    evaluator = EvalWithCompoundTypes(names=lambda node: facts.get(node.id), functions=_helpers(facts))
    try:
        return evaluator.eval(expression)
    except (TypeError, ZeroDivisionError):
        return None


def holds(when: str | bool, facts: Facts) -> bool:
    return when is True or (isinstance(when, str) and bool(calc(when, facts)))


def resolve(value: Any, facts: Facts) -> Any:
    """A `then` value: text starting with `=` is an expression; anything else as written."""
    if isinstance(value, str) and value.startswith("="):
        return calc(value[1:].strip(), facts)
    if isinstance(value, dict):
        return {k: resolve(v, facts) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, facts) for v in value]
    return value


def _typed(value: Any) -> Any:
    """ISO date and time texts as dates and times, so they compare as such."""
    if isinstance(value, str) and len(value) >= 10 and value[4] == "-" and value[7] == "-":
        try:
            return date.fromisoformat(value) if len(value) == 10 else datetime.fromisoformat(value)
        except ValueError:
            return value
    if isinstance(value, dict):
        return {k: _typed(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_typed(v) for v in value]
    return value


def _plain(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


# ── running a rule ────────────────────────────────────────────────────────

def _first(cases: list[dict], facts: Facts) -> tuple[int, dict]:
    for number, case in enumerate(cases, 1):
        if holds(case["when"], facts):
            return number, resolve(case["then"], facts)
    return 0, {}


def _report(then: dict, rule_id: str, record: dict) -> None:
    """Gather what a `then` reports — flags, notes, provisional — into the record."""
    for flag in then.get("flags", []) + ([then["flag"]] if "flag" in then else []):
        record["flags"].append({**flag, "rule": rule_id})
    if "note" in then:
        record["notes"].append(then["note"])
    if then.get("provisional"):
        record["provisional"] = True


def _total(spec: dict, rows: list[Facts], facts: Facts) -> Any:
    rows = [r for r in rows if "where" not in spec or holds(spec["where"], {**facts, **r})]
    if "count" in spec:
        return len(rows)
    if "collect" in spec:
        return [r[spec["collect"]] for r in rows if r.get(spec["collect"]) is not None]
    values = [r.get(spec["sum"]) for r in rows]
    return None if None in values else round(sum(values), 2)


def evaluate(rule: dict[str, Any], facts: Facts) -> dict[str, Any]:
    """The decision record: which case held, the outputs, and every flag and note."""
    facts = _typed(dict(facts))
    record: dict[str, Any] = {
        "rule": rule["id"], "version": rule["version"],
        "inputs": {n: facts.get(n) for n in rule.get("inputs", [])},
        "lines": [], "flags": [], "notes": [], "provisional": False,
    }

    for block in rule.get("lines", []):
        rows = []
        for item in facts.get(block["for_each"]) or []:
            item_facts = {**facts, **item}
            for check in block.get("checks", []):
                if holds(check["when"], item_facts):
                    _report(resolve(check["then"], item_facts), rule["id"], record)
            number, then = _first(block["cases"], item_facts)
            _report(then, rule["id"], record)
            row = {**item, **{k: v for k, v in then.items() if k not in STANDARD}}
            rows.append(row)
            record["lines"].append({"for_each": block["for_each"], "case": number, **row})
        facts |= {name: _total(spec, rows, facts) for name, spec in block["total"].items()}

    for item in rule.get("compute", []):
        (name, expression), = item.items()
        facts[name] = calc(expression, facts)

    for check in rule.get("checks", []):
        if holds(check["when"], facts):
            _report(resolve(check["then"], facts), rule["id"], record)

    number, then = _first(rule["cases"], facts)
    _report(then, rule["id"], record)
    record |= {
        "case": number,
        "result": then.get("result"),
        "outcome": then.get("outcome"),
        "reason": then.get("reason"),
        "outputs": {n: then[n] if n in then else facts.get(n) for n in rule.get("outputs", []) if n not in STANDARD},
    }
    return _plain(record)
