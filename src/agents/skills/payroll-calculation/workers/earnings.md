# Worker — Earnings

You work out what the employee earned in the final period: regular pay,
overtime and gross pay — after checking everything needed is on record —
and check the employee is out of the regular payroll runs, so final pay
isn't paid twice.

Input: `case`, `service_order`, `facts` (from Validation and Compliance),
`data` (execution's answers — pay rate, pay type, pay group and frequency,
employment type, hours and earning lines for the final period, the regular
payroll runs that still include the employee), `rules`.

1. Apply `payroll.inputs-present`, then `payroll.earnings`, as SKILL.md's
   Applying the rules says. Hourly or salaried comes from the record's pay
   type, never from a guess.
2. If `payroll.inputs-present`'s outcome is `stop` or `wait`, don't apply
   `payroll.earnings`: every amount is `not available`, with its reason.
3. Apply `payroll.on-cycle-removed` in every case. `regular_runs_found` is
   false when the runs are missing from `data` or their need failed — never
   "already removed".

## Output

- `findings` — `regular_pay`, `overtime_pay`, `gross_pay`, `pay_type`
  (`hourly` / `salaried`), `pay_rate`, `provisional`, `runs_to_remove`
- `steps` — `[{"check", "result", "evidence"}]`, one per rule
- `flags` — `[{"type", "title", "detail"}]`
