# Rule Applies

## Purpose
Find the approved rule that applies to this case for a
topic: final pay, leave payout, or health-coverage
continuation.

## Required data
- The topic.
- Work state, and any local jurisdiction.
- Termination type and employment type, from
  Validation.
- The client's headcount.
- The rule catalogue's rules for that state and topic:
  text, effective and expiry dates, employment types
  covered, minimum headcount, source.
- Rules come only from the rule catalogue, never from
  memory.
- Sources: the rule catalogue, the client account,
  Validation's result.

## Condition
Validation has returned the work state and termination
type.

## Required output

### Exactly one rule applies
- result: pass
- Return the rule, its text and its source.

### No rule for the state and topic
- result: fail
- Stop — flag `missingData` (rule: the topic).
- Never fill the gap from memory.

### The rule has expired, or isn't in effect yet
On the termination date.
- Ignore it. If no other rule applies, treat it as no
  rule.

### The rule doesn't cover this employment type
- Ignore it.

### The client is below the rule's minimum headcount
- The rule doesn't apply. Note it — e.g. below the
  federal minimum, a state continuation rule may apply
  instead (compliance.cobra).

### Headcount is missing and the rule has a minimum
- result: not available
- Stop — flag `missingData` (headcount).

### Work state is missing
- result: not available
- No flag of its own — Validation names it.

## Exceptions

### A federal and a state rule both apply
- Return both. The topic's rule decides which governs
  (e.g. the earlier deadline).

### The local jurisdiction has its own rule
- Apply it alongside the state's.
- A local jurisdiction with no rule in the catalogue →
  stop, flag `missingData` (local rule).

### Two current rules for the same state and topic
They say different things.
- result: not available
- Flag — the analyst picks.

### The employee worked in two states in the final period
- Find the rules for both states.
- Flag — the analyst confirms which applies.

### The employee is a contractor
- Employee rules don't apply. result: not applicable
- Payroll flags the classification.

## Output
- result: pass, fail, not available or not applicable
- rules: per topic, the text, source, jurisdiction, and
  effective and expiry dates
- flags: issues requiring acknowledgement or review

## Evidence
Return:
- Topic, and the state, types and headcount used.
- Each rule considered, and why it was kept or ignored.
- Each rule's source.
- Rule ID: compliance.rule-applies.

## To confirm with the team
- No rule: `missingData` (this rule), or a separate
  `noRule` flag (team doc)?
