# Employee Identified

## Purpose
Make sure the order is about one real employee of the
order's company, who hasn't already left.

## Required data
- The employee the order names: name and ID.
- The order's assignee — the specialist handling it.
- The employee record: ID, name, company, employment
  status, and termination date if any.
- The order's company.
- Sources: the service order, the employee record.

## Condition
order-eligible passed.

## Required output

### Found, same company, still employed
- result: pass

### The order doesn't name the employee
- result: fail
- Flag `missingData` (employee).

### No record for the named employee
- result: fail
- Stop — flag `missingData` (employee ID).

### The named person is the assignee
- result: fail
- The assignee handles the case; never treat them as the
  employee leaving.
- Flag `missingData` (employee).

### The employee works for another company
- result: fail
- Flag `employeeMismatch`, with both companies.

### Already terminated
- result: fail
- Stop — flag `alreadyTerminated` with the status.

### Name and ID point to different people
- result: fail
- Flag `recordMismatch` — the analyst picks.

## Exceptions

### On a leave of absence
On leave is still employed.
- result: pass
- Note it; validation.leave-of-absence flags it.

### Suspended or inactive, but not terminated
- result: pass
- Note the status.

### The record already shows this termination
Status is terminated, with the same termination date as
this order — the record was updated ahead of payroll.
- result: pass
- Check flag — the analyst confirms it is this
  termination, not an earlier one.

### Several records match the name, and there is no ID
- result: not available
- Input flag — the analyst picks the record.

### Rehired employee
An older terminated record and a current one.
- Use the current record.

### Contractor
- result: pass
- Note it; payroll flags the classification.

### The employee has died
- result: pass
- Note it; the payee changes later.

## Output
- result: pass, fail, not available or not applicable
- subject_employee_id, subject_name: or null
- employment_status: as on the record
- flags: issues requiring acknowledgement or review

## Evidence
Return:
- The name and ID from the order, and the assignee.
- The record matched: ID, company, status and source.
- Rule ID: validation.employee-identified.

## To confirm with the team
- Already terminated with the same date as this order:
  check flag (this rule), or stop?
