"""The two pauses for a person.

Flag review: as soon as an agent raises a flag, the run waits for the
analyst's answer to each one. The answers are saved on the flags, and the
agents that raised them run again with them before anything else continues.

Review at the end: one decision on the whole run, after every agent,
execution included, has finished. The reviewer sees each agent's result and
every flag, and approves or rejects the run.
"""

from __future__ import annotations

from langgraph.types import interrupt

from agents.graph.states import Flag, Review, State, flag_agent, step_record, waiting_flags


def open_flags(state: State) -> list[Flag]:
    """The flags still standing — merged duplicates are left out."""
    return [f for f in state.get("flags", []) if not f["resolved"]]


def flag_answer(flag: Flag, reply: dict | None) -> str | None:
    """Accept takes the flag's suggested fix (its recommendation); decline takes
    what the analyst typed. None when there is nothing to use: no reply, an
    accept on a flag with no suggested fix, or a decline left empty."""
    if not reply:
        return None
    if reply.get("action") == "accept":
        return flag.get("recommendation") or None
    if reply.get("action") == "decline":
        return str(reply.get("answer") or "").strip() or None
    return None


def missing_answers(values: dict, reply: dict | None) -> list[str]:
    """The waiting flags the analyst's reply leaves without an answer."""
    given = {a.get("flag_id"): a for a in (reply or {}).get("answers") or [] if isinstance(a, dict)}
    return [f["flag_id"] for f in waiting_flags(values.get("flags") or []) if flag_answer(f, given.get(f["flag_id"])) is None]


def flag_review_node(state: State) -> dict:
    """Resumed with {"answers": [{"flag_id", "action": "accept" | "decline",
    "answer": <typed text, on decline>}]}, one per flag — the server refuses a
    reply that leaves any flag without an answer. Should one get through anyway,
    that flag stays waiting, so the case pauses again with just those flags."""
    waiting = waiting_flags(state.get("flags") or [])
    reply = interrupt({
        "service_order_id": state.get("service_order_id"),
        "summary": state.get("summary"),
        "flags": waiting,
    })
    given = {a["flag_id"]: a for a in (reply or {}).get("answers") or [] if isinstance(a, dict) and "flag_id" in a}

    answered: list[Flag] = []
    for f in waiting:
        if (answer := flag_answer(f, given.get(f["flag_id"]))) is not None:
            decision = {"action": given[f["flag_id"]]["action"], "answer": answer}
            answered.append({**f, "answer": answer, "decisions": [*f["decisions"], decision]})

    # each agent that raised an answered flag runs again with the answers, like after a re-plan
    results = state.get("results") or {}
    agents: dict[str, list[str]] = {}
    for f in answered:
        agents.setdefault(flag_agent(f), []).append(f["flag_id"])
    return {
        "flags": answered,
        "results": {a: {**(results.get(a) or {}), "rerun": True, "answered": ids} for a, ids in agents.items()},
        "runs": {a: 0 for a in agents},
        "steps": [step_record(
            "planning", "Reviewer", f"Answered {len(answered)} of {len(waiting)} flags", "Console",
            result="answered" if len(answered) == len(waiting) else "waiting",
            evidence={"answers": {f["flag_id"]: f["answer"] for f in answered}},
            feed="handoff",
        )],
    }


def review_node(state: State) -> dict:
    results = state.get("results") or {}
    flags = open_flags(state)
    decision: Review = interrupt({
        "service_order_id": state.get("service_order_id"),
        "summary": state.get("summary"),
        "results": {a: r for a, r in results.items() if a != "planner"},
        "flags": flags,
    })

    action = decision["action"]
    review: Review = {"action": action, "flags_seen": [f["flag_id"] for f in flags]}
    if decision.get("reason"):
        review["reason"] = decision["reason"]
    return {
        "review": review,
        "steps": [step_record(
            "planning", "Reviewer", f"Run {'approved' if action == 'approve' else 'rejected'} by reviewer",
            "Console", result=action, evidence={"reason": review["reason"]} if "reason" in review else {},
        )],
    }
