# Benefits

## Purpose
Decide whether the employee is benefits-eligible for the
final pay period, and what benefit cost is billed to the
client.

## Required data
- Benefits status codes and eligibility on record.
- Employment type (e.g. regular or temporary) and FTE.
- The plan's eligibility terms (e.g. minimum FTE).
- Coverage on the last day worked and the date it ends.
- Employer premium per pay period for each coverage.
- Whether the order asks to bill benefits to the client.
- Sources: payroll record, benefits coverage, the order.

## Condition
The case is a termination, and inputs-present passed.

## Required output

### The records give one clear answer
- benefits_eligible: true or false.

### The records point different ways
e.g. a temporary employee marked eligible, status codes
that disagree, or FTE on the edge of the plan's minimum.
- benefits_eligible: null
- Decision flag `benefitsAmbiguous`: option A (eligible)
  and option B (not eligible), each with its net pay; the
  recommendation names the option the records support
  best, and why.

### Benefits billed to the client
- The employer premiums for the final pay period, for
  each coverage active in it.

### No coverage
- benefits_billed_to_client: 0

### Required data is missing or conflicting
- result: not available
- benefits_eligible and benefits_billed_to_client: null
- Do not guess eligibility from pay type alone.

### Case is not a termination
- result: not applicable
- reason: The case is outside this rule's scope.

## Exceptions

### Coverage ended before the last day worked
- Nothing billed for the final period; note the end date.

### The employee waived coverage
- Not billed; benefits_billed_to_client: 0.

### The order asks to bill benefits to the client
- Bill the employee's share to the client as well,
  instead of deducting it.
- Decision flag — the analyst confirms.

### Coverage changed during the final period
- Bill each coverage for the part of the period it was
  active, as the payroll system gives it.
- Check flag when the system gives no figure.

### COBRA continuation
- Not billed here — Compliance reports the notices; the
  employee pays continuation premiums directly.

### The employee has died
- Coverage ends at death; dependants may continue it.
- Stop — an analyst handles the coverage end.

### The employee is a contractor
- result: not applicable
- Flag to confirm the classification, then stop.

## Output
- result: pass, not available or not applicable
- benefits_eligible: true, false, or null if unresolved
- benefits_billed_to_client: amount, or null if
  unresolved
- billing_lines: per coverage, the premium and period
- flags: issues requiring acknowledgement or review

## Not included
Benefit deductions from the employee's pay
(payroll.deductions), and COBRA notices (Compliance).

## Evidence
Return:
- Employee ID and final pay period.
- Status codes, employment type, FTE and the plan's
  terms used.
- Each coverage: premium, active dates and source.
- Any exception applied, and why.
- Rule ID: payroll.benefits.

## To confirm with the team
- Eligibility: from status codes and FTE (team's rule),
  or from the record's eligibility against employment
  type (what our agents do today)?
- Flag name for a coverage change with no system figure.
