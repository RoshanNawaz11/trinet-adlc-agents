"""Worker node — classify skill. Same shape as FAWM skill_pipeline job branch:

ensure_bundle_published → run_skill → parse → normalize.

If classify `content` is empty, the last successful expert StepResult is
used as context (same idea as injecting entity_graph into the job skill).
"""

from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)

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
    raw_content = payload.get("content")
    if content_as_text(raw_content).strip():
        logger.info(
            "[%s] _with_expert_context: content already present (%r) — not substituting",
            step["step_id"], content_as_text(raw_content)[:80],
        )
        return step
    for result in reversed(state.get("step_results") or []):
        if result.get("agent") != "expert":
            continue
        if result.get("escalation") or result.get("error"):
            continue
        output = result.get("output")
        if isinstance(output, dict):
            payload["content"] = output
            logger.info(
                "[%s] _with_expert_context: substituted expert output from step %r",
                step["step_id"], result.get("step_id"),
            )
            return {**step, "input": payload}
    logger.warning(
        "[%s] _with_expert_context: content empty and no usable expert result found",
        step["step_id"],
    )
    return step


async def worker_node(state: dict[str, Any], gateway: ModelGateway | None = None) -> dict:
    step = _with_expert_context(state, _step(state))
    step_id = step["step_id"]
    logger.info("[%s] worker_node starting", step_id)
    gateway = gateway or get_default_gateway()
    content = (step.get("input") or {}).get("content")
    bounced = bounce_upstream_reason(content)
    if bounced:
        logger.warning("[%s] worker_node: bounced upstream (%s)", step_id, bounced)
        return {"step_results": [bounced_classify(step, bounced)]}
    if not content_as_text(content).strip():
        logger.warning("[%s] worker_node: content empty — bouncing", step_id)
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
            logger.error("[%s] worker_node: classify skill returned no text", step_id)
            return {"step_results": [_error_result(step, "classify skill returned no text")]}
        parsed = parse_json(raw)
        result = normalize_classify(parsed, step)
        logger.info(
            "[%s] worker_node done: label=%s confidence=%s fallback_used=%s",
            step_id, result.get("output", {}).get("label"),
            result.get("confidence"), result.get("output", {}).get("fallback_used"),
        )
        return {"step_results": [result]}
    except (SkillOutputError, JSONParseError) as exc:
        logger.error("[%s] worker_node: skill output error: %s", step_id, exc)
        return {"step_results": [_error_result(step, str(exc))]}
    except Exception as exc:
        logger.exception("[%s] worker_node: unexpected error", step_id)
        return {"step_results": [_error_result(step, str(exc))]}
