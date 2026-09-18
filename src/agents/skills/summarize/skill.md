---
name: expert-summarize
description: >
  Use this skill when the Expert agent receives a "summarize" subtask from the
  Planner. Compresses raw/verbose input (task output, retrieved documents, prior
  agent chatter) into a structured summary with a confidence signal, and decides
  whether the result is safe to pass downstream or needs to bounce back to the
  Planner for re-scoping. Triggered by: subtask.type == "summarize", or any input
  routed to the Expert agent.
---

# SKILL: Expert Summarize (synthesis layer)
**Chain position:** orchestrator → planner → **expert** → worker
**Runs at:** whenever the Planner emits a subtask whose `type` requires judgment/
compression rather than a bounded decision. Expert is the *generative* half of the
pair — it decides what something means. It does not act on the world (that's Worker).

---

## Inputs required

1. `source_text` — the raw content to summarize (task output, doc chunk, transcript)
2. `task_id` — correlates the result back to the Planner's task graph
3. `constraints` (optional) — `max_points`, `target_length`, `audience` — set by the
   Planner if the subtask has downstream formatting requirements
4. `context` (optional) — prior summaries or task history, if this is a rollup of
   several Worker/Expert outputs rather than a single source

---

## SUMMARIZE phase

1. **Extract** — pull the core claim(s) from `source_text`. Do not introduce facts
   not present in the source (mirror the "never invent nodes beyond source data"
   rule from entity-job-kpi-mapper — same discipline applies to summarization).
2. **Compress** — produce:
   - a 2-3 sentence summary
   - up to `max_points` key points (default 4), each a single clause
3. **Self-score confidence** — not a vibe number. Score against three checks:
   - **Coverage**: does the summary account for every load-bearing sentence in the
     source, or did something get dropped silently?
   - **Compression ratio**: is `len(summary) / len(source_text)` in a sane band
     (roughly 0.05–0.3)? Below that, the summary is probably too thin to be useful;
     above it, it isn't actually a summary.
   - **Hallucination check**: does every noun/number in the summary trace back to
     the source? Any that don't → confidence drops hard, flag in output.

## ESCALATION phase

Expert does not silently guess when the source is ambiguous or contradictory. If:
- the source contains conflicting claims the summary can't reconcile without
  picking a side, or
- coverage confidence is below a working threshold (e.g. < 0.5), or
- `source_text` is empty, truncated, or clearly not what the subtask expected

→ do not fabricate a clean summary. Return an `escalation` block instead of (or
alongside) the summary, so the Planner can re-scope the subtask rather than the
Orchestrator silently forwarding a bad result to Worker.

```
ESCALATION:
  task_id: <id>
  reason: <conflicting_claims | low_coverage | malformed_input>
  detail: <what specifically is unresolved>
```

## Output format

```
SUMMARY:
  task_id: <id>
  agent: expert
  summary: "<2-3 sentence summary>"
  key_points:
    - <point 1>
    - <point 2>
  confidence: <0.0-1.0>
  confidence_breakdown:
    coverage: <0.0-1.0>
    compression_ratio: <float>
    hallucination_flags: [<any unsupported claims>]

ESCALATION (only if triggered — see above):
  task_id: <id>
  reason: <conflicting_claims | low_coverage | malformed_input>
  detail: <text>
```

Worker and Orchestrator should treat any result with `confidence < 0.5` or a
present `ESCALATION` block as **not safe to act on** — it routes back to Planner,
not forward to Worker.