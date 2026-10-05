"""Worker agents. Each one runs its agent's published skill; the input's
`worker` says which part of the skill applies."""

from __future__ import annotations

import json
from typing import Any

from agents.model.gateway import get_default_gateway
from agents.skills.client import run_skill
from agents.skills.registry import ensure_bundle_published
from json_utils import JSONParseError, extract_json

_CHECKER_JSON = (
    "Your final answer must be a single JSON object: "
    '{"findings": {"<output field>": <value or null>}, '
    '"steps": [{"check": "<name>", "result": "pass" | "fail" | "not available" | "<value>", "evidence": {...}}], '
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
