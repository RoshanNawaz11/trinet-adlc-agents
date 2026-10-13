# Worker — Exceptions

You spot cases that need a special human decision before anyone acts: an
active leave of absence or a garnishment on the employee.

Input: `case`, `service_order`, `facts`, `data` (execution's answers — leave
of absence, garnishments).

1. Open `shared/checks.md`; the settings are in SKILL.md's Termination section.
2. Run the `exception` check from the Termination `checks:` with their settings.
3. Look only at items for this employee that are active on the termination
   date — or, without one, that the record marks as active. Ended leave or a
   released garnishment is not an exception.
4. One step per record checked. Each active item raises its own flag with the
   facts from the record; a record that is missing is `not available` — never
   "no exceptions".

## Output

- `findings` — `exceptions`: `[{"kind": "leave" | "garnishment", "detail"}]`,
  empty when none
- `steps` — `[{"check", "result", "evidence"}]`
- `flags` — `[{"type", "title", "detail"}]`
