"""Wires the rules into a worker: the model reports the facts the worker's
rules need, and the rules decide.

    instruction = ask_for("payroll-calculation", "leave")              # what the model reports
    result = decide("payroll-calculation", "leave", facts, sources)    # {"findings", "steps", "flags"}
"""

from __future__ import annotations

import json
from typing import Any

from rules_engine.evaluate import STANDARD, Facts, all_rules, evaluate, rules_for
from rules_engine.tables import catalogue, lookup

CASE_TYPES = ["state", "pay_group", "employment_type", "termination_type"]


def _rules(agent: str, worker: str | None) -> list[dict[str, Any]]:
    return [r for r in all_rules() if r.get("agent") == agent and r.get("worker") == worker]


def ask_for(agent: str, worker: str | None) -> str:
    """The instruction for the model: which facts to report, what each means,
    and the rules' guidance on facts that need judgement."""
    names = dict.fromkeys(CASE_TYPES)
    guidance: list[str] = []
    for rule in _rules(agent, worker):
        names |= dict.fromkeys(rule.get("inputs", []))
        names |= dict.fromkeys(block["for_each"] for block in rule.get("lines", []))
        guidance += rule.get("judgement", [])
    known = catalogue()
    wanted = {n: known.get(n) for n in names}
    for name, entry in list(wanted.items()):
        for item in (entry or {}).get("item_facts", []):
            wanted[f"{name}[].{item}"] = known.get(item)
    return (
        "Report the facts below for this case — don't calculate or decide anything; "
        "code applies the rules to your facts. Give each fact's value from the order, "
        "the data and the other agents' results, or null when it isn't there — never guess. "
        "Dates as YYYY-MM-DD; a list fact is a list of objects with its `[]` fields.\n"
        f"Facts: {json.dumps(wanted, ensure_ascii=False, default=str)}\n"
        + (f"Guidance: {json.dumps(guidance, ensure_ascii=False)}\n" if guidance else "")
        + 'Your final answer must be a single JSON object: {"facts": {"<fact>": <value or null>}, '
        '"sources": {"<fact>": "<where its value came from>"}}. '
        "Return ONLY JSON — no preamble, no markdown fences."
    )


def decide(agent: str, worker: str | None, facts: Facts, sources: dict | None = None) -> dict[str, Any]:
    """Runs the worker's rules on the facts: findings, one step per rule, and the rules' flags."""
    facts = dict(facts)
    facts |= {k: v for k, v in lookup("state", facts).items() if v is not None}
    findings: dict[str, Any] = {"rules": {}}
    steps = [{"check": "Facts reported", "result": "ok", "evidence": {"facts": facts, "sources": sources or {}}}]
    flags = []
    for rule in rules_for(agent, worker, facts):
        record = evaluate(rule, facts)
        outputs = {k: v for k, v in record["outputs"].items() if k not in STANDARD}
        facts |= outputs          # a later rule can use an earlier one's outputs
        findings |= outputs
        findings["rules"][record["rule"]] = {k: record[k] for k in ("result", "outcome", "reason", "provisional")}
        steps.append({
            "check": record["rule"],
            "result": record["result"],
            "evidence": {k: record[k] for k in ("version", "case", "reason", "inputs", "lines", "notes", "provisional")},
        })
        flags += [
            {"type": f.get("type") or record["rule"], "title": f["title"],
             "detail": {**(f.get("detail") or {}), "kind": f["kind"], "rule": record["rule"]}}
            for f in record["flags"]
        ]
    return {"findings": findings, "steps": steps, "flags": flags}
