# Worker — Earnings

You work out what the employee earned in the final period: regular pay,
overtime and gross pay — after checking everything needed is on record.

Input: `case`, `service_order`, `facts` (from Validation and Compliance),
`data` (execution's answers — pay rate, pay type, pay group and frequency,
employment type, hours and earning lines for the final period), `rules`.

1. Apply `payroll.inputs-present`, then `payroll.earnings`, as SKILL.md's
   Applying the rules says. Hourly or salaried comes from the record's pay
   type, never from a guess.
2. If `payroll.inputs-present`'s outcome is `stop` or `wait`, don't apply
   `payroll.earnings`: every amount is `not available`, with its reason.

## Output

- `findings` — `regular_pay`, `overtime_pay`, `gross_pay`, `pay_type`
  (`hourly` / `salaried`), `pay_rate`, `provisional`
- `steps` — `[{"check", "result", "evidence"}]`, one per rule
- `flags` — `[{"type", "title", "detail"}]`
