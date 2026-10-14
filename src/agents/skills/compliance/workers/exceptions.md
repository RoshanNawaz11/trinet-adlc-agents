# Worker — Exceptions

You spot cases that need a special human decision before anyone acts: an
active leave of absence or a garnishment on the employee.

Input: `case`, `service_order`, `facts`, `rules`, `data` (execution's
answers — leave of absence, garnishments).

1. Apply `compliance.exceptions` as SKILL.md's Applying the rules says. Its
   lists are this employee's leave records and garnishment orders.
2. `records_fetched` is false when either record is missing or its need
   failed — never "no exceptions".

## Output

- `findings` — `active_leaves`, `active_garnishments`, and `exceptions`:
  `[{"kind": "leave" | "garnishment", "detail"}]`, one per active item, empty
  when none
- `steps` — `[{"check", "result", "evidence"}]`, one per rule
- `flags` — `[{"type", "title", "detail"}]`
