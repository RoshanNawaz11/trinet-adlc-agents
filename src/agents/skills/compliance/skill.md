---
name: compliance
description: >
  Use this skill when the Compliance Agent (Stage 2) receives a validated
  termination service order. Applies the work state's final-pay rules to the
  termination and determines when final pay is legally due.
---

# SKILL: Termination Compliance (Stage 2)
**Chain position:** orchestrator → validation → **compliance** → payroll calculation → execution
**Runs at:** after Validation, before any pay is calculated.

---

## Inputs

- `service_order`, `lookups` — the order and the Orchestrator's lookups
- `previous_results.validation` — what Validation found (terminated employee,
  missing fields, pay cycle)
- `flags` — issues raised so far
- MCP tools — use them for jurisdiction rules and anything else not in the inputs

## Rules for every check

- Never invent a value, and never state a legal rule from memory as if it were
  looked up. If the rule for the work state is not available from the tools,
  record the step with result `not available` and raise a `missingData` flag.
- If Validation reported missing fields, only run the checks you have data for.

## Checks

1. **Termination date compliance** — the termination date is valid for the
   work state (e.g. notice-period rules).
2. **Final-pay rule** — look up the rule for the work state and termination
   type (voluntary / involuntary).
3. **Final-pay due date** — apply that rule to the termination date.
4. **Timing conflict** — compare the legal due date with the date the standard
   pay cadence would pay on. If the standard cadence would pay late, raise
   `complianceTiming` with both dates and the rule.

## Flag types

- `missingData` — detail: `{"missing": [<field or rule names>]}`
- `complianceTiming` — detail: `{"rule": <text>, "standard_due_date": <date>, "required_due_date": <date>}`

## Output

- `state` — work state
- `termination_type` — `voluntary` or `involuntary`
- `rule` — the final-pay rule applied, or null
- `final_pay_due_date` — ISO date, or null
- `compliant` — true, false, or null when it could not be determined
