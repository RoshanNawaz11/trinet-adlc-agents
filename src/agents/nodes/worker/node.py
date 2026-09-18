"""Worker node — classify skill. Same shape as FAWM skill_pipeline job branch:

ensure_bundle_published → run_skill → parse → normalize.

If classify `content` is empty, the last successful expert StepResult is
used as context (same idea as injecting entity_graph into the job skill).
"""

from __future__ import annotations

from typing import Any

from agents.graph.states import Step
from agents.model.gateway import ModelGateway, get_default_gateway
from agents.skills.client import run_skill
from agents.skills.io import (
    SkillOutputError,
    bounce_upstream_reason,
    bounced_classify,
    normalize_classify,
    parse_json,
)
from agents.skills.loader import content_as_text, format_for_skill
from agents.skills.registry import ensure_bundle_published
from json_utils import JSONParseError

_BUNDLE = "classify"
_JSON_INSTRUCTION = (
    "Your final answer must be a single JSON object that matches the output "
    "format in SKILL.md (label, confidence, fallback_used). Assign exactly one "
    "label from label_set. Return ONLY JSON — no preamble, no markdown fences."
)


def _step(state: dict[str, Any]) -> Step:
    step = state.get("step")
    if not isinstance(step, dict):
        raise ValueError("worker_node expects a Send() payload with 'step'")
    if step.get("skill") != _BUNDLE:
        raise ValueError(f"worker_node only runs {_BUNDLE!r} steps, got {step.get('skill')!r}")
    return step


def _config(gateway: ModelGateway) -> tuple[str, int]:
    cfg = gateway.policy.get("worker", gateway.policy["default"])
    return str(cfg["model"]), int(cfg.get("max_tokens", 1024))


def _error_result(step: Step, message: str) -> dict[str, Any]:
    return {
        "step_id": step["step_id"],
        "agent": "worker",
        "output": {},
        "error": message,
    }


def _with_expert_context(state: dict[str, Any], step: Step) -> Step:
    payload = dict(step.get("input") or {})
    if content_as_text(payload.get("content")).strip():
        return step
    for result in reversed(state.get("step_results") or []):
        if result.get("agent") != "expert":
            continue
        if result.get("escalation") or result.get("error"):
            continue
        output = result.get("output")
        if isinstance(output, dict):
            payload["content"] = output
            return {**step, "input": payload}
    return step


async def worker_node(state: dict[str, Any], gateway: ModelGateway | None = None) -> dict:
    step = _with_expert_context(state, _step(state))
    gateway = gateway or get_default_gateway()
    content = (step.get("input") or {}).get("content")
    bounced = bounce_upstream_reason(content)
    if bounced:
        return {"step_results": [bounced_classify(step, bounced)]}
    if not content_as_text(content).strip():
        return {"step_results": [bounced_classify(step, "malformed_input")]}

    try:
        skill_id, version_id = await ensure_bundle_published(_BUNDLE, gateway=gateway)
        model, max_tokens = _config(gateway)
        executed = await run_skill(
            skill_id,
            version_id,
            format_for_skill(step),
            model=model,
            max_tokens=max_tokens,
            additional_instructions=_JSON_INSTRUCTION,
            gateway=gateway,
        )
        raw = (executed or {}).get("raw_response") or ""
        if not raw:
            return {"step_results": [_error_result(step, "classify skill returned no text")]}
        parsed = parse_json(raw)
        result = normalize_classify(parsed, step)
        return {"step_results": [result]}
    except (SkillOutputError, JSONParseError) as exc:
        return {"step_results": [_error_result(step, str(exc))]}
    except Exception as exc:
        return {"step_results": [_error_result(step, str(exc))]}
