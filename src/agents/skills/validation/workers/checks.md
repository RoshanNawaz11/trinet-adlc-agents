# Worker — Checks

Every check a case can use, what its settings mean, and when it passes. A case
file only names checks from this list. A check whose inputs are missing is
`not available` — it does not fail, and it raises no flag of its own (the
missing field is caught by `required_fields`).

## Universal checks — run once for every order

| Check | Passes when | Flag if not |
|---|---|---|
| `order_open` | the order's status is not Closed or Cancelled | `orderNotOpen` |
| `subject_identified` | `subject_name` or `subject_employee_id` was extracted | `missingData` (`subject_name`) |
| `company_match` | when the subject has an employee record: its company is the order's company | `employeeMismatch` |

## Checks a case can add

| Check | Settings | Passes when | Flag if not |
|---|---|---|---|
| `subject_exists` | `must_exist: true \| false` | `true`: a record for the subject exists in `data`. `false`: a record may or may not exist (e.g. a new hire) | `missingData` (`subject_employee_id`) |
| `employment_status` | `forbidden: [<statuses>]`, `flag` | the subject's record status is not in `forbidden` | the case's `flag` |
| `required_fields` | `fields: [...]` | every listed field has a value; `null` or `unknown` counts as missing | one `missingData` listing every missing field |
| `field_equals` | `field`, `expected`, `flag`, `unknown_is: fail \| pass` | the field equals `expected`; `unknown` follows `unknown_is` | the case's `flag` |
| `date_order` | `rule: [a, op, b, op, c, ...]` | every comparison holds (`<`, `<=`). Names starting `order.` are service-order fields, `record.` are employee-record fields, others are extracted fields | `invalidDates` |
| `no_duplicate` | `order_type`, `match_on` | no other **open** service order with this `caseType` for the same subject (matched on `match_on`) | `duplicateSO` |
| `pay_cycle` | `date_field` | always reports: `off-cycle` when that date is before the current pay run, `on-cycle` otherwise, `unknown` without a pay calendar | — |

## Universal flags

- `missingData` — `{"missing": [<field names>]}`
- `orderNotOpen` — `{"status": <status>}`
- `employeeMismatch` — `{"employee_company": <id>, "order_company": <id>}`
- `invalidDates` — `{"rule": <the rule>, "values": {<field>: <date>}}`
- `duplicateSO` — `{"this_order": <id>, "other_order": <id>}`

Raise each problem once, even if several cases hit it.
