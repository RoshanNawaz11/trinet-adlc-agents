# State

## What
The state the employee works in. It decides the final-pay
deadline, whether leave must be paid out, which payment
methods are allowed, and who is paid on death.

## Values
Any two-letter state. In the mock data: TX, CA, NY, IL,
WA, FL, AZ.

## Source
Validation's work state.

## How it reaches the rules
As facts, worked out once by Compliance from the state's
rule record. The payroll rules read the facts, never the
state's name:
- final-pay due date (from the discharge or resignation
  rule, by termination type)
- payout requirement: required, policy or not required
- allowed payment methods, by termination type
- who is paid on death

## Effect by value
From the legal rule records in the mock data.

| State | Leave payout | Due — involuntary | Due — voluntary | Payment method — involuntary | Payment method — voluntary |
|---|---|---|---|---|---|
| CA | required | immediately at discharge | within 72 hours; last day if 72 hours' notice given | live check at termination | check, or direct deposit with consent |
| TX | policy | within 6 calendar days | next regular payday | check or direct deposit | check or direct deposit |
| NY | policy — if the policy is silent, required | next regular payday | next regular payday | check or direct deposit | check or direct deposit |
| IL | required | at separation if possible, at the latest next regular payday | next regular payday | check or direct deposit | check or direct deposit |
| WA | policy | end of the pay period | end of the pay period | check or direct deposit | check or direct deposit |
| FL | policy | next regular payday | next regular payday | check or direct deposit | check or direct deposit |
| AZ | policy | next regular payday | next regular payday | check or direct deposit | check or direct deposit |

Rules it changes:
- payroll.leave-payout — through the payout requirement
- payroll.payment-method — through the allowed methods
- payroll.deductions — through deduction limits and
  consent rules, when the state has them
- payroll.net-pay — state tax comes from the payroll
  system's figures for the work state
- Compliance's deadline and timing rules

## Gaps the data shows
- "Within 72 hours" (CA, voluntary) and "end of the pay
  period" (WA): Compliance's deadline forms don't cover
  hours or end-of-period yet.
- NY's "policy, but required if the policy is silent" is
  a fourth payout requirement — today it would read as
  plain "policy".
- State tax: only TX and WA say "no state income tax" in
  the data; the rules take tax from the payroll system,
  so this is a note, not a rule.

## Orders in the mock data
| State | Order | Termination type |
|---|---|---|
| TX | SO-20260930-1001 | voluntary |
| CA | SO-20261002-1002 | involuntary |
| NY | SO-20260930-1003 | voluntary, on leave |
| IL | SO-20260930-1004 | involuntary (layoff) |
| WA | SO-20260925-1005 | death |
| FL | SO-20261016-1006 | voluntary |
| AZ | SO-20261023-1007 | voluntary |
