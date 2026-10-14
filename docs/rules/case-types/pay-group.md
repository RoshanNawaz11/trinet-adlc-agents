# Pay Group

## What
How often the employee is paid. It decides the final pay
period, the next regular payday, the salary per period
and the payroll cut-offs.

## Values
weekly, biweekly, semi-monthly, monthly.

## Source
The payroll record's pay group. The pay calendar for that
pay group gives the periods, pay dates and cut-offs.

## How it reaches the rules
As facts from the pay calendar:
- the final pay period: the period containing the last
  day worked
- the next regular payday after the last day worked
- the change deadline for that period

As a case in a rule only where the arithmetic depends on
the frequency (salary per period).

## Effect by value

| Value | Periods per year | Final period | Salary per period |
|---|---|---|---|
| weekly | 52 | the week containing the last day worked | annual ÷ 52 |
| biweekly | 26 | the two weeks containing it | annual ÷ 26 |
| semi-monthly | 24 | the half-month containing it (1st–15th or 16th–end) | annual ÷ 24 |
| monthly | 12 | the month containing it | annual ÷ 12 |

Always take the periods and pay dates from the pay
calendar — the table only explains them; never build a
calendar from it.

Rules it changes:
- payroll.inputs-present — hours are needed for the
  final period
- payroll.earnings — the period, and salary per period
  for proration
- payroll.leave-payout — the balance must be as of the
  last day worked, inside the final period
- payroll.benefits and payroll.deductions — premiums and
  deductions are per pay period
- payroll.payment-method — the cut-offs come from the
  calendar
- Compliance — "next regular payday" and "end of the pay
  period" deadlines

## Gaps the data shows
- The pay group's name holds the frequency and the
  state (e.g. a biweekly Texas group). Match the period
  by dates in the calendar, never by the name.
- One employee in the mock data (IL) has no pay group:
  the final period and payday are not available.

## Orders in the mock data
| Value | Orders |
|---|---|
| weekly | SO-20260930-1003 (NY) |
| biweekly | SO-20260930-1001 (TX), SO-20260925-1005 (WA), SO-20261016-1006 (FL), SO-20261023-1007 (AZ) |
| semi-monthly | SO-20261002-1002 (CA) |
| none | SO-20260930-1004 (IL) |
