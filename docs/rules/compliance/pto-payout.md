# PTO Payout

## Purpose
Work out what the law requires for unused leave at
termination.

## Required data
- The state's leave-payout rule, from
  compliance.rule-applies.
- The company's payout policy, if on file: whether it
  pays out, for which leave types, minimum length of
  service, and any forfeiture terms.
- Termination type, from Validation.
- Rules come only from the rule catalogue, never from
  memory.
- Sources: the rule catalogue, company policies,
  Validation's result.

## Condition
compliance.rule-applies has looked for the rule.

## Required output

### The law requires payout
- pto_payout: required
- It overrides the company policy.

### The law defers to company policy
- pto_payout: policy
- Report what the policy promises: whether it pays out,
  for which leave types, and its minimum length of
  service.

### The law defers to policy, and none is on file
- result: fail
- Stop — flag `missingData` (company payout policy).

### The law doesn't require it, and there's no policy
- pto_payout: not_required

### The rule's text is unclear
- pto_payout: unknown
- result: not available
- Flag — the analyst confirms.

### No leave-payout rule for the state
- pto_payout: unknown
- result: not available — compliance.rule-applies flags
  the missing rule.
- Never assume it is or isn't required.

## Exceptions

### Sick leave and floating holiday
- Report them separately when the rule or policy treats
  them differently. Otherwise not required.

### The law requires payout but the policy says no
- pto_payout: required — the law wins.
- Note the conflict.

### The state forbids forfeiting earned leave
A "use it or lose it" policy.
- Earned leave is required; note it.

### The policy forfeits leave on some exits
e.g. dismissed for cause.
- Report the condition. It applies only when pto_payout
  is policy.

### The policy gives unlimited leave
- Report it; payroll.leave-payout decides what is owed.

### A special instruction changes the payout
- Stop — the special-instructions rules apply.

## Output
- result: pass, fail or not available
- pto_payout: required, policy, not_required or unknown
- by_leave_type: the requirement for each type, when
  they differ
- policy_terms: what the policy promises, or null
- flags: issues requiring acknowledgement or review

## Evidence
Return:
- The rule's text and source.
- The policy's terms and source.
- Rule ID: compliance.pto-payout.
