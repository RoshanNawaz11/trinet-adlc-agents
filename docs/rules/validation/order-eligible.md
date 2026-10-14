# Order Eligible

## Purpose
Decide whether a service order is a termination that
should be worked now.

## Required data
- The order's case type and status.
- The order's description — only when the case type is
  missing.
- Sources: the service order.

## Condition
Any service order.

## Required output

### Termination order, open
- result: pass
- Continue to the other validation rules.

### Not a termination
- result: not applicable
- Skip the order — no agent works it.

### Order is closed or cancelled
- result: fail
- Stop — flag `orderNotOpen` with the status.

### Case type is missing
- Use the description only if it clearly says this is a
  termination.
- Otherwise result: not available — flag `missingData`
  (case type).

### Case type and description disagree
- result: not available
- Input flag — the analyst picks.
- Do not choose one yourself.

## Exceptions

### Order is pending or on hold
Any status other than closed or cancelled is open.
- result: pass

### One order terminates several employees
- result: fail
- Stop — each employee needs their own order.

### Order reverses a termination
"Cancel the termination", "Employee is staying".
- result: not applicable
- Stop — an analyst handles it.

### Order mixes a termination with other work
e.g. a termination and an address change.
- Work only the termination.
- Note the other work in evidence.

## Output
- result: pass, fail, not available or not applicable
- eligible: true, false, or null if unresolved
- case_type and order_status as read
- flags: issues requiring acknowledgement or review

## Evidence
Return:
- Service order ID.
- Case type and status used, and their source.
- The description text used, if any.
- Rule ID: validation.order-eligible.
