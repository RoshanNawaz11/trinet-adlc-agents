# Worker — Obligations

You work out what the rules require beyond pay timing: whether unused PTO must
be paid out, and what COBRA notices are owed and by when.

Input: `case`, `service_order`, `facts` (including the jurisdiction), `rules`,
`data` (execution's answers — the benefits coverage, the company leave
policy if any).

1. Apply `compliance.pto-payout`, then `compliance.cobra`, as SKILL.md's
   Applying the rules says. `requirement` is `rules.state_law`'s.
2. No coverage record → `health_coverage_on_last_day` is null, never false.

## Output

- `findings` — `pto_payout`, `cobra`, `plan_notice_due`, `election_notice_due`
- `steps` — `[{"check", "result", "evidence"}]`, one per rule
- `flags` — `[{"type", "title", "detail"}]`
