from json_utils import extract_json

from agents.graph.edges import END
from agents.nodes.orchestrator.guardrails import violations
from agents.nodes.planner.node import _check


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
    })

    assert plan == []
    assert priority == "low"
    assert "records" in reason


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
