from json_utils import extract_json

from agents.graph.edges import END, route_from_orchestrator
from agents.nodes.orchestrator.node import orchestrator_node
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


def test_empty_plan_ends_the_run_as_needs_review():
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

    assert route_from_orchestrator(state) is END
    assert orchestrator_node(state)["status"] == "needs_review"


def test_a_real_plan_still_routes_to_its_first_agent():
    state = {
        "plan": [{"agent": "validation", "task": "Check the order"}],
        "results": {"planner": {"priority": "high"}},
        "flags": [],
    }

    assert route_from_orchestrator(state) == "validation"
