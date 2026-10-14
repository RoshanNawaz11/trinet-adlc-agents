# Pay Date Change

## Purpose
Handle an instruction that changes when final pay is
paid.

## Applies to
- state: any
- pay_group: any
- employment_type: any
- termination_type: any
- delivery: any

## Required data
- The instruction's text.
- Compliance's final-pay due date and pay timing.
- Sources: the order, Compliance's result.

## Condition
special-instructions.classify gave this kind.

## Required output

### Recognise it
e.g. "Pay on the last day", "Pay early", "Pay with the
next regular payroll".

### The instruction changes the pay date
- result: not available
- Stop — it overrides Compliance's due date, pay timing
  and submit-by; an analyst decides.

## Exceptions

### It asks for the date that is already due
e.g. "Pay on the last day" where the state already
requires that.
- It changes nothing: note it; the case continues.

### It asks for a date later than the law allows
- Stop — the law wins; an analyst tells the client.

## Output
- result: pass, not available or not applicable
- outcome: stop or note
- overrides: Compliance's due date, pay timing, submit-by
- flags: issues requiring acknowledgement or review

## Evidence
Return:
- The instruction's exact text.
- Compliance's due date and its rule.
- Why it is a change, or why it matches.
- Rule ID: special-instructions.pay-date-change.
