"""Validation agent with worker agents — the model and the queue are faked, so
these run without an API key or Redis."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from agents.nodes import stage_agent
from agents.nodes.stage_agent import AgentOutputError
from agents.nodes.validation.node import validation_node
import agents.workers as validation_workers
from agents.workers.validation import validator

ORDER = {"id": "SO-1", "caseType": "Offboarding", "description": "Terminate Priya Rao (EMP-7) on 2026-10-31."}
FACTS = {"subject_name": "Priya Rao", "subject_employee_id": "EMP-7", "termination_date": "2026-10-31"}
RECORD = {"request": "Employee record for EMP-7", "answer": {"id": "EMP-7", "status": "Active"}}

FINAL = {
    "steps": [{"title": "employment_status passed", "source": "Validation worker", "result": "pass"}],
    "flags": [],
    "output": {"cases": {"termination": FACTS}, "complete": True, "missing_fields": [],
               "special_instructions": "none", "status": "ready"},
    "confidence": 0.9,
}


def _tasks(*tasks: dict) -> dict:
    return {"worker_tasks": list(tasks)}


def _check(worker: str) -> dict:
    return {"kind": f"validation.{worker}", "input": {"case": "termination"}}


class Fake:
    """Scripted model answers and a fake queue; records what each was given."""

    def __init__(self, monkeypatch, answers: list[dict], worker_results=None):
        self.answers = list(answers)
        self.inputs: list[dict] = []
        self.instructions: list[str] = []
        self.dispatched: list[list[dict]] = []
        self.worker_results = worker_results or (lambda task: {"status": "done", "result": {"ok": task["kind"]}})
        monkeypatch.setattr(stage_agent, "run_skill", self.run_skill)
        monkeypatch.setattr(stage_agent, "ensure_bundle_published", self.publish)
        monkeypatch.setattr(stage_agent, "dispatch", self.dispatch)

    async def publish(self, bundle, gateway=None):
        return ("skill-id", "version-id")

    async def run_skill(self, skill_id, version_id, user, **kwargs):
        self.inputs.append(json.loads(user))
        self.instructions.append(kwargs["additional_instructions"])
        return {"raw_response": json.dumps(self.answers.pop(0))}

    async def dispatch(self, tasks):
        self.dispatched.append(tasks)
        return [self.worker_results(t) for t in tasks]


def _state(**extra) -> dict:
    return {
        "run_id": "r1", "status": "running", "flagged": False, "service_order": ORDER,
        "plan": [{"agent": "validation", "task": "check the termination"}],
        "results": {"planner": {"work": ["termination"]}},
        "steps": [], "flags": [], "needs": [], "runs": {}, **extra,
    }


GATEWAY = SimpleNamespace(policy={"default": {"model": "test-model"}})


async def test_the_agent_is_told_it_can_send_its_workers(monkeypatch):
    # the skill alone isn't enough: the runner's instruction lists the answers the
    # model may give, and without worker_tasks in it the agent does the work itself
    fake = Fake(monkeypatch, [FINAL])

    await validation_node(_state(), gateway=GATEWAY)

    [instruction] = fake.instructions
    assert '"worker_tasks"' in instruction
    for kind in ("validation.extract", "validation.identity", "validation.validator"):
        assert kind in instruction
    assert "compliance." not in instruction


async def test_run_1_extracts_then_asks_execution_for_records(monkeypatch):
    fake = Fake(monkeypatch, [
        _tasks({"kind": "validation.extract", "input": {"cases": ["termination"]}}),
        {"needs": [{"ask": "execution", "request": "Employee record for EMP-7", "args": {"id": "EMP-7"}}]},
    ])

    update = await validation_node(_state(), gateway=GATEWAY)

    # the extractor got the order without the agent copying it
    [[task]] = fake.dispatched
    assert task["kind"] == "validation.extract"
    assert task["input"] == {"cases": ["termination"], "service_order": ORDER, "data": [], "worker_results": []}
    # the agent saw the extractor's result on its second call
    assert "worker_results" not in fake.inputs[0]
    assert fake.inputs[1]["worker_results"][0]["status"] == "done"
    # it waits on execution, and keeps the extraction for the next run
    assert [n["ask"] for n in update["needs"]] == ["execution"]
    # the agent sees which worker ran and what it returned — not the task's input
    assert update["worker_results"]["validation"] == [
        {"kind": "validation.extract", "case": None, "status": "done", "result": {"ok": "validation.extract"}},
    ]
    assert "results" not in update
    assert [s["result"] for s in update["steps"]] == ["done", "waiting"]


async def test_run_2_sends_both_checkers_and_finishes(monkeypatch):
    extracted = [{"kind": "validation.extract", "input": {"cases": ["termination"]},
                  "status": "done", "result": {"cases": {"termination": FACTS}}}]
    done_need = {"id": "validation-1-1", "from_agent": "validation", "ask": "execution", "request": RECORD["request"],
                 "args": {}, "for_need": None, "status": "done", "answer": RECORD["answer"], "error": None}
    fake = Fake(monkeypatch, [_tasks(_check("identity"), _check("validator")), FINAL])

    update = await validation_node(
        _state(needs=[done_need], runs={"validation": 1}, worker_results={"validation": extracted}),
        gateway=GATEWAY,
    )

    # the extraction from run 1 and execution's record are both in its input
    assert fake.inputs[0]["worker_results"] == extracted
    assert fake.inputs[0]["data"] == [{"request": RECORD["request"], "answer": RECORD["answer"]}]
    # both checkers ran together, in one round, each given the record and the
    # extraction by the code — the agent only named the case
    [batch] = fake.dispatched
    assert [t["kind"] for t in batch] == ["validation.identity", "validation.validator"]
    for t in batch:
        assert t["input"]["data"] == [{"request": RECORD["request"], "answer": RECORD["answer"]}]
        assert t["input"]["worker_results"] == extracted
    assert len(update["worker_results"]["validation"]) == 3
    assert update["results"]["validation"]["status"] == "ready"
    assert update["results"]["validation"]["confidence"] == 0.9
    assert [s["title"] for s in update["steps"]][-1] == "employment_status passed"


async def test_a_failed_worker_is_shown_to_the_agent(monkeypatch):
    fake = Fake(
        monkeypatch, [_tasks(_check("validator")), FINAL],
        worker_results=lambda t: {"status": "failed", "error": "TimeoutError: no result"},
    )

    update = await validation_node(_state(), gateway=GATEWAY)

    assert fake.inputs[1]["worker_results"] == [
        {"kind": "validation.validator", "case": "termination", "status": "failed", "error": "TimeoutError: no result"},
    ]
    assert update["steps"][0]["result"] == "failed"
    assert "results" in update


async def test_tasks_for_another_agents_workers_are_refused(monkeypatch):
    fake = Fake(monkeypatch, [_tasks({"kind": "payroll-calculation.calc", "input": {}})])

    with pytest.raises(AgentOutputError, match="its own workers"):
        await validation_node(_state(), gateway=GATEWAY)
    assert fake.dispatched == []


async def test_an_agent_that_keeps_sending_tasks_is_stopped(monkeypatch):
    Fake(monkeypatch, [_tasks(_check("validator"))] * (stage_agent.MAX_WORKER_ROUNDS + 1))

    with pytest.raises(AgentOutputError, match="worker tasks"):
        await validation_node(_state(), gateway=GATEWAY)


async def test_a_checker_worker_runs_its_part_of_the_skill(monkeypatch):
    seen = {}

    async def fake_skill(bundle, i, instruction, key):
        seen.update(i, bundle=bundle)
        return {"findings": {"missing_fields": []}, "steps": [{"check": "date_order", "result": "pass", "evidence": {}}]}

    monkeypatch.setattr(validation_workers, "run_worker_skill", fake_skill)

    out = await validator.validator({"case": "termination", "facts": FACTS, "records": []})

    assert (seen["bundle"], seen["worker"]) == ("validation", "validator")
    assert out == {"case": "termination", "worker": "validator", "findings": {"missing_fields": []},
                   "steps": [{"check": "date_order", "result": "pass", "evidence": {}}], "flags": []}
