# Checks

Every check a compliance case can use, what its settings mean, which worker
runs it, and when it passes. A case file only names checks from this list. A
check whose facts, rule or record is missing is `not available` — it does not
fail.

## Rules and records

A rule comes from `execution` (in `data`) — never from memory. Record for
each one: what it covers, the jurisdiction, its text, and its source. Records
(cut-offs, benefits coverage, leave, garnishments) come from `execution` too,
in `data`. A rule or record that wasn't asked for, or whose need failed, isn't
there.

Deadline rules usually take one of these forms; apply them exactly, and show
the from-date, the form and the result in `evidence`:

| Form | Deadline |
|---|---|
| immediately / same day | the from-date itself |
| next business day | the next Monday–Friday after the from-date |
| N calendar days | from-date + N days |
| N business days | from-date + N Monday–Friday days |
| next regular payday | the next payday in the employee's pay calendar after the from-date |

If a rule's wording doesn't fit one form clearly, the deadline is `not available`.

## Checks a case can use

| Check | Worker | Settings | Passes when | Flag if not |
|---|---|---|---|---|
| `facts_present` | timing | `fields: [...]` | every listed fact is known; `null` or `unknown` counts as missing | `missingData` — unless Validation already flagged the same fields |
| `rule_found` | timing | `rule`, `keys: [...]` | an approved rule for that topic and those facts was found | `missingData` (`rule: <topic>`) |
| `deadline` | timing | `rule`, `from`, `output` | always computes: applies the rule to the `from` date and writes the date to `output`; `not available` if either is missing | — |
| `deadline_met` | timing | `deadline`, `by`, `flag` | the date in `by` is on or before the `deadline` | the case's `flag` |
| `cutoff` | timing | `pay_by`, `cutoffs`, `output`, `flag` | from the `cutoffs` record, the latest time a payment can be submitted and still reach the employee by the date in `pay_by`, written to `output`; passes when the record's `as_of` (the cut-off system's current time) is comfortably before it. No `as_of` → `not available` | the case's `flag` — also when it is too close to call |
| `requirement` | obligations | `rule`, `output` | always reports what the rule requires (e.g. pay out unused PTO: `required` / `policy` / `not_required`) | — |
| `obligation` | obligations | `when`, `rule`, `output` | when the condition holds, reports the obligation the rule creates and its deadline; `not_applicable` otherwise | — |
| `exception` | exceptions | `records: [...]`, `flag` | none of the listed records shows an active item for the subject (e.g. an open leave of absence, an active garnishment) | the case's `flag`, one per active item |

Run only your own checks, from the ones the case's `checks:` lists. A worker
with nothing to run returns empty `steps`.

## Common flags

- `missingData` — `{"missing": [<facts or rules>]}`
- `complianceTiming` — `{"rule": <text>, "required_by": <date>, "planned": <date>}`
- `cutoffRisk` — `{"pay_by": <date>, "submit_by": <time>, "as_of": <time>, "cutoffs": <source>}`
- `complianceException` — `{"kind": "leave" | "garnishment", "record": <the facts from the record>}`

Raise each problem once, even if several cases hit it.
