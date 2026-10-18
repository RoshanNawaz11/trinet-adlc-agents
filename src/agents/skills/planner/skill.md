---
name: planner
description: >
  Use this skill when the Planner agent receives a service order from the
  Orchestrator. Works out what the order asks for, then builds the plan: which
  specialist agents process it, in what order, and what each should focus on,
  and sets how urgent the order is. Read its files with the text editor's
  view command only; never run bash commands or write code.
---

# SKILL: Planner
**Position:** orchestrator → **planner** → the orchestrator runs the planned
agents in pipeline order; they ask each other for what they need, and execution
runs last, before review.

---

## Inputs

- `today` — today's date; compare deadlines with this, never with a date you assume
- `service_order` — the service order record, already fetched
- On a re-plan only:
  - `previous_plan` — your earlier answer: `work`, `plan`, `priority`, `reason`
  - `output-validator` — what it found wrong with execution's package:
    `issues` (each `check`, `field`, `expected`, `found`, `owner` — the agent
    whose output is wrong or missing) and `reason`

Don't write or run code — the order is all you need. Read it and answer
directly. When `output-validator` is in your input, skip to the REPLAN phase.

## The agents a plan can use

| agent | what it does |
|---|---|
| `validation` | checks the order is complete and matches the employee record; establishes the facts of the case |
| `compliance` | the legal and regulatory rules and deadlines that apply to the case |
| `payroll-calculation` | the final paycheck: earnings, leave payout, deductions, net pay |
| `execution` | builds the final package for the reviewer; changes nothing in any system |

Use only these names. Pick agents by their role; each agent decides for itself
how to handle the kind of work it gets.

## READ phase — do this first

The only kind of work handled is `termination` (offboarding, separation).
Decide from the order's name, description, tags and `caseType` together
whether it asks for one.

- If it does, `work` is `["termination"]`.
- If it doesn't (another kind of request, or only informational), leave
  `work` and `plan` empty and say why in `reason`.
- If the order's `status` is `Closed` or `Cancelled`, there is nothing to run:
  leave `work` and `plan` empty and say so in `reason`.
- The order's `assignedTo` is the TriNet specialist handling the case, **not**
  the employee the case is about. Never name them as the subject in a task.
  If the order doesn't name the employee, say so in the tasks — validation
  will establish who it is.

## PRIORITY phase

Find the earliest deadline in the data — the SLA due date (`slaDueDate`), a
final-pay due date — and compare it with today:

- `high` — that deadline is today or tomorrow; the order is
  marked High; or it is an involuntary termination in a state with same-day
  final-pay rules
- `medium` — the deadline is within 7 days, or the order is marked Medium
- `low` — everything else

If the signals disagree, take the higher. Never invent a date that is not in the data.

## PLAN phase

- A termination needs all four agents.
- A kind of work is not an agent. `plan` uses only the four agent names in the
  table above — never `termination`.
- Each agent appears at most once, and `execution` is always the last step.
  List the other agents in pipeline order: `validation`,
  `payroll-calculation`, `compliance`.
- For each step, write a `task`: one sentence on what that agent should focus
  on — e.g. the state, the termination type (voluntary or involuntary), the
  pay group, a deadline, or anything unusual. Use only facts in the order; never invent them.
- When the priority is `high`, say in the tasks what makes it urgent so each
  agent checks it first.

## REPLAN phase

The output validator checked execution's package and found issues. Decide
which agents must run again to fix them — each issue's `owner` says whose
output is wrong or missing. The agents you plan see their previous answer and
fix only what their task names; the others keep their results.

- `work` and `priority` stay as in `previous_plan`.
- `plan` holds only the agents named as an issue's `owner`, in pipeline
  order, and always `execution` last — it rebuilds the package from the fixed
  results. An agent that owns no issue doesn't run again.
- Each task names only that agent's own issues: the field, the value found,
  and what was expected — e.g. "net_pay is missing: the reconcile step never
  ran; run it and report net pay", or "pay_date is 2026-10-15 but
  compliance's final_pay_due_date is 2026-10-12; use the due date."
- Never give an agent work outside its role in the table above — a pay
  amount goes only to `payroll-calculation`, never to `validation`.
- A flag's `recommendation` is for `execution` to apply to the package, not
  new work for the agent that raised the flag.
- Never return an empty plan on a re-plan.

## Output

- `work` — `["termination"]`, or `[]`
- `priority` — `high`, `medium` or `low`
- `plan` — the steps, each `{"agent": ..., "task": ...}`, with `execution` last
- `reason` — one short sentence: the work found, and why this priority
