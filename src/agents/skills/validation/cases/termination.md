# Case — Termination / offboarding

The termination details (who, termination date, reason, last day worked, work
state, notice given) are usually written in the order's description.

```yaml
case: termination
aliases: [offboarding, termination, separation]
order_type: Offboarding

extract:                      # beyond the universal fields (subject_name, subject_employee_id, work_state, special_instructions)
  - {name: termination_date,        type: date}
  - {name: last_day_worked,         type: date}
  - {name: termination_reason_text, type: text}
  - name: termination_type
    type: choice
    values: [voluntary, involuntary, unknown]
    rule: "resigned, quit, retired → voluntary; fired, laid off, let go, terminated for cause → involuntary; otherwise unknown"
  - name: notice_given
    type: choice
    values: [yes, no, unknown]
    rule: "yes only if the order says notice was given; no only if it says none was given"

checks:
  subject_exists:    {must_exist: true}
  employment_status: {forbidden: [Terminated], flag: alreadyTerminated}
  required_fields:
    fields: [subject_employee_id, termination_date, last_day_worked, work_state, termination_type]
  date_order:
    rule: [record.hire_date, "<", last_day_worked, "<=", termination_date]
  no_duplicate:      {order_type: Offboarding, match_on: subject_employee_id}
  pay_cycle:         {date_field: last_day_worked}
```

`termination_type: unknown` counts as missing for `required_fields`.

## Reasoning sub-jobs

| Sub-job | Passes when | Flag if not |
|---|---|---|
| Terminated employee identified | the order names the employee leaving (not `assignedTo`), and the id matches a record | `missingData` (`subject_employee_id`) |

## Case flags

- `alreadyTerminated` — `{"employee_id": <id>, "status": <status>}`

## Output fields (`output.cases.termination`)

Same names as `extract`, so Compliance and Payroll read one name per fact.

- `subject_employee_id`, `subject_name` — or null
- `work_state` — two-letter state, or null
- `termination_date`, `last_day_worked` — ISO dates, or null
- `termination_type` — `voluntary`, `involuntary` or `unknown`
- `termination_reason_text` — as written in the order, or null
- `notice_given` — `yes`, `no` or `unknown`
- `pay_cycle` — `on-cycle`, `off-cycle` or `unknown`
