# Earnings

## Purpose
Calculate the regular and overtime earnings for the
final pay period, based on the employee's pay type.

## Required data
- Pay type: hourly or salaried.
- Pay rate and what it is per (hour, period, year).
- Last day worked and the final pay period.
- Earning lines for the final period, with their hours
  and whether the timecard is approved.
- Salaried employees: FTE, and the proration method the
  payroll system or company policy specifies.
- Overtime: exemption status, and the overtime rate the
  payroll system pays.
- Sources: employee payroll record, timecards, pay
  calendar, company earning policies.

## Condition
The case is a termination, and inputs-present passed.

## Required output

### Hourly employee
- Calculate each regular earning line (regular, and
  paid leave taken in the period such as sick or
  holiday): hours × hourly rate.
- Sum the lines into regular_pay.
- Calculate overtime separately (below).
- Never count the same hours in both.

### Salaried employee
- Take the full-period salary from the recorded salary
  and pay frequency.
- Prorate it for the final period with the method the
  payroll system or company policy specifies.
- Apply FTE only if that method requires it and the
  recorded salary isn't already adjusted for FTE.
- Return the result as regular_pay.
- Do not assume a proration method.

### Overtime, non-exempt employee
- Calculate each overtime line: overtime hours × the
  overtime rate the payroll system pays.
- Sum the lines into overtime_pay.
- Do not assume an overtime rate or multiplier.

### Overtime, exempt employee
- overtime_pay: null
- Outcome: flag the overtime lines for review against
  the company's earning policy.
- Do not infer exemption status from pay type.

### Records confirm no overtime
- overtime_pay: 0

### Timecard is not approved
- Calculate from the submitted hours anyway.
- Mark the amounts provisional.
- Outcome: check flag — the analyst acknowledges the
  unapproved timecard; the case then continues.

### Required data is missing or conflicting
- result: not available
- Return the affected amounts as null, not zero.
- Raise no flag of its own — inputs-present names the
  missing or conflicting input.
- Do not guess rates, hours, exemption status or
  proration.

### Case is not a termination
- result: not applicable
- reason: The case is outside this rule's scope.

## Exceptions

### The final period was already paid
The payroll system shows the employee already paid
through the last day worked.
- regular_pay and overtime_pay: 0 — never pay it twice.
- Note the earlier payment in evidence.

### The pay rate changed during the final period
- Split each line at the change: hours before × the old
  rate, hours after × the new rate.
- Both rates and effective dates in evidence.

### A special instruction adds pay
Severance, bonus, commission, expense reimbursement.
- Not part of earnings — leave it out of gross_pay.
- Decision flag — the analyst confirms the amount.
- A request for a separate check for it → decision flag
  as well.

### The pay type doesn't match the time records
e.g. a salaried employee with hourly timecard lines,
or an hourly employee with no timecard at all.
- Calculate by the pay type on the payroll record.
- Check flag, naming the mismatch.

### Hours look impossible
More hours in a day or a period than can be worked.
- result: not available
- Flag — an analyst confirms the hours.

### The employee worked in two states in the final period
- Split each line's wages by state, for state tax.
- Flag — an analyst confirms the split.

### The employee is a contractor
- result: not applicable
- Flag to confirm the classification, then stop.

### The employee has died
- Calculate as usual, but the wages go to the estate,
  not the employee.
- Stop — the payee changes; an analyst handles the
  payment.

## Output
- result: pass, not available or not applicable
- regular_pay, overtime_pay, gross_pay: amounts, or
  null if unresolved
- provisional: true or false
- earning_lines: per line, the type, hours, rate and
  amount
- flags: issues requiring acknowledgement or review

## Not included
Leave payout, taxes, deductions and any additional pay
(severance, bonus, commission) — other rules handle
them.

## Evidence
Return:
- Employee ID and final pay period.
- Pay type and what the rate is per.
- Hours, rate and amount for each line, and the formula.
- Proration method and its source (salaried).
- Exemption status and the overtime rate's source.
- Sources of the input values.
- Rule ID: payroll.earnings.

## To confirm with the team
- Flag names for the unapproved timecard and the
  exempt-overtime review.
- Our agents today prorate salary by days worked ÷
  working days in the period, and allow rate ×
  multiplier for overtime. This rule asks for the
  method and rate from the payroll system instead.
