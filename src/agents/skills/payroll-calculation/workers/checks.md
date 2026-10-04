# Worker — Checks

Every check a payroll case can use, what its settings mean, and when it passes.
A case file only names checks from this list. A check whose inputs are missing
is `not available` — it does not fail.

| Check | Settings | Passes when | Flag if not |
|---|---|---|---|
| `inputs_present` | `fields: [...]` | every listed input is known; `null` or `unknown` counts as missing | `missingData` — unless another agent already flagged the same fields |
| `matches_system` | `field`, `system_field`, `tolerance`, `flag` | our figure and the payroll system's differ by no more than `tolerance` (USD) | the case's `flag`, with both amounts and what explains the difference |
| `one_outcome` | `field`, `flag` | the records allow exactly one value for the field | the case's `flag`, with each possible value and its effect on pay |
| `payment_method_usable` | `flag` | the method on file is active and can pay by the date needed | the case's `flag`, with the reason and a recommended method |
| `setup_complete` | `fields: [...]`, `flag` | every listed pay-setup item is present in the payroll system | the case's `flag`, listing what is missing |

## Common flags

- `missingData` — `{"missing": [<field names>]}`

Raise each problem once, even if several cases hit it.
