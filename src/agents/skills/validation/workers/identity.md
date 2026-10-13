# Worker — Identity

You check the order is open and is about a real employee of this company who
can still be processed.

Input: `case`, `universal`, `service_order`, `data` (execution's answers —
here, the employee record), `worker_results` (the extractor's result: your
facts are its `cases.termination`).

1. Open `shared/checks.md`; the settings are in SKILL.md's Termination section.
2. Fill `subject_employee_id` and `work_state` from the employee record when
   the facts don't have them (see `shared/checks.md`, Before checking).
3. If `universal` is true, run the universal checks: `order_open`,
   `subject_identified`, `company_match`.
4. Run the identity checks from the Termination `checks:` — `subject_exists`,
   `employment_status` — with their settings.
5. Run the reasoning sub-job "Terminated employee identified".
6. One step per check or sub-job. A failed check raises its flag; a check whose
   inputs are missing is `not available`.

## Output

- `findings` — `subject_employee_id`, `subject_name`, `work_state` as you
  established them
- `steps` — `[{"check", "result", "evidence"}]`
- `flags` — `[{"type", "title", "detail"}]`
