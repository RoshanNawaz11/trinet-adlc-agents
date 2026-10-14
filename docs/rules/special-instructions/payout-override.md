# Payout Override

## Purpose
Handle an instruction that overrides the leave payout.

## Applies to
- state: any
- pay_group: any
- employment_type: any
- termination_type: any
- delivery: any

## Required data
- The instruction's text.
- Compliance's payout requirement.
- Sources: the order, Compliance's result.

## Condition
special-instructions.classify gave this kind.

## Required output

### Recognise it
e.g. "Don't pay out PTO", "Pay out despite policy".

### The instruction changes the payout
- result: not available
- Stop — it overrides Compliance's payout requirement
  and payroll.leave-payout; an analyst decides.

## Exceptions

### It asks for what is already required
e.g. "Pay out PTO" where the state requires the payout.
- It changes nothing: note it; the case continues.

### It asks not to pay where the law requires the payout
- Stop — the law wins; an analyst tells the client.

## Output
- result: pass, not available or not applicable
- outcome: stop or note
- overrides: Compliance's payout requirement,
  payroll.leave-payout
- flags: issues requiring acknowledgement or review

## Evidence
Return:
- The instruction's exact text.
- Compliance's payout requirement and its rule.
- Why it is a change, or why it matches.
- Rule ID: special-instructions.payout-override.
