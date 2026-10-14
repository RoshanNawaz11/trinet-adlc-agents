# Employment Type

## What
The kind of employment, and whether the employee is
exempt from overtime. It decides which inputs are
needed, whether overtime is paid, and benefits
eligibility.

## Values
- Employment: regular, temporary, part-time, contractor.
- Overtime status: exempt, non-exempt.

## Source
Payroll and HR records. Never inferred from pay type —
a salaried employee can be non-exempt.

## How it reaches the rules
As cases inside the rules — the logic itself changes.

## Effect by value

| Value | inputs-present | earnings | benefits | leave-payout |
|---|---|---|---|---|
| regular | as written | as written | eligible per the plan | as written |
| temporary | as written | as written | usually not eligible — if the record says eligible, benefitsAmbiguous | per the plan's accrual |
| part-time | as written | FTE applies if the proration method uses it | eligible only if FTE meets the plan's minimum | per the plan's accrual |
| contractor | not applicable — flag to confirm the classification, then stop | not applicable | not applicable | 0 — no company leave |
| exempt | as written | no overtime; overtime lines → flag for review | — | — |
| non-exempt | as written | overtime at the rate the payroll system pays | — | — |

## Gaps the data shows
- Most of the mock employees are non-exempt; one is
  exempt (the CA salaried employee).
- No contractor in the mock data, so the contractor
  path can't be tested yet.

## Orders in the mock data
| Value | Orders |
|---|---|
| exempt, salaried | SO-20261002-1002 (CA) |
| temporary, part-time | SO-20260930-1004 (IL) |
| regular, non-exempt | the others |
