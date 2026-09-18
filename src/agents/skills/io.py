"""
Parse and normalize JSON skill output into StepResult-shaped dicts or any schema when reuired.
"""

from __future__ import annotations

import logging
from typing import Any

from agents.graph.states import Step
from json_utils import extract_json

logger = logging.getLogger(__name__)

_ESCALATION_REASONS = frozenset({"conflicting_claims", "low_coverage", "malformed_input"})
DEFAULT_LABELS = ("urgent", "escalate", "routine", "ignore", "needs_review")
SAFE_DEFAULTS = frozenset({"routine", "needs_review", "ignore"})
LOW_LABEL_CONFIDENCE = 0.6
LOW_EXPERT_CONFIDENCE = 0.5
DEFAULT_ACTION_MAP = {
    "urgent": "notify_on_call",
    "escalate": "create_ticket",
    "routine": "queue_for_batch",
    "ignore": None,
    "needs_review": None,
}
AGENT_BY_SKILL = {"summarize": "expert", "classify": "worker"}


class SkillOutputError(ValueError):
    pass


def _is_valid_confidence(value: Any) -> bool:
    """int/float in [0, 1], excluding bool — isinstance(True, int) is True
    in Python, so a naive isinstance(x, (int, float)) check silently lets
    `"confidence": true` through as 1.0. Both normalize_* functions use
    this instead of a bare isinstance check for that reason."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= float(value) <= 1


# ── JSON parsing ─────────────────────────────────────────────────────────


def parse_json(text: str) -> dict[str, Any]:
    parsed = extract_json(text)
    if not isinstance(parsed, dict):
        raise SkillOutputError(f"Skill output is not a JSON object (got {type(parsed).__name__})")
    return parsed


def result_dict(
    step: Step,
    output: dict[str, Any],
    *,
    confidence: float,
    escalation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "step_id": step["step_id"],
        "agent": AGENT_BY_SKILL[step["skill"]],
        "output": output,
        "confidence": confidence,
    }
    if escalation:
        result["escalation"] = escalation
    return result


# ── summarize (Expert) ──────────────────────────────────────────────────


def normalize_summarize(parsed: dict[str, Any], step: Step) -> dict[str, Any]:
    """Validates against expert-summarize-skill.md's output contract.
    Re-applies the SKILL.md's own rule ("confidence < 0.5 → escalate")
    independently of whether the model actually escalated itself."""
    step_id = step["step_id"]
    summary = parsed.get("summary")
    key_points = parsed.get("key_points")
    confidence = parsed.get("confidence")
    breakdown = parsed.get("confidence_breakdown")
    if not isinstance(summary, str):
        raise SkillOutputError("summarize.summary must be a string")
    if not isinstance(key_points, list) or not all(isinstance(p, str) for p in key_points):
        raise SkillOutputError("summarize.key_points must be an array of strings")
    if not _is_valid_confidence(confidence):
        raise SkillOutputError("summarize.confidence must be a number in [0, 1]")
    if not isinstance(breakdown, dict):
        raise SkillOutputError("summarize.confidence_breakdown must be an object")

    escalation = parsed.get("escalation")
    if escalation is not None:
        if not isinstance(escalation, dict):
            raise SkillOutputError("summarize.escalation must be an object or null")
        if escalation.get("reason") not in _ESCALATION_REASONS:
            raise SkillOutputError(
                f"summarize.escalation.reason must be one of {sorted(_ESCALATION_REASONS)}"
            )

    confidence_f = float(confidence)
    if confidence_f < LOW_EXPERT_CONFIDENCE and not escalation:
        logger.warning(
            "[%s] Expert confidence %.2f below threshold with no model-reported "
            "escalation — escalating anyway", step_id, confidence_f,
        )
        escalation = {
            "reason": "low_coverage",
            "detail": f"model confidence {confidence_f} is below {LOW_EXPERT_CONFIDENCE}",
        }

    output = {
        "task_id": step_id,
        "agent": "expert",
        "summary": summary,
        "key_points": key_points,
        "confidence": confidence_f,
        "confidence_breakdown": breakdown,
        "escalation": escalation,
    }
    return result_dict(step, output, confidence=confidence_f, escalation=escalation)


def empty_summarize(step: Step, *, reason: str, detail: str) -> dict[str, Any]:
    escalation = {"reason": reason, "detail": detail}
    output = {
        "task_id": step["step_id"],
        "agent": "expert",
        "summary": "",
        "key_points": [],
        "confidence": 0.0,
        "confidence_breakdown": {
            "coverage": 0.0,
            "compression_ratio": 0.0,
            "hallucination_flags": [],
        },
        "escalation": escalation,
    }
    return result_dict(step, output, confidence=0.0, escalation=escalation)


# ── classify (Worker) ───────────────────────────────────────────────────


def normalize_classify(parsed: dict[str, Any], step: Step) -> dict[str, Any]:
    """Validates against worker-classify-skill.md's output contract.
    Re-applies the SKILL.md's own rule ("confidence < 0.6 → fall back to
    a safe label") independently of the model's self-reported confidence.

    A safe-label fallback now ALSO sets `escalation` (see module-level
    note above the diff that introduced this) — worker-classify-skill.md
    says low-confidence classifications should route to Planner/Expert
    for review, not resolve silently just because a safe label existed
    to fall back to."""
    payload = step["input"]
    label_set = list(payload.get("label_set") or DEFAULT_LABELS)
    action_map = payload.get("action_map")
    step_id = step["step_id"]
    label = parsed.get("label")
    confidence = parsed.get("confidence")
    if label not in label_set:
        raise SkillOutputError(f"classify.label {label!r} is not in label_set {label_set}")
    if not _is_valid_confidence(confidence):
        raise SkillOutputError("classify.confidence must be a number in [0, 1]")

    confidence_f = float(confidence)
    fallback_used = False
    escalation: dict[str, Any] | None = None
    bounced = None

    if confidence_f < LOW_LABEL_CONFIDENCE:
        safe = next((item for item in label_set if item in SAFE_DEFAULTS), None)
        if safe is None:
            bounced = {"reason": "low_classify_confidence"}
            logger.warning(
                "[%s] Worker confidence %.2f below threshold, no safe label in "
                "label_set %s — bouncing to Planner", step_id, confidence_f, label_set,
            )
        else:
            logger.warning(
                "[%s] Worker confidence %.2f below threshold — falling back to "
                "safe label %r and escalating for review", step_id, confidence_f, safe,
            )
            label = safe
            fallback_used = True
            escalation = {
                "reason": "low_classify_confidence",
                "detail": f"model confidence {confidence_f} is below {LOW_LABEL_CONFIDENCE}; "
                          f"fell back to safe label {safe!r}",
            }

    mapping = DEFAULT_ACTION_MAP if not isinstance(action_map, dict) else {**DEFAULT_ACTION_MAP, **action_map}
    action = None if fallback_used or bounced else mapping.get(label)
    output = {
        "task_id": step_id,
        "agent": "worker",
        "label": label,
        "confidence": confidence_f,
        "fallback_used": fallback_used,
        "action": action,
        "mcp_action_taken": False,
        "mcp_result": None,
        "mcp_error": None,
        "bounced": bounced,
    }
    return result_dict(step, output, confidence=confidence_f, escalation=escalation or bounced)


def bounced_classify(step: Step, reason: str) -> dict[str, Any]:
    output = {
        "task_id": step["step_id"],
        "agent": "worker",
        "label": None,
        "confidence": 0.0,
        "fallback_used": False,
        "action": None,
        "mcp_action_taken": False,
        "mcp_result": None,
        "mcp_error": None,
        "bounced": {"reason": reason},
    }
    return result_dict(step, output, confidence=0.0, escalation=output["bounced"])


def bounce_upstream_reason(content: object) -> str | None:
    if not isinstance(content, dict):
        return None
    if content.get("escalation"):
        return "escalation_present"
    confidence = content.get("confidence")
    if isinstance(confidence, (int, float)) and not isinstance(confidence, bool) and float(confidence) < LOW_EXPERT_CONFIDENCE:
        return "low_expert_confidence"
    return None