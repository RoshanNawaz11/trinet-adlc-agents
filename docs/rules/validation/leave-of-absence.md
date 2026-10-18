# Leave of Absence

## Purpose
Find an open leave of absence. The analyst opens a
separate LOA case before the termination is worked.

## Required data
- Leave-of-absence records, and the employment status.
- Sources: the employee record, leave records.

## Condition
validation.employee-identified passed.

## Required output

### No open leave
- result: pass

### Open leave of absence, or status on leave
- result: fail
- Stop — flag `leaveOfAbsence`, with the record's facts.
  The analyst opens an LOA case; this order is validated
  again after it.

### The leave records couldn't be fetched
- result: not available
- Never assume there is none.

## Exceptions

### The leave ended before the last day worked
- Not active. result: pass
- Note it.

### Terminated while on leave
The leave runs up to the termination date.
- Active — `leaveOfAbsence`.

### Leave for a work injury or disability
- Report its kind — some states protect these.

## Output
- result: pass, fail or not available
- active_leaves: how many leaves are open
- flags: issues requiring acknowledgement or review

## Evidence
Return:
- Each leave record checked: its status, dates and
  source.
- Rule ID: validation.leave-of-absence.
