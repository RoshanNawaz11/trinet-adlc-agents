# Submit By

## Purpose
Work out the latest time final pay can be submitted and
still meet every deadline.

## Required data
- The final-pay due date and pay timing, from
  compliance.final-pay.
- The order's own deadline, and its time zone.
- The payroll change deadline for the period (on-cycle),
  or the off-cycle request cut-off (off-cycle).
- The payment method's cut-off: the bank file for direct
  deposit, the same-day cut-off for a live check.
- The payment method on file.
- The work state's time zone, and the current time.
- Sources: the order, payroll cut-offs,
  compliance.final-pay.

## Condition
compliance.final-pay returned a due date.

## Required output

### One time zone
- Convert every deadline to the work state's time zone.

### Submit by
The earliest of:
- the order's deadline;
- the payroll change deadline (on-cycle), or the
  off-cycle request cut-off (off-cycle);
- the payment method's cut-off for paying by the due
  date.

### Comfortably before it
- result: pass

### Past it, or too close to call
- result: fail
- Decision flag `cutoffRisk` — pay-by date, submit-by
  time, the current time, and the deadline that set it.

### Some cut-offs are missing
- Use the ones there are; name the missing ones in
  evidence.
- None at all → result: not available.

### A deadline's time zone isn't stated
- Don't assume one. Leave that deadline out and note it.

## Exceptions

### Due immediately
e.g. a check handed over at termination.
- Submit by is before the termination meeting, within
  the same-day cut-off.
- Meeting time unknown → flag — the analyst confirms.

### The payment method isn't settled yet
A payment-method flag is open.
- Work out submit-by for each possible method; note it.

### A cut-off falls on a weekend or holiday
- Use it as given.

### Final pay is already overdue
- result: fail
- `cutoffRisk`, saying it is already late. No second
  timing flag.

### Part of the pay goes on a separate check
- Submit-by for each check.

## Output
- result: pass, fail or not available
- submit_by: date, time and time zone, or null
- set_by: the deadline that sets it
- deadlines: each one, converted
- flags: issues requiring acknowledgement or review

## Evidence
Return:
- Each deadline: original time, time zone, converted
  time and source.
- Which one is earliest.
- The current time used.
- Rule ID: compliance.submit-by.

## To confirm with the team
- How close counts as too close to call?
- Store every deadline in one time zone (team data fix 6).
