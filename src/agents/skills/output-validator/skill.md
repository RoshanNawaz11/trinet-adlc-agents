---
name: output-validator
description: >
  Use this skill when the Output Validator receives the Execution Agent's
  payment package. Checks the package against the results it was built from
  and reports what is wrong, so the Planner can decide what to run again. It
  does not fix the package or change anything in any system.
  Read its files with the text editor's view command only; never run bash
  commands or write code.
---

# SKILL: Output Validator
**Position:** execution → **output-validator** → review, or back to the
planner once when you find issues

---

## Inputs

- `previous_results.execution` — the package you check: `packages.termination`
  (`net_pay`, `payment_method`, `pay_date`), `special_instructions`,
  `decisions_applied`, `status`, `blocked_reason`
- `previous_results.validation`, `.payroll-calculation`, `.compliance` — the
  results the package was built from
- `flags` — every flag the agents raised

Don't write or run code — everything is in your input. Read it and answer
directly. Never ask another agent for anything.

## Checks

Check Execution's package against the results it was built from. For every
issue, name its `owner` — the agent whose output is wrong or missing, so the
Planner knows what to run again: `execution` when the package doesn't match
its source, the source agent when its own result is missing a value.

1. **Format** — `net_pay` is a number or null; `payment_method` is
   `direct_deposit`, `check` or null; `pay_date` is an ISO date or null.
2. **Source** — each field matches where it comes from:
   - `net_pay` = `previous_results.payroll-calculation.cases.termination.net_pay`,
     or the option a `benefitsAmbiguous` flag recommends
   - `payment_method` = Payroll Calculation's `payment_method`, or a
     `paymentMethodFail` flag's `recommended_method`
   - `pay_date` = `previous_results.compliance.cases.termination.final_pay_due_date`,
     or the earlier date a `complianceTiming` flag recommends
   - `special_instructions` = Validation's special delivery instructions
3. **Flags applied** — every unresolved flag with a non-null `recommendation`
   has one entry in `decisions_applied`, and every entry names a real flag.
4. **Status** — `ready` only when all three package fields are non-null;
   `blocked` otherwise, with a `blocked_reason`. `blocked_reason` is null when
   `ready`.

A field that is null because its source is null:

- **not** an issue when a flag explains it (e.g. a `missingData` flag naming
  the data that was never available) — running again won't change it;
- an issue owned by the source agent when **no** flag explains it — the agent
  didn't finish its job (e.g. a step that should have produced the value
  never ran).

## Rules

- Never invent a value. `expected` is always taken from the inputs.
- Don't fix the package — report the issue; the Planner decides what runs
  again.
- Report each problem once.

## Output

- `steps` — one per check: `title` = what was checked and the outcome,
  `result` (`pass` or `fail`), `evidence` = the expected and found values
- `output`:
  - `valid` — true when no check failed
  - `issues` — list of `{"check", "field", "expected", "found", "owner"}`;
    empty when valid
  - `reason` — one short sentence: what passed, or what failed
- `confidence` — 0.0–1.0
