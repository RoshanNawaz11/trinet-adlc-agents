# Sensitive Handling

## Purpose
Handle an instruction that calls for sensitive handling
of the case.

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
e.g. "Legal hold", "Do not contact the employee".

### The instruction calls for sensitive handling
- result: not available
- Stop — an analyst handles the case.

## Output
- result: not available or not applicable
- outcome: stop
- handling: what the instruction asks for
- flags: issues requiring acknowledgement or review

## Evidence
Return:
- The instruction's exact text.
- Rule ID: special-instructions.sensitive-handling.
