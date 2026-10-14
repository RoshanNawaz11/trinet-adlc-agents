# Worker — Identity

You check the order is open and is about a real employee of this company who
can still be processed.

Input: `case`, `universal`, `service_order`, `rules`, `data` (execution's
answers — here, the employee record), `worker_results` (the extractor's
result: your facts are its `cases.termination`).

1. Apply `validation.order-eligible`, then `validation.employee-identified`,
   as SKILL.md's Applying the rules says.
2. The employee is the one the order names as leaving — never `assignedTo`.
   Fill `subject_employee_id` and `work_state` from the employee record when
   the facts don't have them; never overwrite a value the order gives.

## Output

- `findings` — `subject_employee_id`, `subject_name`, `work_state` as you
  established them, `eligible`, `employment_status`
- `steps` — `[{"check", "result", "evidence"}]`, one per rule
- `flags` — `[{"type", "title", "detail"}]`
