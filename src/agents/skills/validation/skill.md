---
name: validation
description: >
  Use this skill when the Validation Agent (Stage 1) receives a termination
  service order. Checks the order is complete and consistent with the employee
  record before any compliance or payroll work starts.
---

# SKILL: Termination Validation (Stage 1)
**Chain position:** orchestrator → **validation** → compliance → payroll calculation → execution
**Runs at:** first stage after the Orchestrator sends the service order to AI processing.

---

## Inputs

- `service_order` — the order as the backend described it
- `lookups` — service order and employee data the Orchestrator already fetched
- `previous_results` — empty at this stage
- MCP tools — use them for anything the lookups don't already contain

## Rules for every check

- Never invent a value. If a fact is not in the inputs or the tools, record the
  step with result `not available` and raise a `missingData` flag naming the
  missing fields.
- The service order's `assignedTo` is the TriNet specialist handling the case,
  not necessarily the employee being terminated. Only treat someone as the
  terminated employee if the order says so.

## Checks

1. **Terminated employee identified** — the order names the employee being
   terminated, and that employee exists in the employee record.
2. **Required fields present** — termination date, termination reason
   (voluntary / involuntary), work state, pay group, compensation frequency.
3. **Employee record state** — employment status and hire date are consistent
   with a termination (e.g. not already terminated).
4. **Duplicate orders** — no other open service order for the same employee
   and termination. If there is one, raise `duplicateSO` with both order ids.
5. **Special delivery instructions** — read them from the order description;
   report "none" when there are none.
6. **On-cycle vs off-cycle** — off-cycle when the last day worked precedes the
   current pay run; `unknown` when the pay schedule is not available.

## Flag types

- `missingData` — detail: `{"missing": [<field names>]}`
- `duplicateSO` — detail: `{"this_order": <id>, "other_order": <id>}`

## Output

- `terminated_employee_id` — or null if not identified
- `complete` — true only if every required field is present
- `missing_fields` — list of missing field names
- `pay_cycle` — `on-cycle`, `off-cycle` or `unknown`
- `special_instructions` — text or null
