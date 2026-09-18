---
name: worker-classify
description: >
  Use this skill when the Worker agent receives a "classify" subtask, typically
  downstream of an Expert summary or directly from the Planner for bounded-decision
  tasks. Assigns input to a fixed label set, then dispatches the label-mapped action
  via the MCP server. Worker is the only agent in the chain that produces a real
  side effect. Triggered by: subtask.type == "classify", or any task requiring a
  categorical decision followed by an action.
---

# SKILL: Worker Classify & Dispatch (execution layer)
**Chain position:** orchestrator → planner → (expert, optional) → **worker**
**Runs at:** the terminal step of a subtask chain — after any needed synthesis
(Expert) is done, when a bounded decision + a real-world action is required. Worker
is the *discriminative* + *actuating* half — it doesn't reason open-endedly, it
picks one of N labels and does the thing tied to that label.

---

## Inputs required

1. `content` — the material to classify (raw input, or an Expert summary object —
   see Upstream input handling below)
2. `label_set` — the fixed taxonomy for this task (Planner sets this per subtask;
   don't let Worker invent its own labels)
3. `task_id` — correlates back to the task graph
4. `action_map` (optional, else falls back to a default) — label → MCP tool name

---

## Upstream input handling

If `content` arrives as an Expert summary object rather than raw text:
- Check `confidence` and `escalation` first (see expert-summarize skill). If
  confidence is low or an escalation is present, **Worker must not classify** —
  bounce the task back to Planner instead of guessing on shaky input. This is the
  same discipline as job-resolver refusing to invent an entity binding.
- Otherwise classify against `summary` + `key_points`, not the full original source
  — Worker should trust the Expert's compression rather than re-deriving it.

## CLASSIFY phase

1. Assign `content` to exactly one label from `label_set`. No free-text labels,
   no multi-label output — if the task genuinely needs multi-label, that's a
   Planner-level task design issue, not something Worker should paper over.
2. Self-score confidence on the label assignment (not the same number as any
   upstream Expert confidence — this is Worker's own certainty about the label).
3. If confidence is below threshold (e.g. < 0.6) and the label set includes a
   safe/neutral default (e.g. "routine", "needs_review"), fall back to that rather
   than forcing a high-stakes label (e.g. "escalate", "urgent") on weak signal.

## DISPATCH phase — this is what makes Worker a worker

Classification alone is not Worker's job — that's just a second classifier agent
wearing a different name. The actual differentiator is:

1. Map the assigned label to an MCP tool call via `action_map`.
2. Execute the call against the MCP server (the one your teammate is building —
   Worker is the agent that actually talks to it).
3. Record whether the action fired, and the MCP result/error, in the output.
4. **Never dispatch on a fallback/default label** that was chosen because
   confidence was too low to trust — route those to Planner for human/Expert
   review instead of silently taking the low-stakes action anyway.

Default action map (override per task via `action_map`):

```
urgent    → notify_on_call
escalate  → create_ticket
routine   → queue_for_batch
ignore    → (no action)
needs_review → (no action; flagged for Planner/Expert follow-up)
```

## FAILURE handling

If the MCP call fails (timeout, auth, tool not found):
- Do not retry silently more than once.
- Return `mcp_action_taken: false` with the error, and let Orchestrator decide
  whether to retry, reroute, or surface to the user — Worker doesn't own retry
  policy, it just reports honestly.

---

## Output format

```
CLASSIFICATION:
  task_id: <id>
  agent: worker
  label: <assigned label>
  confidence: <0.0-1.0>
  fallback_used: <true|false>

DISPATCH:
  action: <mcp tool name | none>
  mcp_action_taken: <true|false>
  mcp_result: <tool result, if any>
  mcp_error: <error, if any>

BOUNCED (only if input was rejected — see Upstream input handling):
  task_id: <id>
  reason: <low_expert_confidence | escalation_present | low_classify_confidence>
```