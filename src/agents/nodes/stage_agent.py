"""Shared runner for the stage agents (validation, compliance, payroll
calculation, execution).
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from agents.graph.states import Flag, Need, Stage, State, step_record
from agents.model.gateway import ModelGateway, get_default_gateway
from agents.queue.pool import HANDLERS
from agents.queue.subtasks import dispatch
from agents.skills.client import MAX_TOKENS, run_skill
from agents.skills.registry import ensure_bundle_published
from agents.tools.bindings import complete_with_mcp_tools
from json_utils import JSONParseError, extract_json

logger = logging.getLogger(__name__)

# the first run plus two re-runs after needs are answered
MAX_RUNS = 3
# rounds of worker tasks an agent can send within one run
MAX_WORKER_ROUNDS = 3

# who an agent can ask, and for what
PROVIDERS = {
    "validation": "the facts of the case — the employee it is about, their id, the key "
                  "dates, the reason, the work state, and other details in the order",
    "execution": "data from external systems — employee records, service orders, "
                 "rules, pay data, payroll calendars and cut-offs, benefits coverage, "
                 "leave and garnishment records",
    "compliance": "rules, deadlines and obligations that apply to the case — e.g. the "
                  "final-pay due date, the PTO payout rule, the I-9 deadline",
    "payroll-calculation": "pay answers — final pay amounts, deductions, net pay",
}

JSON_INSTRUCTION = (
    "Your final answer must be a single JSON object: "
    '{"steps": [{"title": "<what was checked and the outcome>", "source": "<system or tool used>", '
    '"result": "<short result>", "evidence": {<key facts>}}], '
    '"flags": [{"type": "<flag type from your skill>", "title": "<short title>", "detail": {<facts a reviewer needs>}, '
    '"recommendation": "<what Execution should do about it, if the reviewer approves — or null when the data must be fixed>"}], '
    '"output": {<your findings for the agents after you>}, '
    '"confidence": <0.0-1.0, how sure you are of your findings>}. '
    "Use an empty flags list when nothing needs a human. "
    "Return ONLY JSON — no preamble, no markdown fences."
)

_CAN_ASK = (
    "\n\n`data` holds what other agents already fetched and `my_needs` what you "
    "asked for before. If you need something you don't have, "
    "ask for it instead of guessing — return ONLY "
    '{"needs": [{"ask": "<an agent from who_provides>", "request": "<what you need, plain text>", '
    '"args": {<facts that help answer it>}}]} and nothing else; you will run again with the answers. '
    "Never ask again for a need that failed — treat it as not available."
)
_CANNOT_ASK = (
    "\n\nYou can't ask for anything more. Finish with what you have: use null or "
    "unknown for what is missing and raise a missingData flag naming it."
)
_DELEGATE = (
    "\n\nYou have worker agents: {kinds}. Your skill says what each does and when to "
    "send it — follow it: never do a worker's job yourself. To send work, return ONLY "
    '{{"worker_tasks": [{{"kind": "<one of your workers>", "input": {{<what your skill says to give it>}}}}]}} '
    "and nothing else; you will run again with their results in `worker_results`. Your "
    "final answer comes only after the workers your skill calls for have run."
)
_ANSWER = (
    "\n\nOther agents asked you for something (`requests_for_you`). Also include "
    '"answers": [{"id": "<request id>", "status": "done" | "failed", '
    '"answer": {<the answer>} or null, "error": "<why it failed>" or null}] '
    "in your final JSON."
)


_RERUN = (
    "\n\nYou ran before, and the output was found wrong: your previous answer is "
    "`previous_results.{bundle}` (marked `rerun`), your workers' results are still in "
    "`worker_results`, and `task` says what was wrong. Fix only that — send only the "
    "workers needed to fix it, keep the rest of your previous answer — then give your "
    "full final answer."
)


class AgentOutputError(ValueError):
    pass


def _fetched(state: State) -> list[dict]:
    """What other agents already fetched or answered, shared by everyone."""
    return [{"request": n["request"], "answer": n["answer"]} for n in state.get("needs") or [] if n["status"] == "done"]


def _input(state: State, bundle: str, can_ask: bool, requests: list[Need], worker_results: list[dict]) -> str:
    needs = state.get("needs") or []
    data: dict[str, Any] = {
        # the models don't know the date; deadlines and cut-offs are compared with it
        "today": date.today().isoformat(),
        # this agent's step in the planner's plan
        "task": next((s["task"] for s in state.get("plan") or [] if s["agent"] == bundle), ""),
        "work": (state.get("results") or {}).get("planner", {}).get("work") or [],
        "service_order": state.get("service_order") or state.get("query"),
        "data": _fetched(state),
        "my_needs": [
            {"request": n["request"], "status": n["status"], "error": n["error"]}
            for n in needs if n["from_agent"] == bundle
        ],
        "previous_results": state.get("results") or {},
        "flags": state.get("flags") or [],
    }
    if requests:
        data["requests_for_you"] = [
            {"id": n["id"], "from": n["from_agent"], "request": n["request"], "args": n["args"]}
            for n in requests
        ]
    if worker_results:
        data["worker_results"] = worker_results
    if can_ask:
        data["who_provides"] = {k: v for k, v in PROVIDERS.items() if k != bundle}
    return json.dumps(data, indent=2, default=str, ensure_ascii=False)


def _extract(raw: str) -> Any:
    for key in ("output", "needs", "worker_tasks"):
        try:
            return extract_json(raw, key=key)
        except JSONParseError:
            pass
    raise JSONParseError(f"No final answer, needs or worker_tasks in model output: {raw!r}")


def _worker_tasks(parsed: Any, bundle: str) -> list[dict]:
    """The agent's worker tasks; an agent can only send tasks to its own workers."""
    tasks = parsed.get("worker_tasks") if isinstance(parsed, dict) else None
    if not isinstance(tasks, list):
        return []
    if not all(isinstance(t, dict) and str(t.get("kind", "")).startswith(f"{bundle}.") for t in tasks):
        raise AgentOutputError(f"{bundle}: worker tasks must be for its own workers ({bundle}.*): {tasks!r}")
    return [{"kind": t["kind"], "input": t.get("input") if isinstance(t.get("input"), dict) else {}} for t in tasks]


def _parse(parsed: Any, bundle: str) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        raise AgentOutputError(f"{bundle}: answer must be a JSON object")
    steps, flags, output = parsed.get("steps"), parsed.get("flags", []), parsed.get("output")
    if not isinstance(steps, list) or not all(isinstance(s, dict) and s.get("title") for s in steps):
        raise AgentOutputError(f"{bundle}: 'steps' must be a list of objects with a title")
    if not isinstance(flags, list) or not all(isinstance(f, dict) and f.get("type") for f in flags):
        raise AgentOutputError(f"{bundle}: 'flags' must be a list of objects with a type")
    if not isinstance(output, dict):
        raise AgentOutputError(f"{bundle}: 'output' must be an object")
    confidence = parsed.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, int | float) or not 0 <= confidence <= 1:
        raise AgentOutputError(f"{bundle}: 'confidence' must be a number from 0 to 1, got {confidence!r}")
    return parsed


def _new_needs(asked: Any, bundle: str, run: int) -> list[Need]:
    """The agent's requests as Need records; ids are unique per agent and run,
    so agents running in parallel never collide."""
    needs: list[Need] = []
    for i, n in enumerate(asked if isinstance(asked, list) else [], start=1):
        if not isinstance(n, dict) or n.get("ask") not in PROVIDERS or n.get("ask") == bundle or not n.get("request"):
            logger.warning("[%s] dropped an unroutable need: %r", bundle, n)
            continue
        needs.append({
            "id": f"{bundle}-{run}-{i}",
            "from_agent": bundle,
            "ask": n["ask"],
            "request": str(n["request"]),
            "args": n.get("args") if isinstance(n.get("args"), dict) else {},
            "for_need": None,
            "status": "open",
            "answer": None,
            "error": None,
        })
    return needs


def _answered(requests: list[Need], answers: Any) -> list[Need]:
    by_id = {a["id"]: a for a in answers if isinstance(a, dict) and "id" in a} if isinstance(answers, list) else {}
    updated: list[Need] = []
    for need in requests:
        a = by_id.get(need["id"])
        if a and a.get("status") == "done":
            updated.append({**need, "status": "done", "answer": a.get("answer"), "error": None})
        else:
            error = (a or {}).get("error") or "No answer given"
            updated.append({**need, "status": "failed", "answer": None, "error": str(error)})
    return updated


async def run_stage_agent(
    bundle: str,
    stage: Stage,
    agent: str,
    state: State,
    *,
    gateway: ModelGateway | None = None,
    json_instruction: str = JSON_INSTRUCTION,
    with_tools: bool = False,
    asks: bool = True,
) -> dict[str, Any]:
    """Run one stage agent. Returns either its needs (it is waiting) or its
    result: results, steps, flags — plus answers to what others asked it."""
    gateway = gateway or get_default_gateway()
    run = (state.get("runs") or {}).get(bundle, 0) + 1
    can_ask = asks and not with_tools and run < MAX_RUNS
    requests = [n for n in state.get("needs") or [] if n["ask"] == bundle and n["status"] == "open"]
    logger.info("[%s] run %d (can_ask=%s, requests=%d)", bundle, run, can_ask, len(requests))

    instruction = json_instruction
    instruction += _CAN_ASK if can_ask else _CANNOT_ASK
    # the agents with workers are the ones the worker pool has handlers for
    kinds = sorted(k for k in HANDLERS if k.startswith(f"{bundle}."))
    if kinds:
        instruction += _DELEGATE.format(kinds=", ".join(kinds))
    if requests:
        instruction += _ANSWER
    # re-planned with a task saying what to fix (the validator just checks the new package)
    replanned = any(s["agent"] == bundle for s in state.get("plan") or [])
    if replanned and ((state.get("results") or {}).get(bundle) or {}).get("rerun"):
        instruction += _RERUN.format(bundle=bundle)
    # kept across runs, so a re-run after needs are answered still has them
    worker_results = list((state.get("worker_results") or {}).get(bundle, []))
    worker_steps = []

    skill = await ensure_bundle_published(bundle, gateway=gateway)
    config = gateway.policy.get(bundle, gateway.policy["default"])
    mcp_calls: list[dict] = []
    for round_ in range(MAX_WORKER_ROUNDS + 1):
        user = _input(state, bundle, can_ask, requests, worker_results)
        if with_tools:
            raw, calls = await complete_with_mcp_tools(
                bundle, instruction, user, gateway, skill,
                # write tools only once the reviewer has approved the run
                read_only=(state.get("review") or {}).get("action") != "approve",
            )
            mcp_calls += calls
        else:
            raw = (await run_skill(
                *skill, 
                user, 
                model=config["model"], 
                additional_instructions=instruction, 
                gateway=gateway,
                max_tokens=config.get("max_tokens", MAX_TOKENS),
            ))["raw_response"]
        parsed = _extract(raw)
        tasks = _worker_tasks(parsed, bundle)
        if not tasks:
            break
        if round_ == MAX_WORKER_ROUNDS:
            raise AgentOutputError(f"{bundle}: still sending worker tasks after {MAX_WORKER_ROUNDS} rounds")
        # every worker gets what already exists — the order, the fetched records, the
        # earlier workers' results — so the agent never copies data into a task
        given = {
            "today": date.today().isoformat(),
            "service_order": state.get("service_order") or state.get("query"),
            "data": _fetched(state),
            "worker_results": list(worker_results),
        }
        results = await dispatch([{**t, "input": {**t["input"], **given}} for t in tasks])
        # the agent sees which worker ran for which case and what it returned
        worker_results += [{"kind": t["kind"], "case": t["input"].get("case"), **r} for t, r in zip(tasks, results)]
        worker_steps += [
            step_record(
                stage, agent, f"Worker {t['kind']}", "Workers",
                result=r["status"], evidence={"input": t["input"], "error": r.get("error")},
            )
            for t, r in zip(tasks, results)
        ]
    kept = {"worker_results": {bundle: worker_results}} if worker_results else {}

    if can_ask and isinstance(parsed, dict) and parsed.get("needs"):
        needs = _new_needs(parsed["needs"], bundle, run)
        if needs:
            logger.info("[%s] waiting on %s", bundle, [(n["ask"], n["request"]) for n in needs])
            return {
                "needs": needs,
                "runs": {bundle: run},
                "steps": worker_steps + [
                    step_record(stage, agent, f"Asked {n['ask']}: {n['request']}", "Agents", result="waiting")
                    for n in needs
                ],
                **kept,
            }

    parsed = _parse(parsed, bundle)

    # what agents did for the entire timeline (mcp calls and their own steps)
    steps = worker_steps + [
        step_record(
            stage, agent, f"Looked up {call['tool']}", f"MCP · {call['tool']}",
            result="error" if call.get("error") else "ok", evidence=call["input"], at=call["at"],
        )
        for call in mcp_calls
    ]
    steps += [
        step_record(
            stage, agent, str(s["title"]), str(s.get("source") or "Agents"),
            result=str(s.get("result") or ""), evidence=s.get("evidence") or {},
        )
        for s in parsed["steps"]
    ]

    # what the reviewer sees at the end of the run
    flags: list[Flag] = [
        {
            "flag_id": f"{bundle}-{i}",
            "type": str(f["type"]),
            "stage": stage,
            "title": str(f.get("title") or f["type"]),
            "detail": f.get("detail") or {},
            "recommendation": str(f["recommendation"]) if f.get("recommendation") else None,
            "resolved": False,
            "decisions": [],
        }
        for i, f in enumerate(parsed.get("flags", []), start=1)
    ]
    answered = _answered(requests, parsed.get("answers")) if requests else []
    logger.info(
        "[%s] done: steps=%d flags=%d answered=%d", bundle, len(steps), len(flags), len(answered),
    )
    return {
        "results": {bundle: {**parsed["output"], "confidence": parsed["confidence"]}},
        "steps": steps,
        "flags": flags,
        "needs": answered,
        "runs": {bundle: run},
        **kept,
    }
