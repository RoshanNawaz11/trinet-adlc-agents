# PG-001 — Identify the Payroll Period

## Purpose
Identify the payroll period containing the last day
worked for a WSE termination.

## Required data
- Employee pay group.
- Last day worked.
- Payroll calendar assigned to that pay group.
- Sources: employee payroll record, validated case facts,
  and payroll calendar.

## Condition
Pay group equals "WEEKLY" OR "BIWEEKLY".

## Required output

### Condition matches
Find the period in the matching calendar where:
period start date ≤ last day worked ≤ period end date.

If exactly one period matches, return:
- status: resolved
- period_start_date: matched period's start date
- period_end_date: matched period's end date
- scheduled_pay_date: matched period's pay date
- calendar_id: calendar used

### Condition does not match
- status: not_applicable
- reason: The pay group is outside this rule's scope.
- Do not select a weekly or biweekly calendar.

### Required data is missing or conflicting
- status: unresolved
- reason: Identify the missing or conflicting data.
- Do not guess the pay group, calendar, or dates.

### No period or multiple periods match
- status: unresolved
- reason: A unique payroll period could not be identified.
- Do not select a period arbitrarily.

## Evidence
Return:
- Employee pay group.
- Last day worked.
- Calendar and period identifiers, when available.
- Sources of the input values.
- Rule ID: PG-001.