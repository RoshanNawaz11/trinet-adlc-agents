"""Worker agents. Each one runs its agent's published skill; the input's
`worker` says which part of the skill applies."""

from __future__ import annotations

import json
from typing import Any

from agents.model.gateway import get_default_gateway
from rules_engine.decide import ask_for, decide
from agents.skills.client import MAX_TOKENS, run_skill
from agents.skills.registry import ensure_bundle_published
from json_utils import JSONParseError, extract_json

_CHECKER_JSON = (
    "Your final answer must be a single JSON object: "
    '{"findings": {"<output field>": <value or null>}, '
    '"steps": [{"check": "<name>", "result": "pass" | "fail" | "not available" | "<value>", '
    '"outcome": "stop" | "wait" | "note" | null, "evidence": {...}}], '
    '"flags": [{"type": "<flag>", "title": "<one line>", "detail": {...}}]}. '
    "Return ONLY JSON — no preamble, no markdown fences."
)


async def run_worker_skill(bundle: str, i: dict[str, Any], json_instruction: str, key: str) -> Any:
    gateway = get_default_gateway()
    skill_id, version_id = await ensure_bundle_published(bundle, gateway=gateway)
    config = gateway.policy.get(bundle, gateway.policy["default"])
    executed = await run_skill(
        skill_id, version_id, json.dumps(i, indent=2, default=str, ensure_ascii=False),
        model=config["model"], additional_instructions=json_instruction, gateway=gateway,
        max_tokens=config.get("max_tokens", MAX_TOKENS),
    )
    return extract_json(executed["raw_response"], key=key)


async def run_checker(bundle: str, worker: str, i: dict[str, Any]) -> dict[str, Any]:
    """A checker worker: runs its checks for one case and returns what it found."""
    findings = await run_worker_skill(bundle, {"worker": worker, **i}, _CHECKER_JSON, key="steps")
    if not isinstance(findings, dict) or not isinstance(findings.get("steps"), list):
        raise JSONParseError(f"{bundle} {worker}: answer must be {{'steps': [...]}}")
    return {
        "case": i.get("case"),
        "worker": worker,
        "findings": findings.get("findings") or {},
        "steps": findings["steps"],
        "flags": findings.get("flags") or [],
    }


async def run_with_rules(bundle: str, worker: str, i: dict[str, Any]) -> dict[str, Any]:
    """A worker whose rules are in rules/: the model reports the facts, the rules decide.
    The case's attributes and state law, which the agent fetched with the rules, are
    facts already; the model doesn't get the rules — it doesn't apply them."""
    fetched = i.get("rules") or {}
    known = {k: v for k, v in {**(fetched.get("attributes") or {}), **(fetched.get("state_law") or {})}.items()
             if v is not None}
    task = {"worker": worker, **{k: v for k, v in i.items() if k != "rules"}}
    answer = await run_worker_skill(bundle, task, ask_for(bundle, worker), key="facts")
    if not isinstance(answer, dict) or not isinstance(answer.get("facts"), dict):
        raise JSONParseError(f"{bundle} {worker}: answer must be {{'facts': {{...}}}}")
    sources = {**(answer.get("sources") or {}), **dict.fromkeys(known, "fetched with the rules")}
    return {"case": i.get("case"), "worker": worker,
            **decide(bundle, worker, {**answer["facts"], **known}, sources)}
