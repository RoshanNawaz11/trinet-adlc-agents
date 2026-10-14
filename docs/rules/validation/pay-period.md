# Pay Period

## Purpose
Find the pay period that contains the last day worked,
its regular payday, and whether that pay run is still
open.

## Required data
- The employee's pay group.
- The pay calendar for that pay group.
- Last day worked, from case-facts.
- Today's date.
- Sources: the payroll record, the pay calendar,
  case-facts.

## Condition
case-facts has returned the last day worked.

## Required output

### Exactly one period contains the last day worked
Period start ≤ last day worked ≤ period end.
- result: pass
- Return the period, its regular payday and the pay
  cycle (below).
- Any frequency — weekly, biweekly, semi-monthly,
  monthly. Match by dates, never by the frequency name.

### Pay cycle
- on-cycle: that period's pay run hasn't been processed
  yet (its change deadline hasn't passed).
- off-cycle: it has.
- unknown: the calendar doesn't say.

### No calendar for the pay group
- result: fail
- Stop — flag `missingData` (pay calendar).

### No period, or more than one, contains the date
- result: not available
- Flag `missingData` — a single period couldn't be
  found.
- Do not pick a period yourself.

### Required data is missing
- result: not available
- Do not guess the pay group, calendar or dates.

## Exceptions

### The payday falls on a weekend or holiday
- Use the pay date the calendar gives. Never shift it
  yourself.

### The last day worked is on a period boundary
- It belongs to the period whose start and end include
  it. If two do, flag as above.

### The pay group changed during the final period
- Use the pay group on the last day worked.
- Check flag, with both pay groups.

### The calendar doesn't reach the last day worked
- result: not available
- Flag `missingData` (pay calendar).

### Special or off-cycle runs in the calendar
- Use only the regular pay runs.

## Output
- result: pass, fail, not available or not applicable
- pay_group, period_start, period_end, regular_payday:
  or null
- pay_cycle: on-cycle, off-cycle or unknown
- flags: issues requiring acknowledgement or review

## Not included
Whether final pay must legally run off-cycle —
Compliance decides it from the due date.

## Evidence
Return:
- Pay group and calendar used.
- Last day worked.
- The period matched: start, end, payday, and its
  change deadline.
- Rule ID: validation.pay-period.
