# Leave Payout

## Purpose
Decide whether the employee's unused leave is paid out
with the final paycheck, and how much.

## Required data
- Leave balance for each leave type (vacation or PTO,
  sick, floating holiday), and the date it is as of.
- The payroll system's own final-pay balance, and the
  hours it says to pay out, when it gives them.
- Any manual adjustment to the balance, and its reason.
- Applicable leave-payout rate and its effective date,
  supplied by the payroll record and applicable rule.
- For salaried employees, use the approved conversion
  method when an hourly equivalent is needed.
- Compliance's payout requirement: required, policy or
  not required.
- The company's payout policy: whether it pays out, for
  which leave types, and any minimum length of service.
- Hire date, last day worked, employment type.
- Sources: payroll record, leave records, company
  policies, Compliance's result, the order's special
  instructions.

## Condition
The case is a termination, and inputs-present passed.

## Required output

### Which balance to use
- Use the balance the payroll system worked out for the
  final pay period, including any manual adjustment.
- If another record shows a different balance, use the
  payroll system's and put both in evidence.
- Flag only when the difference changes the payout.

### Balance is dated before the last day worked
- Calculate with that balance anyway.
- provisional: true
- Check flag — the analyst acknowledges the out-of-date
  balance; the case then continues.

### Compliance says required
- Unused hours × the applicable leave-payout rate.
- State law overrides the company policy: pay it even
  if the policy says leave is not paid out.

### Compliance says policy
- Pay out only if the company policy pays out leave at
  separation and the employee meets its minimum length
  of service.
- Otherwise 0, naming the policy reason.

### Compliance says not required
- 0 for that leave type.

### Leave types
- Vacation or PTO: paid as above.
- Sick and floating holiday: paid only if the law or the
  company policy says so; otherwise 0.

### Balance is zero
- 0 for that leave type.

### Balance is negative
- 0 for that leave type — never a negative amount. A
  negative balance means leave was used before it was
  earned; nothing is owed to the employee.
- Taking it back from final pay is not this rule's job:
  payroll.deductions decides it.

### Compliance's requirement is unknown or missing
- result: not available
- leave_payout: null
- Wait for Compliance's result, or ask it.
- Never assume leave is paid, or not paid.

### Required data is missing or conflicting
- result: not available
- leave_payout: null, not zero.
- Do not guess a balance, rate, conversion or policy.

### Case is not a termination
- result: not applicable
- leave_payout: null
- reason: The case is outside this rule's scope.

## Exceptions

### A special instruction changes the payout
"Don't pay out PTO", "Pay out despite the policy".
- result: not available
- leave_payout: null
- Stop — the instruction overrides the law or policy;
  an analyst decides.

### The employee has died
- Calculate as usual, but the payout goes to the estate,
  not the employee.
- Stop — the payee changes; an analyst handles the
  payment.

### The employee is a contractor
- 0 — contractors don't accrue company leave.
- Flag to confirm the classification.

### The payout was already paid
The payroll system shows the leave already paid out.
- 0 — never pay it twice.
- Note the earlier payment in evidence.

### The balance has a manual adjustment
- Use the adjusted balance.
- An adjustment with no reason recorded → check flag.

### The balance is above the plan's maximum
More hours than the plan's accrual cap allows.
- Calculate with the cap, not the balance.
- Check flag, with both figures.

### The policy forfeits leave on this kind of exit
e.g. no payout when dismissed for cause.
- Apply it only when Compliance says policy.
- When Compliance says required, the law wins: pay it.

### The policy gives unlimited leave
There is no balance to pay out.
- 0 when Compliance says policy or not required.
- When Compliance says required: result: not available,
  leave_payout: null, and flag — an analyst decides what
  is owed.

### The employee is on a leave of absence
- Calculate as usual, from the balance on the last day
  worked.
- Note the leave of absence; Compliance raises its own
  exception for it.

## Output
- result: pass, not available or not applicable
- leave_payout: total amount, or null if unresolved
- provisional: true or false
- leave_lines: per leave type, the requirement, hours,
  rate and amount
- flags: issues requiring acknowledgement or review

## Not included
Leave taken during the final period (payroll.earnings),
and recovering a negative balance (payroll.deductions).

## Evidence
Return:
- Employee ID and last day worked.
- Each balance used: hours, as-of date, source, any
  adjustment and its reason — and any other record's
  balance that differed.
- Rate, its effective date and source; the conversion
  method for salaried employees.
- Compliance's requirement and the policy terms applied.
- Hours × rate and amount for each leave type.
- Any exception applied, and why.
- Rule ID: payroll.leave-payout.

## To confirm with the team
- Does a policy's minimum length of service also apply
  when state law requires the payout?
- Over the plan's maximum: pay the capped hours, or stop?
- Flag names for the out-of-date balance, differing
  balances and unlimited leave.
