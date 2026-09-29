---
name: execution
description: >
  Use this skill when the Execution Agent (Stage 4) receives a termination
  service order whose flags have all been resolved by a reviewer. Prepares the
  final payment package for a person to post. It does not submit payroll or
  write to any system.
---

# SKILL: Payment Package Preparation (Stage 4)
**Chain position:** orchestrator → validation → compliance → payroll calculation → review → **execution**
**Runs at:** last, only after every flag on the order is resolved.

---

## Inputs

- `service_order`, `lookups` — the order and the Orchestrator's lookups
- `previous_results` — Validation, Compliance and Payroll Calculation outputs
- `flags` — every flag raised, each with the reviewer's `decisions`

## What this stage does — and does not do

- It **prepares** the payment package and nothing else.
- It **never** submits a payroll run, pays anyone, or updates Salesforce or
  any other system, even if a tool for that is available. A person posts the
  payment afterwards.

## Steps

1. **Start from Payroll Calculation's output** — net pay, payment method, pay date.
2. **Apply the reviewer's decisions** from the resolved flags. For example:
   - `complianceTiming` confirmed → use the required (earlier) due date
   - `paymentMethodFail` confirmed → use the recommended payment method
   - `benefitsAmbiguous` → use the option the reviewer chose (`value`)
   - `netPayMismatch` confirmed → use the calculated net pay
   Record one step per decision applied.
3. **Check the package is complete** — net pay, payment method and pay date
   are all known. If any is missing, the package status is `blocked`.
4. **Special instructions** — carry Validation's special delivery instructions
   into the package.

## Rules

- Never invent a value; take every figure from the inputs.
- Do not raise flags — review is already over. Report problems through the
  package `status` and `blocked_reason`.

## Output

- `net_pay` — number in USD, or null
- `payment_method` — `direct_deposit` or `check`, or null
- `pay_date` — ISO date, or null
- `special_instructions` — text or null
- `decisions_applied` — list of `{"flag_id", "type", "effect"}`
- `status` — `ready_for_posting` or `blocked`
- `blocked_reason` — text when blocked, else null
