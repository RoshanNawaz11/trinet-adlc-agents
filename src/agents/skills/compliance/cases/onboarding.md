# Case — Onboarding a new employee

The rules that set deadlines when a new employee starts: employment
eligibility verification (Form I-9) and state new-hire reporting.

```yaml
case: onboarding
aliases: [onboarding, new hire, hire, new employee]

facts:                        # from validation (previous_results.validation.cases.onboarding)
  - subject_name
  - work_state
  - start_date

rules:                        # ask execution, never from memory
  - {name: i9_verification,    keys: []}            # federal
  - {name: new_hire_reporting, keys: [work_state]}

facts_needed_for_status:      # ask validation or execution; unknown is fine
  - i9_completed_date
  - new_hire_reported_date

checks:
  facts_present:  {fields: [subject_name, work_state, start_date]}
  rule_found:     {rule: i9_verification, keys: []}
  i9_deadline:
    deadline:     {rule: i9_verification, from: start_date, output: i9_due_date}
  i9_on_time:
    deadline_met: {deadline: i9_due_date, by: i9_completed_date, flag: complianceTiming}
  reporting_deadline:
    deadline:     {rule: new_hire_reporting, from: start_date, output: new_hire_report_due_date}
  reporting_on_time:
    deadline_met: {deadline: new_hire_report_due_date, by: new_hire_reported_date, flag: complianceTiming}
```

A `deadline_met` check whose completed date is unknown is `not available` — the
work may simply not be done yet. Report the deadline so Execution and the
reviewer know when it falls.

## Case flags

None beyond the common flags.

## Output fields (`output.cases.onboarding`)

- `work_state` — two-letter state, or null
- `start_date` — ISO date, or null
- `i9_rule`, `new_hire_reporting_rule` — the rules applied, with their source, or null
- `i9_due_date` — ISO date, or null
- `new_hire_report_due_date` — ISO date, or null
