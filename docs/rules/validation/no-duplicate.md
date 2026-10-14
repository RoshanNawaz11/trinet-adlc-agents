# No Duplicate

## Purpose
Make sure no other open termination order exists for
the same employee.

## Required data
- The employee's ID, from employee-identified.
- This order's ID.
- The employee's other service orders: type, status and
  dates.
- Sources: the service orders.

## Condition
employee-identified passed.

## Required output

### No other open termination order
- result: pass

### Another open termination order
- result: fail
- Stop — flag `duplicateSO`, with both orders.

### Employee not identified
- result: not available

## Exceptions

### The other order is closed or cancelled
- Not a duplicate. result: pass
- Note it if it closed recently — this may be a
  re-submission.

### The other order has a different termination date
- result: fail
- Flag `duplicateSO`, with both dates — the analyst
  decides which one stands.

### The other order corrects this one
It refers to this order as an amendment.
- Not a duplicate. result: pass
- Note it.

### An open order of another type
e.g. an address change.
- Not a duplicate. result: pass

### Same employee ID at another company
- Only orders for the same company count.

## Output
- result: pass, fail, not available or not applicable
- flags: issues requiring acknowledgement or review

## Evidence
Return:
- This order's ID and the employee's ID.
- Each other order checked: ID, type, status, dates.
- Rule ID: validation.no-duplicate.
