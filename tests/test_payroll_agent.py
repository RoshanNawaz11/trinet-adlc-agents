"""Payroll agent with worker agents: round 1 (earnings, leave, deductions), then
round 2 (reconcile) on their findings — all inside one run. The model and the
queue are faked, as in test_validation_agent."""

from __future__ import annotations

from test_validation_agent import FINAL, GATEWAY, Fake, _state, _tasks

from agents.nodes.payroll_calculation.node import payroll_calculation_node


def _task(worker: str) -> dict:
    return {"kind": f"payroll-calculation.{worker}", "input": {"case": "termination", "facts": {}}}


async def test_reconcile_runs_after_round_one_in_the_same_run(monkeypatch):
    round_one = _tasks(_task("earnings"), _task("leave"), _task("deductions"))
    round_two = _tasks(_task("reconcile"))
    fake = Fake(monkeypatch, [round_one, round_two, FINAL],
                worker_results=lambda t: {"status": "done", "result": {"worker": t["kind"]}})

    update = await payroll_calculation_node(_state(plan=[{"agent": "payroll-calculation", "task": "final pay"}]),
                                            gateway=GATEWAY)

    assert [[t["kind"].split(".")[1] for t in batch] for batch in fake.dispatched] == [
        ["earnings", "leave", "deductions"], ["reconcile"],
    ]
    # the agent saw round 1's results before it sent reconcile, and all four before finishing
    assert len(fake.inputs[1]["worker_results"]) == 3
    assert len(fake.inputs[2]["worker_results"]) == 4
    # reconcile got round 1's results from the code, without the agent copying them
    assert [r["result"]["worker"] for r in fake.dispatched[1][0]["input"]["worker_results"]] == [
        "payroll-calculation.earnings", "payroll-calculation.leave", "payroll-calculation.deductions",
    ]
    assert "payroll-calculation" in update["results"]
