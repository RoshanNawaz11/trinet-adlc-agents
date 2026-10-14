# Deduction Request

## Purpose
Handle an instruction that asks to deduct something from
final pay.

## Applies to
- state: any
- pay_group: any
- employment_type: any
- termination_type: any
- delivery: any

## Required data
- The instruction's text, and any amount it states.
- Sources: the order.

## Condition
special-instructions.classify gave this kind.

## Required output

### Recognise it
e.g. unreturned laptop, salary advance, negative PTO.

### The instruction asks for a deduction
- Leave it out of payroll.deductions.
- result: not available
- Stop — legal limits apply and a signed agreement is
  needed; an analyst decides.

## Output
- result: not available or not applicable
- outcome: stop
- deduction: what, and the amount as stated or null
- overrides: payroll.deductions
- flags: issues requiring acknowledgement or review

## Evidence
Return:
- The instruction's exact text.
- What is to be deducted, and the amount as stated.
- Rule ID: special-instructions.deduction-request.
