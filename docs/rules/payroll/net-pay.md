# Net Pay

## Purpose
Work out the taxes, anything that can't be taken from
the final paycheck, and the final net pay.

## Required data
- Gross pay, from payroll.earnings.
- Leave payout, from payroll.leave-payout.
- Deductions (before and after tax) and garnishments,
  from payroll.deductions.
- Withholding settings, and the payroll system's tax
  figures for this pay.
- Sources: payroll record, the other payroll rules'
  results.

## Condition
The case is a termination, and earnings, leave-payout
and deductions have each returned a result.

## Required output

### Taxes
- Take them from the payroll system's tax figures for
  this pay.
- Never compute a tax rate yourself.

### Unrecoverable amounts
- Anything that would take net pay below zero, or past a
  limit the payroll system gives, can't be taken.
- Report it as unrecoverable and leave it out of
  net pay.
- Decision flag `unrecoverable` — the analyst decides.

### Net pay
- net_pay = gross pay + leave payout − taxes −
  (deductions + garnishments − unrecoverable).
- Round only the result, to cents.

### Net pay is zero
- A valid result — e.g. already paid through the last
  day.
- No flag just because it is zero.

### An input is provisional
- Calculate as usual.
- provisional: true

### Required data is missing or conflicting
- result: not available
- net_pay: null, not zero.
- Do not guess a tax figure or an amount.

### Case is not a termination
- result: not applicable
- reason: The case is outside this rule's scope.

## Exceptions

### The payroll system has no tax figures for this pay
- taxes and net_pay: null
- result: not available
- Flag — an analyst gets the figures.

### Part of the pay goes on a separate check
A special instruction puts e.g. the leave payout or a
bonus on its own check.
- Work out taxes and net pay for each check.
- Decision flag — the analyst confirms the split.

### The employee is tax-exempt
- Use the exemption on record: no tax for what it
  covers.

### The work state has no state income tax
- State tax: 0. A normal result, not an exception to
  flag.

### The employee worked in two states in the final period
- State tax for each state's share of the wages, as
  earnings split them.
- Flag — an analyst confirms the split.

### The employee has died
- Tax treatment changes for wages paid after death.
- Stop — an analyst handles the payment.

## Output
- result: pass, not available or not applicable
- taxes: total, or null if unresolved
- tax_lines: per tax, the amount and source
- unrecoverable: amount, or null if unresolved
- net_pay: amount, or null if unresolved
- provisional: true or false
- flags: issues requiring acknowledgement or review

## Not included
Checking net pay against the payroll system's figure
(payroll.matches-system), and how it is paid
(payroll.payment-method).

## Evidence
Return:
- Employee ID and final pay period.
- Every input amount and its source.
- Each tax: amount and source.
- Unrecoverable: what, how much, and why.
- The net-pay formula with the figures filled in.
- Any exception applied, and why.
- Rule ID: payroll.net-pay.

## To confirm with the team
- Taxes: take them from the payroll system (this rule,
  and what our agents do today), or compute them —
  before-tax deductions reduce federal tax and FICA,
  payouts and bonuses at the 22% supplemental rate,
  Social Security 6.2%, Medicare 1.45%, state tax by
  work state (team's rule)?
