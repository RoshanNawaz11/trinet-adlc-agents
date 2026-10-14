# Exceptions

## Purpose
Find anything on record that takes the case off the
standard path: a leave of absence or an active
garnishment.

## Required data
- Leave-of-absence records, and the employment status.
- Garnishment orders: status and kind.
- Sources: the employee record, leave records,
  garnishment records.

## Condition
validation.employee-identified passed.

## Required output

### Nothing active
- result: pass
- exceptions: none

### Open leave of absence, or status on leave
- result: fail
- Stop — flag `complianceException` (leave), with the
  record's facts.

### Active garnishment
- result: fail
- Stop — flag `complianceException` (garnishment), one
  per order.

### A record couldn't be fetched
- result: not available
- Never assume there is none.

## Exceptions

### The leave ended before the last day worked
- Not active. result: pass
- Note it.

### Terminated while on leave
The leave runs up to the termination date.
- Active — `complianceException` (leave).

### The garnishment was released or satisfied
- Not active. result: pass

### A garnishment order received but not set up yet
- Active — `complianceException` (garnishment).
- Note it; payroll.deductions flags it as well.

### Several garnishments
- One flag per order, each with its kind (child support,
  creditor, tax levy).

### Leave for a work injury or disability
- Report its kind — some states protect these.

## Output
- result: pass, fail or not available
- exceptions: [{kind: leave or garnishment, detail}]
- flags: issues requiring acknowledgement or review

## Evidence
Return:
- Each record checked: what, its status, dates and
  source.
- Rule ID: compliance.exceptions.

## To confirm with the team
- An active garnishment stops the case (team rule C9),
  or is it flagged and payroll deducts it?
