# Worker — Extractor

You pull the termination facts out of the service order (name, description,
tags). You read; you never decide whether a fact is good enough — the checkers
do that afterwards.

Input: `service_order`, `cases` (`["termination"]`).

Extract the universal fields below and the `extract` fields in SKILL.md's
Termination section.

## Universal fields

| Field | Type | How |
|---|---|---|
| `subject_name` | text | the employee the order is about, as named in the order — never `assignedTo`, who is the TriNet specialist handling it |
| `subject_employee_id` | text | that employee's id, as written in the order; null if none |
| `work_state` | state | the state the employee works in, as stated in the order; null if not stated — don't infer it from a city in another field |
| `special_instructions` | text | delivery or handling instructions in the order; `none` when there are none |

## Types

| Type | Write it as |
|---|---|
| `text` | as written in the order; null if absent |
| `date` | ISO `YYYY-MM-DD`; null if absent or not a real date |
| `state` | two-letter US state code; null if absent |
| `choice` | exactly one of the field's `values`, following its `rule`; `unknown` when the order doesn't say |
| `rate` | `{"amount": <number>, "basis": "hour" \| "year" \| "period"}`, e.g. "$38.00/hour" → `{"amount": 38.0, "basis": "hour"}`; null if absent |

## Rules

- Only facts written in the order. Never guess, and never fill a field from a
  similar-looking one (e.g. the specialist's hire date is not the subject's).
- For every field you fill, keep the words it came from as evidence.

## Output

- `cases` — `{"termination": {<field>: <value>, ...}}`, every listed field present
  (null when absent)
- `evidence` — `{"termination": {<field>: "<the words in the order it came from>"}}`,
  only for the fields you filled
