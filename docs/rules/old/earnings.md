# PAY-001 — Calculate Termination Earnings

## Purpose
Calculate regular and overtime earnings for a WSE
termination based on the employee's pay type.

## Required data
- Employee pay type: hourly or salaried.
- Pay rate, rate basis and currency.
- Last day worked and final payroll period.
- Regular and overtime earning lines and hours.
- For salaried employees: FTE and approved proration method.
- For overtime: exemption status and applicable overtime rate.
- Sources: employee payroll record, timecards,
  payroll calendar and approved earning policies.

## Condition
The case is a WSE termination AND pay type equals
"HOURLY" OR "SALARIED".
Apply the OR only to the two pay types.

## Required output

### Pay type is HOURLY
- Calculate each regular earning line:
  regular hours × applicable hourly rate.
- Sum the calculated lines into regular_pay.
- Calculate overtime separately.
- Do not include the same hours in both calculations.

### Pay type is SALARIED
- Determine the full-period salary from the recorded
  salary basis and payroll configuration.
- Apply the approved final-period proration method.
- Apply FTE only if the method requires it and the
  recorded salary is not already adjusted for FTE.
- Return the calculated amount as regular_pay.
- Do not assume a proration formula.

### Overtime exists and employee is NON_EXEMPT
- Calculate each eligible overtime line:
  overtime hours × applicable overtime rate.
- Sum the calculated lines into overtime_pay.
- Do not assume an overtime rate or multiplier.

### Overtime exists and employee is EXEMPT
- Flag the earning lines for review against the
  applicable earning policy.
- Leave overtime_pay unresolved until confirmed.
- Do not infer exemption status from pay type.

### Complete records confirm no overtime
- Set overtime_pay to zero.

### Calculation is complete
Return:
- status: calculated
- regular_pay: calculated regular earnings
- overtime_pay: calculated overtime earnings
- currency: currency from the payroll record
- earning_lines: inputs and amount for each line

These amounts exclude unused-leave payout, taxes,
deductions and additional pay handled by other rules.

### Timecard is not approved
- Raise the P2 check flag.
- Calculate provisionally from the available records,
  as specified in the PM's rule.
- Set status to provisional pending acknowledgement.

### Required data is missing or conflicting
- status: unresolved
- reason: Identify the missing or conflicting fields.
- Return affected amounts as null, not zero.
- Do not guess rates, hours, exemption status or formulas.

### Case is outside WSE termination
- status: not_applicable
- reason: The case is outside this rule's scope.

## Evidence
Return:
- Employee ID and payroll period.
- Pay type and rate basis.
- Hours, rates and calculation used for each line.
- Applied policy references.
- Sources of the input values.
- Rule ID: PAY-001.