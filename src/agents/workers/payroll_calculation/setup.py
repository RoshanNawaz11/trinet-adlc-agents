"""Payroll's setup worker — a model. Onboarding only: the new employee's first
pay date and what they still have to provide
(skills/payroll-calculation/workers/setup.md).

    input  {"case", "facts", "service_order", "data", "worker_results"}
    output {"case", "worker", "findings": {"first_pay_date", "setup_to_collect", ...}, "steps", "flags"}
"""

from __future__ import annotations

from typing import Any

from agents.workers import run_checker


async def setup(i: dict[str, Any]) -> dict[str, Any]:
    return await run_checker("payroll-calculation", "setup", i)
