"""The rules engine runs real rules on facts from the mock orders."""

from rules_engine.evaluate import evaluate, load_rule, rules_for
from rules_engine.tables import lookup


def run(rule_id: str, **facts):
    return evaluate(load_rule(rule_id), facts)


def balance(hours, **extra):
    return {"leave_type": "vacation", "balance_hours": hours, "balance_as_of": "2026-09-30",
            "plan_max_hours": 200, "policy_pays_out": None, "already_paid_out": False, **extra}


# ── on-cycle removed (Action 15) ──────────────────────────────────────────

def test_still_in_a_regular_run_is_flagged_once_per_run():
    record = run("payroll.on-cycle-removed", employment_type="regular", regular_runs_found=True,
                 regular_runs=[{"run_pay_date": "2026-10-23", "run_status": "open"},
                               {"run_pay_date": "2026-10-16", "run_status": "processing"}])
    assert record["result"] == "fail"
    assert record["outputs"]["runs_to_remove"] == 2
    assert [f["kind"] for f in record["flags"]] == ["check", "decision"]


def test_removed_from_every_regular_run_passes():
    record = run("payroll.on-cycle-removed", employment_type="regular", regular_runs_found=True, regular_runs=[])
    assert record["result"] == "pass"


def test_unread_runs_are_never_taken_as_removed():
    record = run("payroll.on-cycle-removed", employment_type="regular", regular_runs_found=None)
    assert record["result"] == "not available"
    assert record["flags"][0]["type"] == "missingData"


# ── leave payout ──────────────────────────────────────────────────────────

def test_so_1004_illinois_layoff_pays_no_leave():
    law = lookup("state", {"state": "IL", "termination_type": "involuntary"})
    record = run("payroll.leave-payout", termination_type="involuntary", employment_type="temporary",
                 payout_rate=22.0, last_day_worked="2026-09-30", instruction_kinds=[], **law,
                 leave_balances=[balance(0, other_balance_hours=-5)])
    assert record["result"] == "pass"
    assert record["outputs"]["leave_payout"] == 0
    assert "Another record shows a different balance; the payroll system's is used" in record["notes"]


def test_a_negative_balance_is_never_a_negative_payout():
    record = run("payroll.leave-payout", requirement="required", payout_rate=22.0,
                 last_day_worked="2026-09-30", leave_balances=[balance(-5)])
    assert record["outputs"]["leave_payout"] == 0


def test_so_1003_new_york_pays_its_balance():
    law = lookup("state", {"state": "NY", "termination_type": "voluntary"})
    record = run("payroll.leave-payout", termination_type="voluntary", employment_type="regular",
                 payout_rate=28.0, last_day_worked="2026-08-14", service_months=20,
                 policy_min_service_months=0, instruction_kinds=[], **law,
                 leave_balances=[balance(16, balance_as_of="2026-08-14", policy_pays_out=True)])
    assert law["requirement"] == "policy_else_required"
    assert record["outputs"]["leave_payout"] == 448.0


def test_the_same_rule_gives_each_state_its_answer():
    """16 hours at $28, and a plan that doesn't pay out."""
    def payout(state):
        law = lookup("state", {"state": state, "termination_type": "voluntary"})
        return run("payroll.leave-payout", payout_rate=28.0, last_day_worked="2026-09-30",
                   service_months=24, policy_min_service_months=0, instruction_kinds=[], **law,
                   leave_balances=[balance(16, policy_pays_out=False)])["outputs"]["leave_payout"]

    assert payout("CA") == 448.0     # the law requires it, whatever the plan says
    assert payout("TX") == 0         # the plan decides, and it doesn't pay


def test_a_stale_balance_is_paid_but_provisional():
    record = run("payroll.leave-payout", requirement="required", payout_rate=20.0,
                 last_day_worked="2026-09-30", leave_balances=[balance(10, balance_as_of="2026-09-15")])
    assert record["outputs"]["leave_payout"] == 200.0
    assert record["provisional"] is True
    assert record["flags"][0]["kind"] == "check"


def test_death_stops_the_payout():
    record = run("payroll.leave-payout", termination_type="death", requirement="required",
                 payout_rate=20.0, leave_balances=[balance(10)])
    assert (record["result"], record["outcome"]) == ("not available", "stop")


def test_no_requirement_yet_means_waiting_not_guessing():
    record = run("payroll.leave-payout", payout_rate=20.0, leave_balances=[balance(10)])
    assert (record["result"], record["outcome"]) == ("not available", "wait")
    assert record["outputs"]["leave_payout"] is None


# ── other rules ───────────────────────────────────────────────────────────

def test_termination_reasons_map_to_types():
    def kind(reason):
        return run("validation.termination-type", termination_reason_text=reason)["outputs"]["termination_type"]

    assert kind("Layoff") == "involuntary"
    assert kind("Involuntary") == "involuntary"          # not "voluntary", which it contains
    assert kind("Voluntary") == "voluntary"
    assert kind("Mutual agreement") == "unknown"
    assert kind("Death") == "death"


def test_net_pay_and_what_cant_be_recovered():
    ok = run("payroll.net-pay", gross_pay=1000.0, leave_payout=448.0, system_taxes=300.0,
             deductions=100.0, garnishments=0)
    assert ok["outputs"]["net_pay"] == 1048.0

    short = run("payroll.net-pay", gross_pay=100.0, leave_payout=0, system_taxes=50.0,
                deductions=200.0, garnishments=0)
    assert short["outputs"]["net_pay"] == 0
    assert short["outputs"]["unrecoverable"] == 150.0
    assert short["flags"][0]["type"] == "unrecoverable"


def test_so_1002_order_pay_differs_from_the_system():
    record = run("payroll.matches-system", gross_pay=3000.0, leave_payout=0, net_pay=2100.0,
                 system_net_pay=2100.0, system_total_gross=3000.0, order_total_pay=3200.0)
    assert record["result"] == "fail"
    assert [f["type"] for f in record["flags"]] == ["orderPayMismatch"]


def test_california_discharge_needs_a_live_check():
    law = lookup("state", {"state": "CA", "termination_type": "involuntary"})
    record = run("payroll.payment-method", termination_type="involuntary", employment_type="regular",
                 payment_method_on_file="direct_deposit", method_active=True, prenote_verified=True, **law)
    assert record["result"] == "fail"
    assert record["flags"][0]["detail"]["recommended_method"] == "live_check"


def test_final_pay_due_dates_from_the_state_table():
    tx = lookup("state", {"state": "TX", "termination_type": "involuntary"})
    record = run("compliance.final-pay", termination_type="involuntary", termination_date="2026-10-01",
                 today="2026-10-02", regular_payday="2026-10-09", state_rule_found=True, **tx)
    assert record["outputs"]["final_pay_due_date"] == "2026-10-07"     # within 6 calendar days
    assert record["outputs"]["pay_timing"] == "off-cycle"
    assert record["flags"][0]["type"] == "complianceTiming"

    il = lookup("state", {"state": "IL", "termination_type": "involuntary"})
    record = run("compliance.final-pay", termination_type="involuntary", termination_date="2026-09-30",
                 today="2026-10-01", regular_payday="2026-10-09", state_rule_found=True, **il)
    assert record["outputs"]["final_pay_due_date"] == "2026-10-09"     # the next regular payday
    assert record["outputs"]["pay_timing"] == "on-cycle"


def test_missing_inputs_are_named_never_guessed():
    record = run("payroll.inputs-present", case_facts_confirmed=True, pay_type="hourly",
                 withholding="on_record", final_period_hours=40)
    assert record["result"] == "fail"
    assert record["outputs"]["missing_inputs"] == ["pay_rate"]


def test_rules_are_chosen_by_agent_worker_and_case_type():
    assert [r["id"] for r in rules_for("payroll-calculation", "leave", {"termination_type": "involuntary"})] == ["payroll.leave-payout"]
    assert rules_for("validation", "validator", {"termination_type": "involuntary"}) \
        != rules_for("validation", "validator", {"termination_type": "voluntary"})     # notice-given: voluntary only
