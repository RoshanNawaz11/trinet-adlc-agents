import json

from agents.nodes.orchestrator.node import orchestrator_node
from agents.nodes.planner.node import format_mcp_source, inject_mcp_source
from agents.runtime.samples import sample_query


PRIYA_LOOKUP = {
    "tool": "get_employee",
    "input": {"name": "Priya Sharma"},
    "result": json.dumps(
        {
            "name": "Priya Sharma",
            "department": "Finance",
            "job_title": "Payroll Analyst",
            "location": "Bengaluru",
            "employment_status": "active",
        }
    ),
}


async def test_priya_query_flags_when_employee_lookup_returns_payroll_role(monkeypatch):
    async def fake_complete(node, system, user, gateway):
        assert node == "orchestrator"
        assert "Priya Sharma" in user
        return (
            '{"flagged": true, "reason": "Payslip request for a Finance payroll employee."}',
            [PRIYA_LOOKUP],
        )

    monkeypatch.setattr(
        "agents.nodes.orchestrator.node.complete_with_mcp_tools", fake_complete
    )

    out = await orchestrator_node({"query": sample_query("priya")}, gateway=object())
    assert out["flagged"] is True
    assert out["status"] == "needs_review"
    assert out["mcp_results"][0]["tool"] == "get_employee"
    assert out["mcp_results"][0]["input"]["name"] == "Priya Sharma"


async def test_orchestrator_accepts_array_wrapped_object(monkeypatch):
    async def fake_complete(node, system, user, gateway):
        return '[{"flagged": false, "reason": "Routine self-service request."}]', []

    monkeypatch.setattr(
        "agents.nodes.orchestrator.node.complete_with_mcp_tools", fake_complete
    )

    out = await orchestrator_node({"query": sample_query("priya")}, gateway=object())
    assert out["flagged"] is False
    assert out["status"] == "running"


async def test_orchestrator_reads_stringified_false(monkeypatch):
    async def fake_complete(node, system, user, gateway):
        return '{"flagged": "false", "reason": "Routine self-service request."}', []

    monkeypatch.setattr(
        "agents.nodes.orchestrator.node.complete_with_mcp_tools", fake_complete
    )

    out = await orchestrator_node({"query": sample_query("priya")}, gateway=object())
    assert out["flagged"] is False


async def test_orchestrator_flags_when_decision_is_missing(monkeypatch):
    async def fake_complete(node, system, user, gateway):
        return '{"reason": "Could not reach the employee lookup tool."}', []

    monkeypatch.setattr(
        "agents.nodes.orchestrator.node.complete_with_mcp_tools", fake_complete
    )

    out = await orchestrator_node({"query": sample_query("priya")}, gateway=object())
    assert out["flagged"] is True
    assert out["status"] == "needs_review"


def test_planner_injects_priya_lookup_into_summarize_source():
    plan = [
        {
            "step_id": "summarize_request",
            "skill": "summarize",
            "input": {"source_text": sample_query("priya")},
            "status": "pending",
            "attempt": 0,
        },
        {
            "step_id": "classify_priority",
            "skill": "classify",
            "input": {"content": "", "label_set": ["critical", "high", "medium", "low"]},
            "status": "pending",
            "attempt": 0,
        },
    ]
    injected = inject_mcp_source(plan, [PRIYA_LOOKUP])
    source = injected[0]["input"]["source_text"]
    assert source == format_mcp_source([PRIYA_LOOKUP])
    assert "Priya Sharma" in source
    assert "Payroll Analyst" in source
    assert injected[1]["input"]["content"] == ""
