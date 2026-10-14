"""A worker wired to the rules: the model reports facts, the rules decide."""

import asyncio

import agents.workers as workers
from rules_engine.decide import ask_for, decide
from rules_engine.tables import lookup


def balance(hours, **extra):
    return {"leave_type": "vacation", "balance_hours": hours, "balance_as_of": "2026-09-30",
            "plan_max_hours": 200, "policy_pays_out": None, "already_paid_out": False, **extra}


SO_1004 = {"state": "IL", "termination_type": "involuntary", "employment_type": "temporary",
           "payout_rate": 22.0, "last_day_worked": "2026-09-30", "instruction_kinds": [],
           "leave_balances": [balance(0, other_balance_hours=-5)]}


def test_the_model_is_asked_for_the_rules_facts():
    text = ask_for("payroll-calculation", "leave")
    for name in ("termination_type", "payout_rate", "leave_balances", "leave_balances[].balance_hours"):
        assert f'"{name}"' in text
    assert "requirement" in text               # filled by the state table when it has a row


def test_the_state_table_fills_the_requirement_and_the_rule_decides():
    result = decide("payroll-calculation", "leave", SO_1004)
    assert result["findings"]["leave_payout"] == 0
    assert result["findings"]["rules"]["payroll.leave-payout"]["result"] == "pass"
    assert result["steps"][0]["evidence"]["facts"]["requirement"] == \
        lookup("state", {"state": "IL", "termination_type": "involuntary"})["requirement"]
    assert [s["check"] for s in result["steps"]] == ["Facts reported", "payroll.leave-payout"]


def test_so_1003_new_york_pays_448():
    facts = {"state": "NY", "termination_type": "voluntary", "employment_type": "regular",
             "payout_rate": 28.0, "last_day_worked": "2026-08-14", "service_months": 20,
             "policy_min_service_months": 0, "instruction_kinds": [],
             "leave_balances": [balance(16, balance_as_of="2026-08-14", policy_pays_out=True)]}
    assert decide("payroll-calculation", "leave", facts)["findings"]["leave_payout"] == 448.0


def test_rule_flags_reach_the_worker_result():
    facts = {**SO_1004, "state": "CA", "leave_balances": [balance(10, balance_as_of="2026-09-15")]}
    flags = decide("payroll-calculation", "leave", facts)["flags"]
    assert flags and flags[0]["type"] == "payroll.leave-payout" and flags[0]["detail"]["kind"] == "check"


def test_the_leave_worker_runs_the_rules_on_the_models_facts(monkeypatch):
    async def model(bundle, i, instruction, key):
        assert key == "facts" and '"leave_balances"' in instruction
        return {"facts": SO_1004, "sources": {"payout_rate": "pay data"}}

    monkeypatch.setattr(workers, "run_worker_skill", model)
    result = asyncio.run(workers.run_with_rules("payroll-calculation", "leave", {"case": "termination"}))
    assert (result["case"], result["worker"]) == ("termination", "leave")
    assert result["findings"]["leave_payout"] == 0


def test_the_fetched_attributes_and_state_law_are_facts_the_model_needn_t_find(monkeypatch):
    """The model left state and termination type null; the agent's fetched rules have them."""
    sent = {}

    async def model(bundle, i, instruction, key):
        sent.update(i)
        return {"facts": {"state": None, "termination_type": None, "payout_rate": 28.0,
                          "last_day_worked": "2026-09-30", "instruction_kinds": [],
                          "leave_balances": [balance(16)]}}

    monkeypatch.setattr(workers, "run_worker_skill", model)
    from rules_engine.fetch import get_rules
    fetched = get_rules("payroll-calculation", {"state": "CA", "termination_type": "involuntary"})
    result = asyncio.run(workers.run_with_rules("payroll-calculation", "leave", {"case": "termination", "rules": fetched}))

    assert "rules" not in sent                                   # the model doesn't apply rules
    assert result["findings"]["leave_payout"] == 448.0           # CA requires it: 16 h × $28
    facts = result["steps"][0]["evidence"]
    assert (facts["facts"]["state"], facts["sources"]["requirement"]) == ("CA", "fetched with the rules")
