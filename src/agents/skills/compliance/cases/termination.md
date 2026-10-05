# Case — Termination / offboarding

The rules that decide when final pay is legally due, whether unused PTO must be
paid out, whether the regular payroll would pay in time, what COBRA requires,
and whether anything needs a special human decision.

```yaml
case: termination
aliases: [offboarding, termination, separation]

workers: [timing, obligations, exceptions]

facts:                        # from validation (previous_results.validation.cases.termination)
  - subject_employee_id
  - work_state
  - termination_type          # voluntary | involuntary
  - notice_given              # yes | no | unknown — matters for voluntary terminations
  - termination_date
  - last_day_worked
  - pay_cycle

rules:                        # ask execution, never from memory
  - {name: final_pay,    keys: [jurisdiction, termination_type, notice_given]}
  - {name: pto_payout,   keys: [jurisdiction]}
  - {name: cobra,        keys: [jurisdiction]}                # federal + any state continuation rule
  - {name: pay_calendar, keys: [subject_employee_id]}         # the employee's regular paydays

records:                      # ask execution
  - {name: payroll_cutoffs,   keys: [subject_employee_id]}    # payroll and bank cut-offs, with `as_of`
  - {name: benefits_coverage, keys: [subject_employee_id]}    # health coverage on the last day worked
  - {name: leave_of_absence,  keys: [subject_employee_id]}
  - {name: garnishments,      keys: [subject_employee_id]}

checks:
  # timing
  facts_present:  {fields: [work_state, termination_type, termination_date]}
  rule_found:     {rule: final_pay, keys: [jurisdiction, termination_type]}
  deadline:       {rule: final_pay, from: termination_date, output: final_pay_due_date}
  standard_payday:
    deadline:     {rule: pay_calendar, from: last_day_worked, output: standard_pay_date}
  deadline_met:   {deadline: final_pay_due_date, by: standard_pay_date, flag: complianceTiming}
  cutoff:         {pay_by: final_pay_due_date, cutoffs: payroll_cutoffs, output: submit_by, flag: cutoffRisk}
  # obligations
  requirement:    {rule: pto_payout, output: pto_payout}
  obligation:     {when: "benefits_coverage shows health coverage", rule: cobra, output: cobra}
  # exceptions
  exception:      {records: [leave_of_absence, garnishments], flag: complianceException}
```

If the regular payday is later than the legal due date, final pay must run
off-cycle — `complianceTiming` tells Payroll and the reviewer so.

## Case flags

None beyond the common flags.

## Output fields (`output.cases.termination`)

- `work_state` — two-letter state, or null
- `jurisdiction` — `{"state": <code>, "local": <name or null>}`, or null
- `termination_type` — `voluntary`, `involuntary` or `unknown`
- `final_pay_rule` — the rule applied, with its source, or null
- `final_pay_due_date` — ISO date, or null
- `standard_pay_date` — ISO date, or null
- `pay_timing` — `on-cycle`, `off-cycle` or `unknown`
- `submit_by` — the latest time to submit final pay and still meet the due
  date, or null
- `pto_payout` — `required`, `policy`, `not_required` or `unknown`
- `cobra` — `{"required": true | false, "notices": [{"notice", "due_date", "rule"}]}`,
  `not_applicable` without coverage, or `unknown`
- `exceptions` — `[{"kind": "leave" | "garnishment", "detail"}]`, empty when none
