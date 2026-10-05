# Worker — Obligations

You work out what the rules require beyond pay timing: whether unused PTO must
be paid out, and what COBRA notices are owed and by when.

Input: `case`, `service_order`, `facts` (including the jurisdiction), `data`
(execution's answers — the PTO rule, the COBRA rules, federal and any state,
and the benefits coverage).

1. Open `cases/<case>.md` and `shared/checks.md`.
2. Run the case's obligation checks from its `checks:` — `requirement`,
   `obligation` — with their settings.
3. For an `obligation`, decide its `when` condition from the records (e.g.
   COBRA applies only if the employee had health coverage). No record →
   `not available`, not `not_applicable`.
4. One step per check, with the rule and the facts in `evidence`. A check whose
   rule or record is missing is `not available`.

## Output

- `findings` — the fields your checks write (`output:` settings), e.g.
  `pto_payout`, `cobra`, and the rules applied with their source
- `steps` — `[{"check", "result", "evidence"}]`
- `flags` — `[{"type", "title", "detail"}]`
