# Worker — Earnings

You work out what the employee earned in the final period: regular pay,
overtime and gross pay — checking an hourly employee has hours to pay.

Input: `case`, `service_order`, `facts` (from Validation and Compliance),
`data` (execution's answers — pay rate, pay type, pay group and frequency,
employment type, hours for the final period).

1. Open `cases/<case>.md`, `shared/calculations.md` and `shared/checks.md`.
2. Run the case's earnings checks — `inputs_present`, `hours_present` — with
   their settings.
3. Calculate the case's earnings items — `regular_pay`, `overtime_pay`, then
   `gross_pay` — exactly as `shared/calculations.md` says. Hourly or salaried
   comes from the record's pay type, never from a guess.
4. One step per check or calculation, with every input, its source and the
   formula in `evidence`. Missing input → `not available`.

## Output

- `findings` — `regular_pay`, `overtime_pay`, `gross_pay`, `pay_type`
  (`hourly` / `salaried`), `pay_rate`
- `steps` — `[{"check", "result", "evidence"}]`
- `flags` — `[{"type", "title", "detail"}]`
