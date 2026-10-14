# Termination Type

## What
Why the employment ends. It decides which of the
state's deadlines applies, the allowed payment method in
some states, leave forfeiture under some policies, and —
for death — who is paid.

## Values
voluntary, involuntary, death. A layoff is involuntary.

## Source
Validation's termination type, from the order's reason.
Unknown → Validation raises an input flag; the analyst
picks.

## How it reaches the rules
- As facts from Compliance: the due date and the allowed
  payment methods are read for this termination type.
- As a case inside a rule where the logic changes
  (forfeiture, death).

## Effect by value

| Value | Due date | Payment method | leave-payout | Payee |
|---|---|---|---|---|
| voluntary | the state's resignation rule; may depend on notice given | the state's voluntary methods | a policy may require notice for the payout — only when the requirement is policy | the employee |
| involuntary | the state's discharge rule — often sooner | the state's involuntary methods (e.g. CA: live check at termination) | a policy may forfeit leave when dismissed for cause — only when the requirement is policy | the employee |
| death | the state's rule for death | as the payee needs | as usual | the estate or surviving spouse, as the state's rule says — stop (special-instructions.death) |

Rules it changes:
- payroll.payment-method — allowed methods by type
- payroll.leave-payout — forfeiture and notice terms
- every payroll rule's death exception
- Compliance's deadline rules

## Gaps the data shows
- Notice given matters for CA voluntary terminations
  (72 hours' notice → due on the last day); the mock
  orders don't say whether notice was given.
- A layoff is written as its own reason in the data
  (IL); it is read as involuntary.

## Orders in the mock data
| Value | Orders |
|---|---|
| voluntary | SO-20260930-1001 (TX), SO-20260930-1003 (NY), SO-20261016-1006 (FL), SO-20261023-1007 (AZ) |
| involuntary | SO-20261002-1002 (CA), SO-20260930-1004 (IL, layoff) |
| death | SO-20260925-1005 (WA) |
