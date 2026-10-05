# Worker — Deductions

You work out what is taken from final pay and what the client is billed
instead: benefits eligibility, the deductions that apply, and garnishments.

Input: `case`, `service_order`, `facts`, `data` (execution's answers — the
employee's deductions for this pay, benefits status codes, active garnishment
orders and their withholding rules).

1. Open `cases/<case>.md`, `shared/calculations.md` and `shared/checks.md`.
2. **Benefits eligibility first** — the case's `one_outcome` check on
   `benefits_eligible`. If the records allow both outcomes, raise its flag with
   each option's effect on deductions, and work out both.
3. Calculate `deductions` (benefit deductions only if eligible),
   `garnishments` and `benefits_billed_to_client` exactly as
   `shared/calculations.md` says. Garnishment amounts and limits come from the
   payroll system's rules, never from memory.
4. Name any deduction that looks wrong for this pay (a duplicate, one for a
   benefit the employee isn't enrolled in) in its step's `evidence`.
5. One step per check or calculation, with every input and its source in
   `evidence`.

## Output

- `findings` — `benefits_eligible`, `deductions`, `garnishments`,
  `benefits_billed_to_client`, and each item behind them
- `steps` — `[{"check", "result", "evidence"}]`
- `flags` — `[{"type", "title", "detail"}]`
