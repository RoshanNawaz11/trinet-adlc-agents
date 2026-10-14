# Termination Type

## Purpose
Map the termination reason to a type, and find out
whether notice was given when the state's rule depends
on it.

## Required data
- The termination reason: the order's field, or the
  description when there is no field.
- Whether notice was given, as the order says.
- Whether the state's final-pay rule depends on notice,
  from Compliance.
- Sources: the service order, Compliance's result.

## Condition
case-facts has returned the reason.

## Required output

### Voluntary
Voluntary, resigned, quit, retired.
- termination_type: voluntary

### Involuntary
Involuntary, fired, discharged, laid off, layoff,
reduction in force, let go, terminated for cause.
- termination_type: involuntary

### The reason doesn't map clearly
e.g. "Mutual agreement", "End of contract".
- termination_type: unknown
- Input flag — the analyst selects voluntary or
  involuntary.
- Never guess a type.

### Notice
- yes — only if the order says notice was given.
- no — only if the order says none was given.
- Otherwise unknown.

### Notice is unknown and the state's rule depends on it
- result: not available
- Input flag — the analyst confirms.

### Notice is unknown and the rule doesn't depend on it
- result: pass

## Exceptions

### The employee has died
- termination_type: death — neither voluntary nor
  involuntary.
- Stop — the payee becomes the estate; an analyst
  handles it.

### End of a temporary assignment
- termination_type: unknown
- Input flag — the analyst selects.

### Released during the notice period
The employee resigned, but the employer ended it before
the notice ran out — some states treat this as a
discharge.
- termination_type: unknown
- Input flag — the analyst selects.

### Job abandonment
No-call, no-show.
- termination_type: unknown
- Input flag — the analyst selects.

### The reason field and the description disagree
- Input flag — the analyst picks.

## Output
- result: pass, not available or not applicable
- termination_type: voluntary, involuntary, death or
  unknown
- termination_reason_text: as written
- notice_given: yes, no or unknown
- flags: issues requiring acknowledgement or review

## Evidence
Return:
- The reason text, its source, and the mapping applied.
- The notice text, if any, and its source.
- Whether the state's rule depends on notice, and its
  source.
- Rule ID: validation.termination-type.

## To confirm with the team
- A `death` type: the other agents only know voluntary,
  involuntary and unknown today.
- Released during the notice period: unknown (this
  rule), or involuntary?
