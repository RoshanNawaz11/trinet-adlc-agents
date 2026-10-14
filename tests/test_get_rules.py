"""Agents fetch their rules by the case's attributes; the rules go into the
agent's context and its workers'. The model and the queue are faked."""

from __future__ import annotations

import pytest

from agents.nodes.stage_agent import AgentOutputError
from agents.nodes.validation.node import validation_node
from rules_engine.fetch import get_rules
from test_validation_agent import FINAL, GATEWAY, Fake, _check, _state, _tasks

ASK = {"get_rules": {"state": "CA", "termination_type": "involuntary"}}


def ids(fetched: dict) -> list[str]:
    return [r["id"] for r in fetched["rules"]]


def test_rules_are_fetched_by_agent_and_attributes():
    payroll = get_rules("payroll-calculation", {"state": "CA", "termination_type": "involuntary"})
    assert "payroll.leave-payout" in ids(payroll)
    assert all(i.startswith("payroll.") for i in ids(payroll))
    assert payroll["state_law"]["requirement"] == "required"
    assert payroll["state_law"]["allowed_methods"] == ["live_check"]

    # notice-given is for voluntary terminations only
    assert "validation.notice-given" in ids(get_rules("validation", {"termination_type": "voluntary"}))
    assert "validation.notice-given" not in ids(get_rules("validation", {"termination_type": "involuntary"}))


def test_a_state_with_no_row_has_no_law_never_another_states():
    assert set(get_rules("compliance", {"state": "ZZ", "termination_type": "voluntary"})["state_law"].values()) == {None}


async def test_the_agent_fetches_its_rules_then_its_workers_get_them(monkeypatch):
    fake = Fake(monkeypatch, [ASK, _tasks(_check("validator")), FINAL])

    update = await validation_node(_state(), gateway=GATEWAY)

    assert '"get_rules"' in fake.instructions[0]
    assert "rules" not in fake.inputs[0]
    agent_sees = fake.inputs[1]["rules"]                                # the agent: which worker applies what,
    assert agent_sees["attributes"]["state"] == "CA"                    # not the rules themselves
    assert "rules" not in agent_sees
    assert "validation.termination-type" in agent_sees["by_worker"]["validator"]
    [[task]] = fake.dispatched                                          # the worker: only its own rules, in full
    worker_rules = task["input"]["rules"]["rules"]
    assert worker_rules and all(r["worker"] == "validator" for r in worker_rules)
    assert update["rules"]["validation"]["attributes"]["termination_type"] == "involuntary"
    assert update["steps"][0]["title"] == "Fetched the rules for the case"
    assert "validation.termination-type" in update["steps"][0]["evidence"]["rules"]


async def test_a_rerun_keeps_the_rules_it_fetched(monkeypatch):
    fetched = get_rules("validation", ASK["get_rules"])
    fake = Fake(monkeypatch, [FINAL])

    await validation_node(_state(rules={"validation": fetched}, runs={"validation": 1}), gateway=GATEWAY)

    assert fake.inputs[0]["rules"]["attributes"] == fetched["attributes"]


async def test_an_agent_that_keeps_fetching_is_stopped(monkeypatch):
    fake = Fake(monkeypatch, [ASK, ASK, ASK])

    with pytest.raises(AgentOutputError):                               # two fetches, then it must answer
        await validation_node(_state(), gateway=GATEWAY)
    assert len(fake.inputs) == 3
