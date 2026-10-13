from json_utils import extract_json

from agents.graph.edges import END
from agents.nodes.orchestrator.route_rules import broken_rules as violations
from agents.nodes.planner.node import PlannerOutputError, _check
import pytest


def test_a_quoted_empty_list_does_not_hide_the_real_plan():
    text = (
        'The skill says to return `"plan": []` when it is not a termination.\n'
        '```json\n'
        '{"priority": "low", "plan": [], "reason": "Records update."}\n'
        '```'
    )
    parsed = extract_json(text, key="plan")
    assert parsed["reason"] == "Records update."


def test_empty_plan_is_a_decision_not_an_error():
    plan, priority, reason = _check({
        "priority": "low",
        "plan": [],
        "reason": "Closed records update, not a termination.",
    }, replan=False)

    assert plan == []
    assert priority == "low"
    assert "records" in reason


def test_a_replan_must_run_something():
    with pytest.raises(PlannerOutputError):
        _check({"priority": "low", "plan": [], "reason": "Nothing to fix."}, replan=True)


# The orchestrator's model picks every route; these check the guardrails that
# accept or refuse it for the planner's two outcomes.
def test_an_empty_plan_can_only_end_the_run():
    state = {
        "plan": [],
        "results": {"planner": {"priority": "low", "reason": "Not a termination."}},
        "flags": [{
            "flag_id": "planner-1",
            "resolved": False,
            "type": "outOfScope",
            "stage": "planning",
            "title": "Not a termination case",
            "detail": {},
            "decisions": [],
        }],
    }

    assert violations(state, [END]) == []
    assert violations(state, ["review"])
    assert violations(state, ["validation"])


def test_a_real_plan_runs_its_agents_before_review():
    state = {
        "plan": [
            {"agent": "validation", "task": "Check the order"},
            {"agent": "execution", "task": "Build the package"},
        ],
        "results": {"planner": {"priority": "high"}},
        "flags": [],
    }

    assert violations(state, ["validation"]) == []
    assert violations(state, ["execution"])
    assert violations(state, ["review"])
    assert violations(state, [END])


def test_the_output_validator_sends_the_run_back_to_the_planner_once():
    plan = [{"agent": "execution", "task": "Build the package"}]
    built = {"planner": {}, "execution": {}}

    # execution's package is checked before review
    state = {"plan": plan, "results": built, "runs": {"planner": 1}}
    assert violations(state, ["review"])
    assert violations(state, ["output-validator"]) == []

    # issues found: the planner may plan again, once
    issues = {**built, "output-validator": {"valid": False}}
    assert violations({**state, "results": issues}, ["planner"]) == []
    assert violations({**state, "results": issues, "runs": {"planner": 2}}, ["planner"])
    assert violations({**state, "results": issues, "runs": {"planner": 2}}, ["review"]) == []

    # no issues: straight to review
    valid = {**built, "output-validator": {"valid": True}}
    assert violations({**state, "results": valid}, ["planner"])
    assert violations({**state, "results": valid}, ["review"]) == []


def test_the_planned_agents_can_start_together():
    plan = [{"agent": a, "task": ""} for a in ("validation", "payroll-calculation", "compliance", "execution")]
    state = {"plan": plan, "results": {"planner": {}}, "needs": []}

    assert violations(state, ["validation", "payroll-calculation", "compliance"]) == []
    assert violations(state, ["validation", "execution"])


def test_a_replanned_agent_runs_again_and_keeps_its_previous_result():
    plan = [
        {"agent": "payroll-calculation", "task": "net_pay is missing: run reconcile"},
        {"agent": "execution", "task": "Rebuild the package"},
    ]
    rerun = {
        "planner": {},
        "payroll-calculation": {"net_pay": None, "rerun": True},
        "execution": {"packages": {}, "rerun": True},
        "output-validator": {"valid": False, "rerun": True},
    }
    state = {"plan": plan, "results": rerun, "runs": {"planner": 2, "payroll-calculation": 0}}

    # the marked agents count as not finished, so they run again in order
    assert violations(state, ["payroll-calculation"]) == []
    assert violations(state, ["execution"])
    assert violations(state, ["review"])
    # the validator's old verdict doesn't allow another re-plan
    assert violations(state, ["planner"])
