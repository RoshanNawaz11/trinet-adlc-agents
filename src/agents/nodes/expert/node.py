"""Expert node — summarize skill. Same shape as FAWM skill_pipeline entity branch:

ensure_bundle_published → run_skill → parse → normalize.
"""

from __future__ import annotations

from typing import Any

from agents.graph.states import Step
from agents.model.gateway import ModelGateway, get_default_gateway
from agents.skills.client import run_skill
from agents.skills.io import SkillOutputError, empty_summarize, normalize_summarize, parse_json
from agents.skills.loader import format_for_skill
from agents.skills.registry import ensure_bundle_published
from json_utils import JSONParseError


_BUNDLE = "summarize"
_JSON_INSTRUCTION = (
    "Your final answer must be a single JSON object that matches the output "
    "format in SKILL.md (summary, key_points, confidence, confidence_breakdown, "
    "escalation). Return ONLY JSON — no preamble, no markdown fences."
)


def _step(state: dict[str, Any]) -> Step:
    step = state.get("step")
    if not isinstance(step, dict):
        raise ValueError("expert_node expects a Send() payload with 'step'")
    if step.get("skill") != _BUNDLE:
        raise ValueError(f"expert_node only runs {_BUNDLE!r} steps, got {step.get('skill')!r}")
    return step


def _config(gateway: ModelGateway) -> tuple[str, int]:
    cfg = gateway.policy.get("expert", gateway.policy["default"])
    return str(cfg["model"]), int(cfg.get("max_tokens", 1024))


def _error_result(step: Step, message: str) -> dict[str, Any]:
    return {
        "step_id": step["step_id"],
        "agent": "expert",
        "output": {},
        "error": message,
    }


async def expert_node(state: dict[str, Any], gateway: ModelGateway | None = None) -> dict:
    step = _step(state)
    gateway = gateway or get_default_gateway()
    source_text = (step.get("input") or {}).get("source_text")
    if not isinstance(source_text, str) or not source_text.strip():
        return {
            "step_results": [
                empty_summarize(
                    step,
                    reason="malformed_input",
                    detail="source_text is missing or empty",
                )
            ]
        }

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
            return {"step_results": [_error_result(step, "summarize skill returned no text")]}
        parsed = parse_json(raw)
        result = normalize_summarize(parsed, step)
        return {"step_results": [result]}
    except (SkillOutputError, JSONParseError) as exc:
        return {"step_results": [_error_result(step, str(exc))]}
    except Exception as exc:
        return {"step_results": [_error_result(step, str(exc))]}
