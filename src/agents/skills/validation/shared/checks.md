# Checks

Every check a case can use, what its settings mean, which worker runs it, and
when it passes. A case file only names checks from this list. A check whose
inputs are missing is `not available` — it does not fail, and it raises no
flag of its own (the missing field is caught by `required_fields`).

The records are in `data`: execution's answers (employee record, open service
orders, pay calendar), each with its `request` and `answer`. A record that
wasn't asked for, or whose need failed, isn't there. The facts are the
extractor's, in `worker_results`.

## Before checking

Fill `subject_employee_id` and `work_state` from the employee record when
the facts don't have them (work state: the two-letter state at the end of the
record's `location`). Never overwrite a value the order gives — if the order
and the record disagree, that is for `sources_agree`.

## Universal checks — `identity` runs them when `universal` is true

| Check | Passes when | Flag if not |
|---|---|---|
| `order_open` | the order's status is not Closed or Cancelled | `orderNotOpen` |
| `subject_identified` | `subject_name` or `subject_employee_id` was extracted | `missingData` (`subject_name`) |
| `company_match` | when the subject has an employee record: its company is the order's company | `employeeMismatch` |

## Always run by `validator` (when there is an employee record)

| Check | Passes when | Flag if not |
|---|---|---|
| `sources_agree` | every fact the order states that the record also holds (name, id, work state, hire date) matches it | `recordMismatch`, one per field |

## Checks a case can add

| Check | Worker | Settings | Passes when | Flag if not |
|---|---|---|---|---|
| `subject_exists` | identity | `must_exist: true \| false` | `true`: a record for the subject exists in `data`. `false`: a record may or may not exist (e.g. a new hire) | `missingData` (`subject_employee_id`) |
| `employment_status` | identity | `forbidden: [<statuses>]`, `flag` | the subject's record status is not in `forbidden` | the case's `flag` |
| `field_equals` | identity | `field`, `expected`, `flag`, `unknown_is: fail \| pass` | the field equals `expected`; `unknown` follows `unknown_is` | the case's `flag` |
| `required_fields` | validator | `fields: [...]` | every listed field has a value in the right format (see the extractor's types); `null` or `unknown` counts as missing | one `missingData` listing every missing field |
| `date_order` | validator | `rule: [a, op, b, op, c, ...]` | every comparison holds (`<`, `<=`). Names starting `order.` are service-order fields, `record.` are employee-record fields, others are extracted fields | `invalidDates` |
| `no_duplicate` | validator | `order_type`, `match_on` | no other **open** service order with this `caseType` for the same subject (matched on `match_on`) | `duplicateSO` |
| `pay_cycle` | validator | `date_field` | always reports: `off-cycle` when that date is before the current pay run, `on-cycle` otherwise, `unknown` without a pay calendar | — |

Run only your own checks. A worker with nothing to run returns empty `steps`.

## Universal flags

- `missingData` — `{"missing": [<field names>]}`
- `orderNotOpen` — `{"status": <status>}`
- `employeeMismatch` — `{"employee_company": <id>, "order_company": <id>}`
- `recordMismatch` — `{"field": <name>, "order": <value>, "record": <value>}`
- `invalidDates` — `{"rule": <the rule>, "values": {<field>: <date>}}`
- `duplicateSO` — `{"this_order": <id>, "other_order": <id>}`

Raise each problem once, with one flag per failed check.
