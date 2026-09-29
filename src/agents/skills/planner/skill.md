---
name: planner
description: >
  Use this skill when the Planner agent receives a termination service order
  from the Orchestrator. Builds the plan: which specialist agents process the
  order, in what order, and what each should focus on, and sets how urgent the
  order is.
---

# SKILL: Planner
**Position:** orchestrator → **planner** → the orchestrator runs the plan, one
agent at a time, and each agent reports back to the orchestrator.

---

## Inputs

- `service_order` — the service order record, already fetched

## The agents a plan can use

| agent | what it does |
|---|---|
| `validation` | the order is complete and consistent with the employee record; decides the pay cycle and due date inputs |
| `compliance` | the state's final-pay rules and the final-pay due date |
| `payroll-calculation` | final pay, leave payout, deductions, net pay |
| `execution` | prepares the payment package for a person to post |

Use only these names.

## PRIORITY phase — do this first

- `high` — final pay is due today or tomorrow, the termination is involuntary
  in a state with same-day final-pay rules, or the order is marked high priority
- `medium` — final pay is due within the week
- `low` — everything else

Base it on the order's dates, termination type, state and stated priority.
Never invent a date that is not in the data.

## PLAN phase — using the priority

Start from the generic plan, which fits every termination order today:

1. `validation`
2. `compliance`
3. `payroll-calculation`
4. `execution`

Rules:

- Each agent appears at most once.
- `execution` is always the last step.
- An agent must run after the agents whose output it needs: compliance needs
  validation, payroll-calculation needs compliance, execution needs all three.
- For each step, write a `task`: one sentence telling that agent what to focus
  on for **this** order — e.g. the state, the termination type (voluntary or
  involuntary), the pay group, or anything unusual in the order. Use only facts
  that are in the order; never invent them.
- When the priority is `high`, say in the tasks what makes it urgent (e.g. the
  final-pay deadline) so each agent checks it first.

## Output

- `priority` — `high`, `medium` or `low`
- `plan` — the ordered list of steps, each `{"agent": ..., "task": ...}`
- `reason` — one short sentence on why this priority and plan
