# Dates Valid

## Purpose
Make sure the case's dates are in a possible order.

## Required data
- Hire date, from the employee record.
- Last day worked and termination date, from
  case-facts.
- Today's date.
- Sources: the employee record, case-facts.

## Condition
case-facts has returned the dates.

## Required output

### Hire date < last day worked ≤ termination date
- result: pass

### Any comparison fails
- result: fail
- Stop — flag `invalidDates`, with the rule and every
  date.

### A date is missing
- result: not available
- No flag of its own — case-facts names the missing
  date.

## Exceptions

### Last day worked is long before the termination date
e.g. on leave until the termination date.
- result: pass
- Note the gap; Compliance checks the leave.

### The termination date is in the future
- result: pass
- Note it.

### The termination date is long past
The case arrived late.
- result: pass
- Note it; Compliance checks whether final pay is
  already overdue.

### Last day worked is the hire date
A same-day exit.
- result: fail as the rule is written
- Flag `invalidDates` — the analyst confirms.

### Rehired employee
- Use the latest hire date.

### The employee has died
- The termination date is the date of death; the last
  day worked may be earlier.
- result: pass

## Output
- result: pass, fail, not available or not applicable
- flags: issues requiring acknowledgement or review

## Evidence
Return:
- Each date and its source.
- Each comparison and whether it held.
- Rule ID: validation.dates-valid.

## To confirm with the team
- Same-day exit (hire date = last day worked): valid?
