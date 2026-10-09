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
agents in parallel; they ask each other for what they need, and execution runs
last, after review.

---

## Inputs

- `service_order` — the service order record, already fetched

Don't write or run code — the order is all you need. Read it and answer
directly.

## The agents a plan can use

| agent | what it does |
|---|---|
| `validation` | checks the order is complete and matches the employee record; establishes the facts of the case |
| `compliance` | the legal and regulatory rules and deadlines that apply to the case |
| `payroll-calculation` | anything pay-related: calculations, pay changes, payroll setup |
| `execution` | carries out the result in the external systems, after review |

Use only these names. Pick agents by their role; each agent decides for itself
how to handle the kind of work it gets.

## READ phase — do this first

Work out which kinds of work the order asks for, from its name, description,
tags and `caseType` together. `caseType` labels the main request only — one
order can contain several kinds of work (e.g. an offboarding that also needs a
benefits change). The kinds of work:

`termination`, `onboarding`, `benefits`, `payroll`, `records`, `compliance`

- List every kind the order asks for. Never invent work it doesn't ask for.
- If it asks for nothing (e.g. it is only informational), leave `work` and
  `plan` empty and say why in `reason`.
- If the order's `status` is `Closed` or `Cancelled`, there is nothing to run:
  leave `work` and `plan` empty and say so in `reason`.
- The order's `assignedTo` is the TriNet specialist handling the case, **not**
  the employee the case is about. Never name them as the subject in a task.
  If the order doesn't name the employee, say so in the tasks — validation
  will establish who it is.

## PRIORITY phase

Find the earliest deadline in the data — the SLA due date (`slaDueDate`), a
final-pay due date, a start date — and compare it with today:

- `high` — that deadline is today or tomorrow; the order is
  marked High; or it is an involuntary termination in a state with same-day
  final-pay rules
- `medium` — the deadline is within 7 days, or the order is marked Medium
- `low` — everything else

If the signals disagree, take the higher. Never invent a date that is not in the data.

## PLAN phase

- Plan the agents whose role the work needs — most work needs all four.
- A kind of work is not an agent. `plan` uses only the four agent names in the
  table above — never `termination`, `benefits` or another kind of work. Name
  the work inside the agent's `task` instead.
- Each agent appears at most once, and `execution` is always the last step.
  The other agents run in parallel and ask each other for what they need —
  don't order them for dependencies.
- For each step, write a `task`: one sentence naming the kinds of work that
  agent handles for this order and what to focus on — e.g. the state, the
  termination type (voluntary or involuntary), the pay group, a deadline, or
  anything unusual. Use only facts in the order; never invent them.
- When the priority is `high`, say in the tasks what makes it urgent so each
  agent checks it first.

## Output

- `work` — the kinds of work found, e.g. `["termination"]`
- `priority` — `high`, `medium` or `low`
- `plan` — the steps, each `{"agent": ..., "task": ...}`, with `execution` last
- `reason` — one short sentence: the work found, and why this priority
