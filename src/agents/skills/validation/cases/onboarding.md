# Case — Onboarding a new employee

A new hire has no employee or payroll record yet — creating them is what
onboarding does. So the order is the source: the new hire's details (name,
start date, job, pay) are written in the order's description.

```yaml
case: onboarding
aliases: [onboarding, new hire, hire, new employee]
order_type: Onboarding

extract:                      # beyond the universal fields (subject_name, subject_employee_id, work_state, special_instructions)
  - {name: start_date,      type: date}
  - {name: job_title,       type: text}
  - {name: employment_type, type: text}
  - {name: pay_group,       type: text}
  - {name: pay_rate,        type: rate}   # e.g. "$38.00/hour" → {amount: 38.0, basis: hour}

checks:
  subject_exists:    {must_exist: false}
  employment_status: {forbidden: [Active], flag: alreadyActive}
  required_fields:
    fields: [subject_name, start_date, work_state, job_title, employment_type, pay_group, pay_rate]
  date_order:
    rule: [order.created_date, "<=", start_date]
  no_duplicate:      {order_type: Onboarding, match_on: subject_name}
```

`match_on: subject_name` because a new hire often has no employee id yet.
No employee record for the new hire is expected, not missing — never flag it.

## Reasoning sub-jobs

| Sub-job | Passes when | Flag if not |
|---|---|---|
| New hire identified | the order names the new hire (not `assignedTo`; a record may not exist yet) | `missingData` (`subject_name`) |

## Case flags

- `alreadyActive` — `{"employee_id": <id>, "status": <status>}`

## Output fields (`output.cases.onboarding`)

Same names as `extract`, so Compliance and Payroll read one name per fact.

- `subject_employee_id`, `subject_name` — or null
- `work_state` — two-letter state, or null
- `start_date` — ISO date, or null
- `job_title`, `employment_type`, `pay_group` — or null
- `pay_rate` — `{"amount": <number>, "basis": "hour" | "year" | "period"}`, or null
