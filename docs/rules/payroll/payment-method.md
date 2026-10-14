# Payment Method

## Purpose
Make sure the final pay can be paid the way it is set
up, as the state allows, and in time.

## Required data
- The payment method on file (direct deposit or check),
  its status, and whether a direct deposit account has
  been verified (prenote).
- The methods the state allows for this termination
  type, from Compliance.
- The final-pay due date and the latest time to submit
  it, from Compliance.
- The payment method's own cut-off (e.g. the bank file
  for direct deposit, same-day for a live check).
- The delivery the order asks for, and its special
  instructions.
- Sources: payroll record, Compliance's result, payroll
  cut-offs, the order.

## Condition
The case is a termination, and net-pay has returned a
result.

## Required output

### The method is usable
Active, verified (direct deposit), allowed by the state
for this termination type, and able to reach the
employee by the due date.
- result: pass
- payment_method: direct_deposit or check. The record
  may say it in words ("Direct Deposit", "Check").

### The method is inactive or not verified
- result: fail
- Decision flag `paymentMethodFail` — the current
  method, the reason, and a recommended method that
  works (usually a check).

### The state doesn't allow the method
e.g. the state requires a check handed over at
termination for a discharge.
- result: fail
- Decision flag `paymentMethodFail`, recommending the
  method the state requires.

### Direct deposit needs consent
The state allows direct deposit only with the
employee's consent.
- Consent on record → pass.
- No consent on record → decision flag
  `paymentMethodFail`, recommending a check.

### The method can't arrive by the due date
Its cut-off has passed or will pass first.
- result: fail
- Decision flag `paymentMethodFail`, recommending a
  method that still arrives in time (e.g. a live check).
- If no method arrives in time, don't raise it here —
  Compliance's cutoffRisk covers late payment.

### Required data is missing
- result: not available
- payment_method: null
- Do not assume the method is active, verified or
  allowed.

### Case is not a termination
- result: not applicable
- reason: The case is outside this rule's scope.

## Exceptions

### The order asks for a different method or delivery
"Pay by live check, not direct deposit", "Mail to a new
address", "Hold for pickup".
- result: not available
- Stop — the instruction overrides the method on file;
  an analyst decides.
- If the instruction asks for what is already required
  or on file (e.g. a live check where the state requires
  one), it changes nothing: note it and continue.

### A paper check is mailed
- The mailing address on record must be current.
- No current address → check flag.

### The employee has died
- The payee becomes the estate or surviving spouse, as
  the state's rule says.
- Stop — an analyst handles the payment.

### Part of the pay goes on a separate check
- Check the method for each check.

### The employee is a contractor
- result: not applicable
- Flag to confirm the classification, then stop.

## Output
- result: pass, fail, not available or not applicable
- payment_method: direct_deposit, check, or null if
  unresolved
- delivery: how it reaches the employee (deposit, check
  handed over, check mailed)
- pay_by: the date the payment must reach the employee
- flags: issues requiring acknowledgement or review

## Not included
The final-pay due date and submit-by time (Compliance),
and the amount (payroll.net-pay).

## Evidence
Return:
- Employee ID.
- The method on file: status, verification and source.
- The state's allowed methods and the rule's source.
- Due date, cut-off and how the method meets it.
- The order's delivery request and special instructions.
- Any exception applied, and why.
- Rule ID: payroll.payment-method.

## To confirm with the team
- Where the state's payment-method rules come from: the
  legal data has them per termination type, the team's
  rule catalogue doesn't (team question P11).
- A delivery instruction that matches what is already
  required: note, or stop?
