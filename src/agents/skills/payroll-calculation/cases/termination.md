# Case — Termination / offboarding

The employee's final paycheck: wages up to the last day worked, any leave
payout, taxes and deductions — checked against the payroll system's own figure.

```yaml
case: termination
aliases: [offboarding, termination, separation]

inputs:
  from_validation:            # previous_results.validation.cases.termination
    - subject_employee_id
    - last_day_worked
    - termination_type
    - pay_cycle
  from_compliance:            # previous_results.compliance.cases.termination
    - final_pay_due_date
    - pto_payout
  from_execution:             # pay data — ask execution
    - pay rate, pay group and frequency, employment type
    - regular and overtime hours for the final period
    - unused leave hours
    - withholding and deductions for this pay
    - the payroll system's net pay for this pay
    - payment method on file

calculate: [regular_pay, overtime_pay, gross_pay, leave_payout, taxes, deductions, net_pay]

checks:
  inputs_present:        {fields: [subject_employee_id, last_day_worked, pay_rate, final_pay_due_date]}
  benefits:
    one_outcome:         {field: benefits_eligible, flag: benefitsAmbiguous}
  matches_system:        {field: net_pay, system_field: system_net_pay, tolerance: 0.01, flag: netPayMismatch}
  payment_method_usable: {flag: paymentMethodFail}
```

Benefits eligibility: regular employees are eligible, temporary employees are
not; when the employee's status codes allow both, it's `benefitsAmbiguous`.

## Case flags

- `benefitsAmbiguous` — `{"option_a": {"label", "net_pay"}, "option_b": {"label", "net_pay"}}`; its `recommendation` names the option the employee's records support best, and why
- `netPayMismatch` — `{"system_net_pay", "calculated_net_pay", "explanation"}`
- `paymentMethodFail` — `{"current_method", "reason", "recommended_method"}`

## Output fields (`output.cases.termination`)

- `regular_pay`, `overtime_pay`, `gross_pay`, `leave_payout`, `taxes`, `deductions`, `net_pay` — USD, or null
- `system_net_pay` — the payroll system's figure, or null
- `benefits_eligible` — true, false, or null
- `payment_method` — `direct_deposit` or `check`, or null
- `pay_date` — the final-pay due date from Compliance, or null
