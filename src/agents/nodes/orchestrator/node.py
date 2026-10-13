"""Orchestrator — the hub. Control comes here at the start and after the
planner, every agent, every fetch and every review. Its rules live in
skills/orchestrator/skill.md: the model picks every route. Code only rejects
a route that breaks a routing rule (route_rules.broken_rules) and asks once more.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langgraph.graph import END

from agents.graph.edges import AGENTS, OUTPUT_VALIDATOR
from agents.nodes.orchestrator.route_rules import broken_rules
from agents.nodes.planner.node import MAX_PLANS
from agents.graph.interrupts import open_flags
from agents.graph.states import Flag, State, is_finished, merge_flags, merge_needs, step_record
from agents.model.gateway import ModelGateway, get_default_gateway
from agents.nodes.stage_agent import MAX_RUNS
from agents.skills.client import MAX_TOKENS, run_skill
from agents.skills.registry import ensure_bundle_published
from json_utils import JSONParseError, extract_json

logger = logging.getLogger(__name__)

_BUNDLE = "orchestrator"
_JSON_INSTRUCTION = (
    "Your final answer must be a single JSON object: "
    '{"route": ["<node>", ...], '
    '"merge": [{"keep": "<flag_id>", "drop": ["<flag_id>", ...]}], '
    '"fail_needs": ["<need id>", ...], '
    '"reason": "<one sentence: why this route>", '
    '"summary": "<2-3 sentences for the reviewer: what was found, what was flagged>"}. '
    "Return ONLY JSON — no preamble, no markdown fences."
)
_RAISED = {"low": "medium", "medium": "high", "high": "high"}
# a route that breaks a routing rule is sent back with the reason this many times in all
_ATTEMPTS = 3


class OrchestratorError(ValueError):
    pass


def _brief(state: State, rejected: list[dict[str, Any]]) -> str:
    """What the model sees: the whole run, as the agents left it — with who is
    waiting on whom read off `needs`, so the model doesn't have to."""
    results = state.get("results") or {}
    runs = state.get("runs") or {}
    planned = {s["agent"] for s in state.get("plan") or []}
    open_needs = [n for n in state.get("needs") or [] if n["status"] == "open"]
    brief: dict[str, Any] = {
        "service_order": state.get("service_order") or state.get("query"),
        "planner": results.get("planner"),
        "agents": {
            a: {
                "planned": a in planned,
                "runs": runs.get(a, 0),
                "max_runs": MAX_RUNS,
                # a result a re-plan marked `rerun` means it runs again
                "finished": is_finished(results, a),
                # its own requests still open — while any are, it is waiting and can't run
                "waiting_on": [n["id"] for n in open_needs if n["from_agent"] == a],
                # requests other agents sent it, still open — it answers them when it runs
                "asked": [n["id"] for n in open_needs if n["ask"] == a],
                "result": results.get(a),
            }
            for a in AGENTS if a != "execution"
        },
        # open requests to execution — `fetch` answers these
        "open_requests_to_execution": [n["id"] for n in open_needs if n["ask"] == "execution"],
        # true once execution has built the package — the last step before review
        "execution_finished": is_finished(results, "execution"),
        # the output validator's check of execution's package — null until it has checked this one
        "output_validator": results[OUTPUT_VALIDATOR] if is_finished(results, OUTPUT_VALIDATOR) else None,
        # true while the planner can still plan again after the validator finds issues
        "replan_left": runs.get("planner", 0) < MAX_PLANS,
        # who asked whom for what, and how it went — not the answers: routing needs only the status
        "needs": [{k: v for k, v in n.items() if k != "answer"} for n in state.get("needs") or []],
        "flags": state.get("flags") or [],
        "review": state.get("review"),
    }
    if rejected:
        brief["your_rejected_answers"] = rejected
    return json.dumps(brief, indent=2, default=str, ensure_ascii=False)


async def _decide(state: State, gateway: ModelGateway, rejected: list[dict[str, Any]]) -> dict[str, Any]:
    skill_id, version_id = await ensure_bundle_published(_BUNDLE, gateway=gateway)
    config = gateway.policy.get(_BUNDLE, gateway.policy["default"])
    executed = await run_skill(
        skill_id, version_id, _brief(state, rejected),
        model=config["model"], additional_instructions=_JSON_INSTRUCTION, gateway=gateway,
        max_tokens=config.get("max_tokens", MAX_TOKENS),
    )
    parsed = extract_json(executed["raw_response"], key="route")
    if not isinstance(parsed, dict):
        raise JSONParseError("orchestrator: answer must be a JSON object")
    return parsed


def _changes(state: State, decision: dict[str, Any]) -> tuple[list[Flag], list]:
    """The flags and needs the decision changes: merged flags, needs given up on."""
    flags: list[Flag] = []
    unresolved = {f["flag_id"]: f for f in state.get("flags") or [] if not f["resolved"]}
    # a flag kept by one group is never dropped by another, and a dropped flag
    # can't keep others — otherwise A→B plus B→A would hide both from the reviewer
    kept: set[str] = set()
    for group in decision.get("merge") or []:
        keep = group.get("keep") if isinstance(group, dict) else None
        if keep not in unresolved or keep in {f["flag_id"] for f in flags}:
            continue
        kept.add(keep)
        for fid in group.get("drop") or []:
            if fid in unresolved and fid not in kept and fid not in {f["flag_id"] for f in flags}:
                f = unresolved[fid]
                flags.append({**f, "resolved": True, "decisions": [*f["decisions"], {"action": "merged", "into": keep}]})

    open_needs = {n["id"]: n for n in state.get("needs") or [] if n["status"] == "open"}
    needs = [
        {**open_needs[i], "status": "failed", "answer": None, "error": "Orchestrator gave up on this request"}
        for i in decision.get("fail_needs") or [] if i in open_needs
    ]
    return flags, needs


async def orchestrator_node(state: State, gateway: ModelGateway | None = None) -> dict[str, Any]:
    gateway = gateway or get_default_gateway()
    rejected: list[dict[str, Any]] = []
    for _ in range(_ATTEMPTS):
        decision = await _decide(state, gateway, rejected)
        route = [str(n) for n in decision.get("route") or []] if isinstance(decision.get("route"), list) else []
        flags, needs = _changes(state, decision)
        # the state as it will be once the decision is applied — the route is checked against that
        after: State = {
            **state,
            "flags": merge_flags(state.get("flags") or [], flags),
            "needs": merge_needs(state.get("needs") or [], needs),
        }
        if not (errors := broken_rules(after, route)):
            break
        logger.warning("[orchestrator] route %s rejected: %s — asking again", route, errors)
        rejected.append({"route": route, "why_rejected": errors})
    else:
        raise OrchestratorError(f"orchestrator: {_ATTEMPTS} routes rejected, last {route}: {errors}")

    reason = str(decision.get("reason") or "").strip()
    logger.info("[orchestrator] route=%s flags=%s gave_up=%s — %s",
                route, [f["flag_id"] for f in flags], [n["id"] for n in needs], reason)

    update: dict[str, Any] = {
        "route": route,
        "steps": [step_record(
            "planning", "Orchestrator", f"Next: {', '.join(route)}", "Agents",
            result=reason, evidence={"flags": [f["flag_id"] for f in flags], "gave_up_on": [n["id"] for n in needs]},
        )],
    }
    if flags:
        update["flags"] = flags
    if needs:
        update["needs"] = needs
    if summary := str(decision.get("summary") or "").strip():
        update["summary"] = summary

    # fields the UI shows, after the decision
    results = after.get("results") or {}
    review = (after.get("review") or {}).get("action")
    update["flagged"] = bool(open_flags(after))
    update["status"] = (
        "rejected" if review == "reject"
        else "needs_review" if route == ["review"]
        else "done" if route == [END]
        else "running"
    )
    if base := results.get("planner", {}).get("priority"):
        # raised one level once any agent has flagged the order, and kept raised
        update["priority"] = _RAISED[base] if after.get("flags") else base
    scores = [results[a]["confidence"] for a in AGENTS if "confidence" in results.get(a, {})]
    if scores:
        update["confidence"] = round(min(scores) * 100)
    return update
