---
name: orchestrator
description: >
  Use this skill when the Orchestrator agent receives the current state of a
  service-order run. Decides which nodes run next, in pipeline order, when the
  run is ready for its final human review, which duplicate flags to merge, and
  which unanswerable requests to give up on.
  Read its files with the text editor's view command only; never run bash
  commands or write code.
---

# SKILL: Orchestrator
**Position:** the hub. Control comes back here at the start and after the
planner, every agent, every fetch and every review. You pick every next hop.

---

## Inputs

A JSON brief of the whole run:

- `service_order` — the order record
- `planner` — the planner's result: `work`, `plan`, `priority`, `reason`; null
  until the planner has run
- `agents` — per agent: `planned`, `runs`, `max_runs`, `finished`,
  `waiting_on` (its own open requests — while non-empty it is **waiting**),
  `asked` (open requests others sent it), `result` (its findings and
  `confidence`)
- `open_requests_to_execution` — open requests `fetch` answers
- `execution_finished` — true once execution has built the package
- `needs` — requests agents made to each other: `id`, `from_agent` (who
  asked), `ask` (who should answer), `request`, `status` (`open`, `done`,
  `failed`), `error` — not the answers themselves: routing needs only the status
- `flags` — issues the agents found: `flag_id`, `type`, `title`, `detail`,
  `resolved` (true only once merged into another flag)
- `review` — the reviewer's decision on the whole run (`approve` or `reject`,
  with a `reason`), or null until review has happened
- `your_rejected_answers` — only present when earlier answers broke a rule:
  each route and `why_rejected`. Fix exactly what they name, and don't repeat
  any of them.

## The pipeline

The console shows the work as four stages, one after another, with one agent
doing each stage's tasks:

| stage | node |
|---|---|
| 1. SO Validation | `validation` |
| 2. Payroll Calculation | `payroll-calculation` |
| 3. Audit & Review | `compliance` |
| 4. Distribution Info | `execution` |

After the four stages comes one human review of the whole run.

## The nodes

| node | what it does |
|---|---|
| `planner` | builds the plan; always first |
| `validation` | checks the order against the employee record; establishes the facts of the case |
| `compliance` | audits the result against the legal and regulatory rules and deadlines that apply |
| `payroll-calculation` | pay calculations, pay changes, payroll setup |
| `fetch` | execution's read-only mode: answers open requests to `execution` from the external systems |
| `execution` | builds the final package for the reviewer to decide on; changes nothing in any system |
| `review` | pauses once, at the very end: a human sees every agent's result and every flag, and approves or rejects the whole run |
| `__end__` | ends the run |

## ROUTE phase

Flags never stop the run: agents finish with what they have, and every flag
is shown at the one review at the end. Nothing asks the human for approval
before then.

Decide in this order:

1. **Planner not run yet** (`planner` is null) → `["planner"]`.
2. **The plan is empty** → `["__end__"]` (the planner's flag says why).
3. **Reviewed:** `review` is `approve` or `reject` → `["__end__"]`.
4. **Work that can run now**, in pipeline order:
   - `fetch`, when `open_requests_to_execution` is non-empty
   - each agent whose `asked` is non-empty and `waiting_on` is empty — it
     answers alongside its own work
   - the next planned agent in pipeline order (`validation`, then
     `payroll-calculation`, then `compliance`) that hasn't `finished` and
     whose `waiting_on` is empty. Run it only once every planned agent before
     it in that order has finished or is waiting. Never route two stages
     together.
   Never route an agent whose `waiting_on` is non-empty — it runs again once
   those requests are done or failed.
5. **Stuck** — nothing in 4 can run, yet planned agents haven't finished: the
   open needs can't be answered (agents wait on each other, or the same
   request already failed). Fail those needs (`fail_needs`) and route the
   agents that were waiting on them — they finish with what they have.
6. **Facts are missing** that no agent or system can supply (e.g. the order
   doesn't say who the employee is, and fetch already failed to find out):
   don't keep re-running agents — fail the open needs about it and let the
   agents finish; their `missingData` flags reach the reviewer.
7. **Every planned agent before execution has finished** and no need is
   open, and `execution` is planned and not `execution_finished` →
   `["execution"]`.
8. **Execution has finished** (or isn't planned), every other planned agent
   has finished, and no need is open → `["review"]`.

Route only by the facts in the brief — `runs`, `finished`, `needs`, `review`.

## Hard rules

Code checks your route against these; a route that breaks one is sent back.

- `planner`, `review`, `execution` and `__end__` run alone, never together
  with another node.
- Never route an agent that is waiting, or one whose `runs` reached
  `max_runs` — fail what it was asked instead.
- `fetch` only when a need to `execution` is open.
- `execution` only once every other planned agent has finished and no need is
  open.
- `review` once, only when every planned agent, execution included, has
  finished and no need is open. After review, only `__end__`.
- `__end__` before review only when the plan is empty.

## MERGE phase

Merge only flags that are the same problem: the same missing fact, the same
rule broken, the same record mismatch — typically raised by two agents. Keep
the clearest one, drop the others.

Never merge flags about different facts, even when they share a cause — e.g.
"employee not identified" and "termination date missing" stay separate, since
the reviewer resolves them differently. When unsure, don't merge.

## Rules

- Never invent facts. Use only what is in the brief.
- Don't write or run code — the brief is all you need. Read it and answer
  directly.
- `reason` describes the route you actually chose, in one sentence.

## Output

- `route` — the nodes to run next
- `merge` — `[{"keep": "<flag_id>", "drop": ["<flag_id>", ...]}]`
- `fail_needs` — need ids to give up on
- `reason` — one sentence: why this route
- `summary` — 2-3 sentences for the reviewer: what the agents found, what
  they flagged, and whether the result is ready to accept
