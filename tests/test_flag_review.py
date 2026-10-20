"""Every flag keeps the case paused until the analyst answers it — accept the
suggested fix or decline and type the answer — and the agent that raised it
runs again with the answer before anything else continues."""

from agents.graph import interrupts
from agents.graph.edges import END, FLAG_REVIEW
from agents.graph.states import waiting_flags
from agents.nodes.orchestrator.route_rules import broken_rules as violations

PLAN = [{"agent": a, "task": ""} for a in ("validation", "payroll-calculation", "compliance", "execution")]


def _flag(flag_id: str, stage: str = "validation", recommendation: str | None = None, **extra) -> dict:
    return {"flag_id": flag_id, "type": "missingData", "stage": stage, "title": flag_id, "detail": {},
            "recommendation": recommendation, "resolved": False, "decisions": [], **extra}


def _state(flags: list[dict], results: dict | None = None) -> dict:
    return {"plan": PLAN, "results": {"planner": {}, **(results or {})}, "flags": flags, "needs": [], "runs": {}}


def test_a_waiting_flag_keeps_the_case_paused():
    state = _state([_flag("validation-1")], {"validation": {"confidence": 0.5}})

    assert violations(state, [FLAG_REVIEW]) == []
    for route in (["payroll-calculation", "compliance"], ["execution"], ["review"], [END]):
        assert violations(state, route)


def test_flag_review_only_runs_when_a_flag_waits():
    answered = _flag("validation-1", answer="2026-10-12")
    merged = _flag("validation-2", resolved=True)
    planner = _flag("planner-1", stage="planning")

    assert waiting_flags([answered, merged, planner]) == []
    assert violations(_state([answered, merged]), [FLAG_REVIEW])


def test_two_flags_wait_together_until_both_are_answered():
    one = _flag("validation-1")
    two = _flag("payroll-calculation-1", stage="payroll")
    results = {"validation": {}, "payroll-calculation": {}}

    assert [f["flag_id"] for f in waiting_flags([one, two])] == ["validation-1", "payroll-calculation-1"]
    # one answered, one not: still paused
    assert violations(_state([{**one, "answer": "x"}, two], results), ["validation"])
    assert violations(_state([{**one, "answer": "x"}, two], results), [FLAG_REVIEW]) == []


def test_the_agents_applying_answers_run_first():
    results = {"validation": {"rerun": True, "answered": ["validation-1"]}}
    state = _state([_flag("validation-1", answer="2026-10-12")], results)

    assert violations(state, ["validation"]) == []
    assert violations(state, ["validation", "compliance"])
    assert violations(state, ["compliance"])


def _review(monkeypatch, state: dict, reply: dict) -> dict:
    monkeypatch.setattr(interrupts, "interrupt", lambda _payload: reply)
    return interrupts.flag_review_node(state)


def test_accept_takes_the_suggested_fix_and_decline_the_typed_answer(monkeypatch):
    state = _state(
        [_flag("validation-1", recommendation="Use the record's date, 2026-10-12"),
         _flag("compliance-1", stage="compliance", recommendation="Pay off-cycle")],
        {"validation": {"confidence": 0.5}, "compliance": {"confidence": 0.7}},
    )
    update = _review(monkeypatch, state, {"answers": [
        {"flag_id": "validation-1", "action": "accept"},
        {"flag_id": "compliance-1", "action": "decline", "answer": "Pay on the regular payday"},
    ]})

    answers = {f["flag_id"]: f["answer"] for f in update["flags"]}
    assert answers == {"validation-1": "Use the record's date, 2026-10-12", "compliance-1": "Pay on the regular payday"}
    # each agent that raised one runs again with its answers
    assert update["results"]["validation"] == {"confidence": 0.5, "rerun": True, "answered": ["validation-1"]}
    assert update["results"]["compliance"]["answered"] == ["compliance-1"]
    assert update["runs"] == {"validation": 0, "compliance": 0}


def test_a_flag_without_a_usable_answer_stays_waiting(monkeypatch):
    no_fix = _flag("validation-1")                       # a data problem: nothing to accept
    typed = _flag("validation-2", recommendation="Use 40 hours")
    state = _state([no_fix, typed], {"validation": {}})

    update = _review(monkeypatch, state, {"answers": [
        {"flag_id": "validation-1", "action": "accept"},
        {"flag_id": "validation-2", "action": "decline", "answer": "   "},
    ]})

    assert update["flags"] == []
    assert update["results"] == {}
    assert len(waiting_flags(state["flags"])) == 2


def test_missing_answers_names_every_flag_left_without_one():
    values = {"flags": [_flag("validation-1"), _flag("payroll-calculation-1", stage="payroll", recommendation="Use $0")]}

    missing_answers = interrupts.missing_answers
    assert missing_answers(values, {"answers": [{"flag_id": "payroll-calculation-1", "action": "accept"}]}) == ["validation-1"]
    assert missing_answers(values, {"answers": [
        {"flag_id": "validation-1", "action": "decline", "answer": "EMP-7"},
        {"flag_id": "payroll-calculation-1", "action": "accept"},
    ]}) == []
