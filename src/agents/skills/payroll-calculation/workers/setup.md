# Worker — Setup

Onboarding only. You work out the new employee's pay setup: when they are first
paid, and what they still have to provide.

Input: `case`, `service_order`, `facts` (from Validation: start date, pay
group, pay rate, …), `data` (execution's answers — the pay group's pay
calendar).

1. Open `cases/<case>.md`, `shared/calculations.md` and `shared/checks.md`.
2. Run the case's setup checks — `inputs_present`, `setup_complete` — with
   their settings.
3. Calculate `first_pay_date` exactly as `shared/calculations.md` says.
4. List what the new hire still has to provide (tax forms, payment method) —
   that is the onboarding to-do list, not a problem: never flag it.
5. One step per check or calculation, with every input in `evidence`.

## Output

- `findings` — `first_pay_date`, `pay_group`, `pay_frequency`, `pay_rate`,
  `setup_to_collect`
- `steps` — `[{"check", "result", "evidence"}]`
- `flags` — `[{"type", "title", "detail"}]`
