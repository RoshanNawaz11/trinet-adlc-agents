# Case — Termination / offboarding

The rules that decide when final pay is legally due, whether unused PTO must be
paid out, and whether the regular payroll would pay in time.

```yaml
case: termination
aliases: [offboarding, termination, separation]

facts:                        # from validation (previous_results.validation.cases.termination)
  - subject_employee_id
  - work_state
  - termination_type          # voluntary | involuntary
  - notice_given              # yes | no | unknown — matters for voluntary terminations
  - termination_date
  - last_day_worked
  - pay_cycle

rules:                        # ask execution, never from memory
  - {name: final_pay,  keys: [work_state, termination_type, notice_given]}
  - {name: pto_payout, keys: [work_state]}
  - {name: pay_calendar, keys: [subject_employee_id]}    # the employee's regular paydays

checks:
  facts_present:  {fields: [work_state, termination_type, termination_date]}
  rule_found:     {rule: final_pay, keys: [work_state, termination_type]}
  deadline:       {rule: final_pay, from: termination_date, output: final_pay_due_date}
  standard_payday:
    deadline:     {rule: pay_calendar, from: last_day_worked, output: standard_pay_date}
  deadline_met:   {deadline: final_pay_due_date, by: standard_pay_date, flag: complianceTiming}
  requirement:    {rule: pto_payout, output: pto_payout}
```

If the regular payday is later than the legal due date, final pay must run
off-cycle — `complianceTiming` tells Payroll and the reviewer so.

## Case flags

None beyond the common flags.

## Output fields (`output.cases.termination`)

- `work_state` — two-letter state, or null
- `termination_type` — `voluntary`, `involuntary` or `unknown`
- `final_pay_rule` — the rule applied, with its source, or null
- `final_pay_due_date` — ISO date, or null
- `standard_pay_date` — ISO date, or null
- `pay_timing` — `on-cycle`, `off-cycle` or `unknown`
- `pto_payout` — `required`, `policy`, `not_required` or `unknown`
