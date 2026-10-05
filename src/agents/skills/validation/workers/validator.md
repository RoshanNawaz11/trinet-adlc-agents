# Worker — Validator

You check the facts later stages need are all there, make sense together, agree
with the records, and don't clash with other orders or the pay calendar.

Input: `case`, `service_order`, `data` (execution's answers — the employee
record, open service orders, the pay calendar), `worker_results` (the
extractor's result: your facts are its `cases.<case>`).

1. Open `cases/<case>.md` and `shared/checks.md`.
2. Fill `subject_employee_id` and `work_state` from the employee record when
   the facts don't have them (see `shared/checks.md`, Before checking).
3. Run `sources_agree` — every case, whenever there is an employee record.
4. Run the case's validator checks from its `checks:` — `required_fields`,
   `date_order`, `no_duplicate`, `pay_cycle` — with their settings.
5. One step per check. A failed check raises its flag; a check whose inputs
   are missing is `not available`.

## Output

- `findings` — `missing_fields` (the fields `required_fields` found missing,
  empty when none), and `pay_cycle` when the case runs that check
- `steps` — `[{"check", "result", "evidence"}]`
- `flags` — `[{"type", "title", "detail"}]`
