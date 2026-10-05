# Checks

Every check a payroll case can use, what its settings mean, which worker runs
it, and when it passes. A case file only names checks from this list. A check
whose inputs are missing is `not available` — it does not fail.

| Check | Worker | Settings | Passes when | Flag if not |
|---|---|---|---|---|
| `inputs_present` | earnings, setup | `fields: [...]` | every listed input is known; `null` or `unknown` counts as missing | `missingData` — unless another agent already flagged the same fields |
| `hours_present` | earnings | `flag` | an hourly employee has hours for the final period (salaried: not applicable) | the case's `flag` |
| `one_outcome` | deductions | `field`, `flag` | the records allow exactly one value for the field | the case's `flag`, with each possible value and its effect on pay |
| `matches_system` | reconcile | `field`, `system_field`, `tolerance`, `flag` | our figure and the payroll system's differ by no more than `tolerance` (USD) | the case's `flag`, with both amounts and what explains the difference |
| `payment_method_usable` | reconcile | `flag` | the method on file is active and can pay by the date needed | the case's `flag`, with the reason and a recommended method |
| `setup_complete` | setup | `fields: [...]`, `flag` | every listed pay-setup item is present in the payroll system | the case's `flag`, listing what is missing |

Run only your own checks, from the ones the case's `checks:` lists. A worker
with nothing to run returns empty `steps`.

## Common flags

- `missingData` — `{"missing": [<field names>]}`

Raise each problem once, even if several cases hit it.
