# Additional Pay

## Purpose
Handle an instruction that adds pay to the final check,
or asks for part of it on its own check.

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
e.g. severance, bonus, commission, expense
reimbursement; "Put the bonus on its own check".

### The instruction adds pay
- Leave it out of payroll.earnings.
- Decision flag — the analyst confirms the amount.

### The instruction asks for a separate check
- Decision flag — the analyst confirms the split.
- payroll.net-pay then works out each check.

## Exceptions

### No amount is stated
- Decision flag — the analyst supplies the amount.
- Never estimate it.

## Output
- result: pass, not available or not applicable
- outcome: decision flag
- pay_type: severance, bonus, commission, reimbursement
  or other
- amount: as stated, or null
- separate_check: true or false
- overrides: payroll.earnings
- flags: issues requiring acknowledgement or review

## Evidence
Return:
- The instruction's exact text.
- The pay type and amount as stated.
- Rule ID: special-instructions.additional-pay.
