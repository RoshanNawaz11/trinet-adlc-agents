# Worker — Checks

Every check a compliance case can use, what its settings mean, and when it
passes. A case file only names checks from this list. A check whose facts or
rule are missing is `not available` — it does not fail.

## Rules

A rule comes from `data` or an answer from `execution` — never from memory.
Record for each one: what it covers, the jurisdiction, its text, and its source.
When asking `execution`, name the topic and the facts that pick the rule, e.g.
"final-pay rule for OR, involuntary termination".

Deadline rules usually take one of these forms; apply them exactly:

| Form | Deadline |
|---|---|
| immediately / same day | the from-date itself |
| next business day | the next Monday–Friday after the from-date |
| N calendar days | from-date + N days |
| N business days | from-date + N Monday–Friday days |
| next regular payday | the next payday in the employee's pay calendar after the from-date |

If a rule's wording doesn't fit one form clearly, the deadline is `not available`.

## Checks a case can use

| Check | Settings | Passes when | Flag if not |
|---|---|---|---|
| `facts_present` | `fields: [...]` | every listed fact is known; `null` or `unknown` counts as missing | `missingData` — unless Validation already flagged the same fields |
| `rule_found` | `rule`, `keys: [...]` | an approved rule for that topic and those facts was found | `missingData` (`rule: <topic>`) |
| `deadline` | `rule`, `from`, `output` | always computes: applies the rule to the `from` date and writes the date to `output`; `not available` if either is missing | — |
| `deadline_met` | `deadline`, `by`, `flag` | the date in `by` is on or before the `deadline` | the case's `flag` |
| `requirement` | `rule`, `output` | always reports what the rule requires (e.g. pay out unused PTO: `required` / `policy` / `not_required`) | — |
| `obligation` | `when`, `rule`, `output` | when the condition holds, reports the obligation the rule creates and its deadline; `not_applicable` otherwise | — |

## Common flags

- `missingData` — `{"missing": [<facts or rules>]}`
- `complianceTiming` — `{"rule": <text>, "required_by": <date>, "planned": <date>}`

Raise each problem once, even if several cases hit it.
