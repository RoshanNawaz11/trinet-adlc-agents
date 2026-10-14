"""Fetches the rules that apply to a case, by its attributes (the case types).
An agent asks for them; the answer goes into its context and its workers'.

    get_rules("payroll", {"state": "CA", "termination_type": "involuntary"})
"""

from __future__ import annotations

from typing import Any

from rules_engine.evaluate import all_rules, applies
from rules_engine.tables import lookup

# the attributes an agent gives to fetch its rules
ATTRIBUTES = ["state", "termination_type", "employment_type", "pay_group"]

HOW_TO_READ = (
    "Each rule's `worker` is the worker that applies it. `inputs` are the facts it uses, and "
    "`judgement` says how to read the ones that need it; `lines` run once per item of a list "
    "fact, then their `total`; `compute` works out named values, in order; every `checks` "
    "entry whose `when` holds applies; then the FIRST of `cases` whose `when` holds decides "
    "(the last is always true). A `then` value starting with `=` is a formula. A fact that "
    "isn't available is null, and anything worked out from it is null too — report "
    "`not available`, never guess. Functions: missing(a, …) — any is null; missing_of('a', …) "
    "— the names of the null ones; within(a, b, t) — they differ by at most t; mentions(text, "
    "[words]) — contains any, ignoring case; min/max skip nulls; first(list); days_between(a, b) "
    "and hours_between(a, b) — b − a; add_days(d, n); due_date(form, amount, start, next_payday, "
    "period_end) — applies a `due` form (immediately, within_hours, calendar_days, "
    "business_days, next_business_day, next_regular_payday, end_of_pay_period); "
    "largest_difference(name=[a, b], …) and smallest(name=x, …) — the name that wins. "
    "`state_law` is the work state's law for this termination type."
)


def get_rules(agent: str, attributes: dict[str, Any]) -> dict[str, Any]:
    """The agent's rules that apply to these attributes, and the state's law."""
    attributes = {k: attributes.get(k) for k in ATTRIBUTES}
    rules = [
        {k: v for k, v in r.items() if k not in ("to_confirm", "agent", "applies_to")}
        for r in all_rules() if r.get("agent") == agent and applies(r, attributes)
    ]
    return {
        "attributes": attributes,
        "state_law": lookup("state", attributes),
        "how_to_read": HOW_TO_READ,
        "rules": rules,
    }
