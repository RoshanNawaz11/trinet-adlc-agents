# COBRA

## Purpose
Work out the health-coverage continuation duties after
termination, and their deadlines.

## Required data
- Whether health coverage was active on the last day
  worked, and when it ends.
- The client's headcount.
- The federal continuation rule and any state
  continuation rule, from compliance.rule-applies.
- Last day worked and termination type, from Validation.
- Rules come only from the rule catalogue, never from
  memory.
- Sources: benefits coverage, the client account, the
  rule catalogue, Validation's result.

## Condition
Validation has returned the last day worked.

## Required output

### No health coverage on the last day
- cobra: not_applicable
- result: pass

### Coverage, and the client meets the federal minimum
- cobra: required
- The notices and deadlines the rule gives — e.g. the
  plan notified within 30 days, the election notice
  within 44 days.
- Take the counts from the rule, never from memory.

### Coverage, and the client is below the federal minimum
- A state continuation rule applies if there is one:
  its notices and deadlines.
- None → cobra: not required. Note it.

### Coverage data is missing
- cobra: unknown
- Note it for the Benefits team.

### Headcount is missing
- result: not available
- Flag `missingData` (headcount).

## Exceptions

### Terminated for gross misconduct
The law may allow denying continuation.
- Report it.
- Decision flag — the analyst decides. Never decide it
  yourself.

### The employee has died
- Covered dependents are owed the notices. Note it.

### Coverage ends later than the last day
e.g. at the end of the month.
- Count from the date the rule names. Note both dates.

### Only dependents are covered
- Still required, for them.

### The employer pays the premiums under a severance agreement
- A special instruction, not this rule. Note it.

### The employee is a contractor
- result: not applicable

## Output
- result: pass, not available or not applicable
- cobra: required with its notices ({notice, due date,
  rule}), not required, not_applicable, or unknown
- passed_to: the Benefits team
- flags: issues requiring acknowledgement or review

## Not included
Premiums and who is billed (payroll.benefits,
payroll.deductions).

## Evidence
Return:
- Coverage on the last day, and its source.
- Headcount and its source.
- Each rule's text and source, and each deadline
  worked out.
- Rule ID: compliance.cobra.

## To confirm with the team
- Coverage data missing: unknown (this rule), or stop?
