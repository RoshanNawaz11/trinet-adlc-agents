# Confirmation Needed

## Purpose
Handle an instruction that says another team must
confirm something before the case can be finished.

## Applies to
- state: any
- pay_group: any
- employment_type: any
- termination_type: any
- delivery: any

## Required data
- The instruction's text: who must confirm, and what.
- Sources: the order.

## Condition
special-instructions.classify gave this kind.

## Required output

### Recognise it
e.g. "Benefits to confirm coverage end", "Client manager
to confirm final hours".

### The instruction names a team and an input
- The input it names is not available until they answer.
- Wait — the analyst chases the answer.
- Everything that doesn't depend on that input carries on.

## Exceptions

### The instruction doesn't say what must be confirmed
- Decision flag — the analyst finds out.

## Output
- result: not available until the answer arrives
- outcome: wait
- waiting_for: the team, and the input it must confirm
- flags: issues requiring acknowledgement or review

## Evidence
Return:
- The instruction's exact text.
- The team and the input named.
- Rule ID: special-instructions.confirmation-needed.
