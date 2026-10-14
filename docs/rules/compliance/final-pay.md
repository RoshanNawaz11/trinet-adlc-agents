# Final Pay

## Purpose
From the state's final-pay rule, work out when final
pay is legally due, whether the regular payday meets
it, which payment methods are allowed, and who is paid
if the employee has died.

## Required data
- The state's final-pay rule, from
  compliance.rule-applies.
- Termination type, notice given, termination date and
  last day worked, from Validation.
- The next regular payday and pay cycle, from
  validation.pay-period.
- Today's date.
- Rules come only from the rule catalogue, never from
  memory.
- Sources: the rule catalogue, Validation's result.

## Condition
compliance.rule-applies found the final-pay rule.

## Required output

### Which part of the rule
- Involuntary → the rule's text for a discharge.
- Voluntary → the rule's text for a resignation, with
  or without notice where the rule says so.

### The rule only speaks of the other type
- result: not available
- Flag `missingData` (final-pay rule for this type).
- Never apply a discharge deadline to a resignation, or
  the reverse.

### The due date
Count from the date the rule names (discharge,
resignation, termination). If it names none, count from
the last day worked. Apply the rule's form exactly:

| Form | Due |
|---|---|
| immediately, same day, at termination | that date |
| within N hours | that date and time + N hours |
| next business day | the next Monday–Friday after it |
| N calendar days | that date + N days |
| N business days | that date + N Monday–Friday days |
| next regular payday | the payday from validation.pay-period |

- Wording that fits no form clearly → result: not
  available.

### The rule depends on notice, and notice is unknown
- result: not available
- Wait — validation.termination-type raises the input
  flag.

### Due on or after the regular payday
- pay_timing: on-cycle
- result: pass

### Due before the regular payday
- pay_timing: off-cycle
- Flag `complianceTiming` — the rule, the due date and
  the regular payday.

### Already overdue
The due date is before today.
- overdue: true
- Note how late it is. compliance.submit-by raises the
  risk flag.

### Payment methods allowed
- From the rule, for this termination type: the methods
  allowed and any conditions (e.g. the employee's
  consent, a check handed over at termination).
- The rule doesn't say → allowed_payment_methods: null.

### Required data is missing
- result: not available
- Do not guess a date or a method.

## Exceptions

### The employee has died
- Due date and payee from the rule's text for a death:
  the estate or the surviving spouse.
- Stop — an analyst handles the payment.

### The rule has its own text for a layoff
- Use it instead of the discharge text.

### Resigned with enough notice
Some rules pay on the last day when enough notice was
given.
- Use that branch when notice is yes.

### The due date falls on a weekend or holiday
- Apply what the rule says. If it says nothing, don't
  shift the date; note it.

### The employee worked in two states
- Use the earlier due date.
- Flag — the analyst confirms.

### Late pay carries a penalty
The rule mentions penalties for late final pay.
- Note the penalty when overdue or off-cycle.

## Output
- result: pass, not available or not applicable
- final_pay_rule: text and source
- final_pay_due_date: date, and time when the rule
  counts hours
- standard_pay_date: the regular payday
- pay_timing: on-cycle, off-cycle or unknown
- overdue: true or false
- allowed_payment_methods: methods and conditions, or
  null
- death_payee: who is paid if the employee died, or null
- flags: issues requiring acknowledgement or review

## Not included
The time to submit by (compliance.submit-by), and the
method on file (payroll.payment-method).

## Evidence
Return:
- The rule's text used, and its source.
- Termination type and notice.
- From-date, form and result.
- The regular payday and its source.
- Rule ID: compliance.final-pay.

## To confirm with the team
- Count from the last day worked (team rule C4) or the
  termination date (our agents today) when the rule
  names no date?
- Overdue: a note (team doc), or a flag?
