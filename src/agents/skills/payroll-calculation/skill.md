---
name: payroll-calculation
description: >
  Use this skill when the Payroll Calculation Agent (Stage 3) receives a
  validated, compliance-checked termination service order. Computes final pay,
  leave payout and deductions, and checks the result against the payroll
  system's own calculation and the payment method on file.
---

# SKILL: Final Pay Calculation (Stage 3)
**Chain position:** orchestrator → validation → compliance → **payroll calculation** → execution
**Runs at:** after Compliance; the last stage before human review and execution.

---

## Inputs

- `service_order`, `lookups` — the order and the Orchestrator's lookups
- `previous_results.validation` — terminated employee, pay cycle
- `previous_results.compliance` — final-pay due date and rule
- `flags` — issues raised so far
- MCP tools — use them for hours, leave balances, pay data and the payroll
  system's calculation

## Rules for every check

- Never invent a value. Every amount must come from the inputs or the tools,
  or be computed from them. If a figure is not available, record the step with
  result `not available` and raise a `missingData` flag.
- Show your working: put the inputs of every calculation in the step's evidence.

## Checks

1. **Pay attributes** — employment type (regular / temp), pay group,
   compensation frequency, termination reason.
2. **Hours** — regular and overtime hours for the final pay period.
3. **Benefits eligibility** — regular employees are eligible, temp status is
   not. If the employee's leave or status codes allow two valid outcomes, raise
   `benefitsAmbiguous` with both options and the net pay for each.
4. **Leave payout** — unused leave hours and their payout amount.
5. **Final pay** — gross pay + leave payout, minus federal tax, state tax and
   benefit deductions = net pay.
6. **System comparison** — compare your net pay with the payroll system's
   calculation. If they differ, raise `netPayMismatch` with both amounts and
   what explains the difference.
7. **Payment method** — the method on file (direct deposit / check) and
   whether it can be used. If it will fail (e.g. a closed account), raise
   `paymentMethodFail` with the reason and a recommended method.

## Flag types

- `missingData` — detail: `{"missing": [<field names>]}`
- `benefitsAmbiguous` — detail: `{"option_a": {"label", "net_pay"}, "option_b": {"label", "net_pay"}}`
- `netPayMismatch` — detail: `{"system_net_pay", "calculated_net_pay", "explanation"}`
- `paymentMethodFail` — detail: `{"current_method", "reason", "recommended_method"}`

## Output

- `gross_pay`, `leave_payout`, `federal_tax`, `state_tax`, `benefits_deduction`, `net_pay`
- `system_net_pay` — the payroll system's figure, or null
- `benefits_eligible` — true, false, or null
- `payment_method` — `direct_deposit` or `check`, or null
- `pay_date` — the final-pay due date from Compliance

Amounts are numbers in USD; use null for anything not available.
