# No Payroll Effect

## Purpose
Handle an instruction that has nothing to do with pay.

## Applies to
- state: any
- pay_group: any
- employment_type: any
- termination_type: any
- delivery: any

## Required data
- The instruction's text.
- Sources: the order.

## Condition
special-instructions.classify gave this kind.

## Required output

### Recognise it
e.g. "Revoke systems access", "Laptop returned".

### The instruction has no payroll effect
- result: pass
- Note it; the case continues.

## Exceptions

### It could affect pay after all
e.g. "Laptop not returned" may lead to a deduction
request.
- Classify it as that kind instead.

## Output
- result: pass or not applicable
- outcome: note
- flags: none

## Evidence
Return:
- The instruction's exact text.
- Rule ID: special-instructions.no-payroll-effect.
