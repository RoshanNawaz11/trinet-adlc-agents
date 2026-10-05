"""Validation's extractor worker — a model. It reads the service order and
returns the facts of each case as typed fields (skills/validation: skill.md,
workers/extractor.md, each case's `extract:`). No tools: only the order.

    input  {"worker": "extractor", "service_order": {...}, "cases": ["termination", ...]}
    output {"cases": {<case>: {<field>: <value>}}, "evidence": {<case>: {<field>: "<words>"}}}
"""

from __future__ import annotations

from typing import Any

from agents.workers import run_worker_skill
from json_utils import JSONParseError

_JSON_INSTRUCTION = (
    "Your final answer must be a single JSON object: "
    '{"cases": {"<case>": {"<field>": <value or null>}}, '
    '"evidence": {"<case>": {"<field>": "<the words in the order it came from>"}}}. '
    "Return ONLY JSON — no preamble, no markdown fences."
)


async def extract(i: dict[str, Any]) -> dict[str, Any]:
    parsed = await run_worker_skill("validation", {"worker": "extractor", **i}, _JSON_INSTRUCTION, key="cases")
    if not isinstance(parsed, dict) or not isinstance(parsed.get("cases"), dict):
        raise JSONParseError("validation extractor: answer must be {'cases': {...}}")
    return {"cases": parsed["cases"], "evidence": parsed.get("evidence") or {}}
