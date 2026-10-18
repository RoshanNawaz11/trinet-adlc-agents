# On-Cycle Removed

## Purpose
Make sure the employee is out of the regular payroll
runs, so final pay isn't paid twice (job map Action 15).

## Required data
- The regular (on-cycle) payroll runs, not yet paid,
  that still include the employee: pay date and status.
- Sources: the payroll system.

## Condition
Any termination.

## Required output

### Not in any regular run
- result: pass

### Still in an open regular run
- result: fail
- Check flag `onCycleNotRemoved`, one per run — the
  analyst removes the employee before final pay.

### Still in a regular run that is already processing
- result: fail
- Decision flag `onCycleNotRemoved` — too late to simply
  take them out; the analyst stops or offsets it.

### The runs couldn't be read
- result: not available
- Flag `missingData` — never assume the employee was
  removed.

## Exceptions

### The employee is a contractor
- result: not applicable

## Output
- result: pass, fail, not available or not applicable
- runs_to_remove: how many regular runs still include
  the employee
- flags: issues requiring acknowledgement or review

## Not included
A regular run that already paid the final period
(payroll.earnings).

## Evidence
Return:
- Each run checked: pay date, status and source.
- Rule ID: payroll.on-cycle-removed.

## To confirm with the team
- Is final pay ever paid inside the regular run
  (on-cycle)? Then the employee stays in that run, and
  only the later runs count.
