# Death

## Purpose
Handle an instruction that reports the employee's death.

## Applies to
- state: any
- pay_group: any
- employment_type: any
- termination_type: any
- delivery: any

## Required data
- The instruction's text.
- The order's termination reason.
- Who final wages go to in the work state, from
  Compliance.
- Sources: the order, Compliance's result.

## Condition
special-instructions.classify gave this kind.

## Required output

### Recognise it
e.g. "Pay final wages to the estate", "Mail to estate
representative".

### The instruction reports a death
- result: not available
- Stop — the payee changes to the estate or surviving
  spouse, as the state's rule says; an analyst handles
  the payment.

## Exceptions

### The order's termination reason also says death
- One case, not two: raise it once.

### The termination reason doesn't say death
- Stop as above, and input flag — the analyst confirms
  the reason.

## Output
- result: not available or not applicable
- outcome: stop
- payee: as the instruction and the state's rule say, or
  null
- overrides: the payee
- flags: issues requiring acknowledgement or review

## Evidence
Return:
- The instruction's exact text.
- The order's termination reason.
- The state's rule on who is paid.
- Rule ID: special-instructions.death.

## To confirm with the team
- Should death be one shared rule, used both here and
  when only the termination reason says death?
