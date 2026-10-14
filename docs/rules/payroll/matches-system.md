# Matches System

## Purpose
Check our final-pay figures against the payroll
system's own figures and the client's order, so that a
wrong amount is caught before anyone is paid.

## Required data
- Our figures: gross pay, leave payout and net pay,
  from the other payroll rules.
- The payroll system's figures for this pay: total gross
  and net pay.
- The total pay amount stated on the client's order,
  when it states one.
- Sources: payroll record, the order, the other payroll
  rules' results.

## Condition
The case is a termination, and net-pay has returned a
result.

## Required output

### The comparisons
1. Our net pay against the payroll system's net pay.
2. Our gross pay plus leave payout against the payroll
   system's total gross.
3. The order's total pay against the payroll system's
   total gross.

Each matches when the two differ by no more than $0.01.

### Every comparison matches
- result: pass

### Our net pay differs from the system's
- result: fail
- Decision flag `netPayMismatch` — both amounts, and the
  line that explains the difference (e.g. taxes, leave,
  a deduction).

### Our gross differs from the system's
- result: fail
- Name the line that differs, in the same
  `netPayMismatch` flag when net pay differs too —
  raise the problem once.

### The order's pay differs from the system's
- result: fail
- Decision flag `orderPayMismatch` — the order's amount,
  the system's amount and the difference.
- Never pay the order's figure without the analyst
  confirming it.

### Both figures are zero
- A match — e.g. already paid through the last day.

### Required data is missing
- The system has no figure → that comparison is
  not available.
- The order states no total → comparison 3 is not
  applicable.
- result: not available when no comparison could run.
- Do not compare against an estimate of your own.

### Case is not a termination
- result: not applicable
- reason: The case is outside this rule's scope.

## Exceptions

### Benefits eligibility is unresolved
benefitsAmbiguous gives two net-pay options.
- Compare each option with the system.
- The option that matches shows what the system
  assumed — note it in the benefitsAmbiguous flag.

### The order states net pay, not gross
- If the order's figure matches the system's net pay,
  it is a match; note that the order gave net pay.

### Part of the pay goes on a separate check
- Compare each check separately.

### Our figures are provisional
- Compare as usual; the result stays provisional.

### The system's figures are older than the latest change
The system's figures were calculated before a change to
hours, rate or leave on record.
- Compare anyway.
- Check flag — the analyst confirms which figures are
  current.

## Output
- result: pass, fail, not available or not applicable
- comparisons: per comparison, both amounts, the
  difference and the explanation
- provisional: true or false
- flags: issues requiring acknowledgement or review

## Not included
Working out the figures themselves (earnings,
leave-payout, deductions, net-pay).

## Evidence
Return:
- Employee ID and final pay period.
- Each comparison: both amounts, their sources and the
  difference.
- The line that explains each difference.
- Any exception applied, and why.
- Rule ID: payroll.matches-system.

## To confirm with the team
- Flag name and severity for the order's pay figure
  differing from the system's (not in the team's rules
  yet; the mock data tests it on one order).
- Is $0.01 also the right tolerance for gross?
