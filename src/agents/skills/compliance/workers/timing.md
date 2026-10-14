# Worker — Timing

You turn the rules into actual deadlines and check payroll can meet them: when
pay is legally due, when it would go out normally, whether that is too late,
and whether there is still time before the payroll and bank cut-offs.

Input: `case`, `service_order`, `facts` (including the jurisdiction), `today`,
`rules`, `data` (execution's answers — the pay calendar, the cut-offs).

1. Apply `compliance.rule-applies`, then `compliance.final-pay`, then
   `compliance.submit-by`, as SKILL.md's Applying the rules says. Each uses
   the earlier ones' outputs (`state_rule_found`, `final_pay_due_date`,
   `overdue`).
2. `regular_payday` and `period_end` come from the pay calendar: the pay
   period containing the last day worked. `now` is `today` unless a record
   gives the time.
3. For a deadline, put the `due` form, its amount, the from-date and the
   resulting date in the step's `evidence`.

## Output

- `findings` — `state_rule_found`, `final_pay_due_date`, `standard_pay_date`
  (the rule's `regular_payday`), `pay_timing`, `overdue`, `allowed_methods`,
  `death_payee`, `final_pay_rule` (`due_text`), `submit_by`, `set_by`
- `steps` — `[{"check", "result", "evidence"}]`, one per rule
- `flags` — `[{"type", "title", "detail"}]`
