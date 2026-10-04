# Worker — Extractor

Pulls facts out of the service order (name, description, tags) and the records
in `data`. It reads; it never decides whether a fact is good enough — the
checks do that.

## Universal fields — extract these for every case

| Field | Type | How |
|---|---|---|
| `subject_name` | text | the employee the order is about, as named in the order — never `assignedTo`, who is the TriNet specialist handling it |
| `subject_employee_id` | text | that employee's id, from the order or a matching record in `data`; null if none |
| `work_state` | state | the state the employee works in, as stated in the order or the employee record; null if not stated — don't infer it from a city in another field |
| `special_instructions` | text | delivery or handling instructions in the order; `none` when there are none |

Then extract each case's `extract` fields.

## Types

| Type | Write it as |
|---|---|
| `text` | as written in the order; null if absent |
| `date` | ISO `YYYY-MM-DD`; null if absent or not a real date |
| `state` | two-letter US state code; null if absent |
| `choice` | exactly one of the field's `values`, following its `rule`; `unknown` when the order doesn't say |

## Rules

- Only facts written in the order or the records. Never guess, and never fill a
  field from a similar-looking one (e.g. the specialist's hire date is not the
  subject's).
- For every field you fill, keep the words it came from as evidence.
