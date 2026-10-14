# Payment Change

## Purpose
Handle an instruction that changes how or where final
pay is delivered — the payment method or the delivery.

## Applies to
- state: any
- pay_group: any
- employment_type: any
- termination_type: any
- delivery: any

## Required data
- The instruction's text.
- The payment method on file.
- The method the state requires for this termination
  type, from Compliance.
- Sources: the order, payroll record, Compliance's
  result.

## Condition
special-instructions.classify gave this kind.

## Required output

### Recognise it
e.g. "Pay by live check, not direct deposit", "Mail to a
new address", "Hold for pickup", "Send to HQ, attention
HR".

### The instruction changes the method or delivery
- result: not available
- Stop — it overrides payroll.payment-method; an analyst
  decides.

## Exceptions

### It asks for what is already required or on file
e.g. "Live check — hand to employee at exit meeting"
where the state requires a live check at discharge, or
"Direct deposit" when that is the method on file.
- It changes nothing: note it; the case continues.

### It contradicts the law
e.g. direct deposit where the state requires a live
check at discharge.
- Stop — the law wins; an analyst tells the client.

## Output
- result: pass, not available or not applicable
- outcome: stop or note
- overrides: payroll.payment-method
- flags: issues requiring acknowledgement or review

## Evidence
Return:
- The instruction's exact text.
- The method on file and the state's required method,
  with sources.
- Why it is a change, or why it matches.
- Rule ID: special-instructions.payment-change.
