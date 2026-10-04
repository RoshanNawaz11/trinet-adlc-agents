# Case — <Name>

Copy this file to `cases/<case>.md` to add a case type. Only use checks from
`workers/checks.md`; if a rule can't be expressed with their settings, add a
check there first.

Where in the order the details are usually written: <description / fields>.

```yaml
case: <case>                  # lowercase, unique; matches the Planner's `work`
aliases: [<other names the Planner or orders use for this work>]
order_type: <service order caseType, used for duplicate checks>

extract:                      # beyond the universal fields (subject_name, subject_employee_id, work_state, special_instructions)
  - {name: <field>, type: <text | date | state | choice>}
  # choice fields also need: values: [...], rule: "<how to pick>"

checks:                       # universal checks run anyway; add the case's checks here
  subject_exists:   {must_exist: <true | false>}
  required_fields:
    fields: [<every field later agents can't work without>]
  # employment_status, date_order, field_equals, no_duplicate, pay_cycle as needed
```

## Reasoning sub-jobs

Only for what the checks can't decide (judgement over the order text).

| Sub-job | Passes when | Flag if not |
|---|---|---|
| <Subject> identified | <rule> | `missingData` |

## Case flags

- `<flag>` — `{<payload>}`

## Output fields (`output.cases.<case>`)

Same names as `extract`.

- `<field>` — <type>, or null
