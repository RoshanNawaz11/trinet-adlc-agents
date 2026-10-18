# Deductions

## Purpose
Work out what is taken from the final paycheck: benefit
and other recurring deductions, garnishments, and any
amount the employee owes back.

## Required data
- Recurring deductions for this pay: type, amount, and
  whether each is taken before or after tax.
- Benefit coverage on the last day worked and the date
  it ends on separation.
- Benefits eligibility, from payroll.benefits.
- Active garnishment orders, and their withholding
  rules and limits as the payroll system gives them.
- A negative leave balance, from payroll.leave-payout,
  and whether the record allows deducting it.
- Any signed agreement allowing a deduction.
- Sources: payroll record, benefits coverage,
  garnishment orders, the order's special instructions,
  Compliance's result.

## Condition
The case is a termination, and inputs-present passed.

## Required output

### Benefit deductions
- Take them only for coverage up to the coverage end
  date, and only if the employee is eligible.
- Keep before-tax and after-tax deductions apart —
  net-pay needs them for the taxes.

### Other recurring deductions
- Take them as the payroll system gives them for this
  pay (e.g. retirement contributions).

### Garnishments
- Take each active order's amount as the payroll
  system's rules give it, in the order it sets.
- Never compute a legal limit yourself.
- Input flag `garnishmentConfirm` per order — the
  analyst confirms the withholding with the Garnishment
  Team, or enters the amount the team gives.
- A released or satisfied order takes nothing.

### Negative leave balance
- Deduct it only when the record says negative balances
  are deducted and a signed agreement is on file.
- Otherwise nothing is recovered; note it in evidence.
- Decision flag when it is deducted — the analyst
  confirms.

### No deductions
- deductions and garnishments: 0

### Required data is missing or conflicting
- result: not available
- The affected amounts: null, not zero.
- Do not guess an amount, a limit or an end date.

### Case is not a termination
- result: not applicable
- reason: The case is outside this rule's scope.

## Exceptions

### A special instruction asks for a deduction
Unreturned laptop, salary advance, negative PTO.
- Leave it out.
- Stop — legal limits apply and a signed agreement is
  needed; an analyst decides.

### A deduction was already taken for this period
An earlier pay already took it for the final period.
- Don't take it twice; note the earlier pay.

### Coverage ends after the last day worked
e.g. coverage runs to the end of the month.
- Take the deduction for the coverage the final pay
  covers, as the payroll system gives it.
- Check flag when the system gives no figure.

### A garnishment order is not yet set up
An active order the payroll system doesn't withhold
for yet.
- That order's amount: not available.
- Flag `garnishmentConfirm` — the analyst gets the
  amount from the Garnishment Team.

### Garnishments together exceed the limit
- Take them in the payroll system's order, up to its
  limit.
- What is left over goes to net-pay as unrecoverable.

### Deductions exceed what the check can cover
- Take them as above; net-pay decides what is
  unrecoverable.

### The employee has died
- Stop — garnishments and the payee change; an analyst
  handles it.

### The employee is a contractor
- result: not applicable
- Flag to confirm the classification, then stop.

## Output
- result: pass, not available or not applicable
- deductions: total, or null if unresolved
- deduction_lines: per deduction, the type, before or
  after tax, amount and source
- garnishments: total, or null if unresolved
- garnishment_lines: per order, the amount and the rule
  applied
- flags: issues requiring acknowledgement or review

## Not included
Taxes and unrecoverable amounts (payroll.net-pay), and
what the client is billed (payroll.benefits).

## Evidence
Return:
- Employee ID and final pay period.
- Each deduction and garnishment: amount, source, and
  the rule or agreement that allows it.
- Coverage end date and its source.
- Any exception applied, and why.
- Rule ID: payroll.deductions.

## To confirm with the team
- Negative leave: is the record's setting enough, or is
  a signed agreement always needed?
- Flag name for the missing coverage figure.
