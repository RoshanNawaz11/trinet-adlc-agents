# Case — Onboarding a new employee

The new employee's pay setup: pay group, rate and first payday. A new hire has
no payroll record yet — their pay terms come from the order (through
Validation), and the items only they can provide (tax forms, payment method)
are collected during onboarding. Those items are the onboarding to-do list,
not a problem: report them, never flag them.

```yaml
case: onboarding
aliases: [onboarding, new hire, hire, new employee]

workers: [setup]

inputs:
  from_validation:            # previous_results.validation.cases.onboarding
    - subject_name
    - subject_employee_id     # null for a new hire
    - start_date
    - work_state
    - employment_type
    - pay_group
    - pay_rate                # from the order
  from_execution:             # pay data — ask execution
    - pay calendar for the pay group

calculate: [first_pay_date]

checks:
  inputs_present:  {fields: [subject_name, start_date, pay_group, pay_rate]}
```

Don't ask for the new hire's payroll record, tax forms or payment method —
they don't exist yet. List them in `setup_to_collect`.

## Case flags

None beyond the common flags.

## Output fields (`output.cases.onboarding`)

- `pay_group`, `pay_frequency` — or null
- `pay_rate` — `{"amount", "basis"}` as Validation gave it, or null
- `first_pay_date` — ISO date, or null
- `setup_to_collect` — what the new hire still has to provide, e.g.
  `["federal W-4", "state withholding form", "payment method"]`
