# Inputs Present

## Purpose
Make sure everything needed to calculate the final
paycheck is on record before any amount is calculated.

## Required data
- Pay rate and pay type (hourly or salaried).
- Hours worked in the final pay period — hourly
  employees only.
- Withholding for the final pay.
- Sources: employee payroll record, timecards.

## Condition
The case is a termination, and the case facts
(employee, last day worked) are confirmed by Validation.

## Required output

### Every input is present
- result: pass
- Outcome: continue to the calculations.

### Employee is salaried
- Final-period hours are not required.
- Check the other inputs as above.

### Hours are recorded as zero
- Zero is a value, not a missing input — e.g. an
  employee on leave, or already paid through the
  last day.
- result: pass, when the other inputs are present.

### An input is missing
- result: fail
- Outcome: stop — flag `missingData`, listing every
  missing input in one flag.
- Return every amount as null, not zero.
- Do not guess a rate, pay type, hours or withholding.

### Two sources give different values for an input
- result: fail
- Outcome: stop — flag `missingData`, naming the
  input and both values with their sources.
- Do not pick one of the values.

### Case facts are not confirmed by Validation
- result: not available
- Outcome: ⏸ wait for Validation's result. If it shows
  the employee isn't identified or the dates are
  invalid, nothing is calculated.

### Case is not a termination
- result: not applicable
- reason: The case is outside this rule's scope.

## Exceptions

### The order's hours differ from the timecard
The client's form states hours that don't match the
final-period timecard.
- Use the timecard hours.
- Check flag, with both figures.

### The pay rate changed during the final period
- Not a conflict: both rates are present, each with its
  effective date.
- result: pass — earnings uses each rate for its dates.

### No withholding because the employee is tax-exempt
- An exemption on record counts as present.
- result: pass

### Another team must confirm the final hours
A special instruction says e.g. "Client manager to
confirm final hours".
- result: not available
- Wait until they answer.

### The employee is a contractor
There is no payroll record or withholding to check.
- result: not applicable
- Flag to confirm the classification, then stop —
  contracts are closed out, not paid through payroll.

### The employee worked in two states in the final period
- Withholding must be on record for both states.
- A missing state's withholding counts as missing.
- Flag — an analyst confirms the split.

## Output
- result: pass, fail, not available or not applicable
- inputs: each input with its value and source, or
  "missing"
- flags: issues requiring acknowledgement or review

## Evidence
Return:
- Employee ID and final pay period.
- Each input: its value, or "missing".
- Source of each value.
- Rule ID: payroll.inputs-present.

## To confirm with the team
- stop vs. flag: today the agents flag a missing
  input and carry on to one review at the end (X2/X3).
