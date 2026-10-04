# Worker — Calculations

How every amount a case can ask for is computed. A case file only names
calculations from this list. A calculation whose inputs are missing is
`not available` — never fill an input with a guess.

| Calculation | Inputs | How |
|---|---|---|
| `regular_pay` | regular hours, hourly rate — or salary per period, days worked in the period, working days in the period | hourly: hours × rate. Salaried: salary per period × days worked ÷ working days |
| `overtime_pay` | overtime hours, hourly rate, overtime multiplier (from the payroll system) | hours × rate × multiplier |
| `gross_pay` | the case's earnings items | the sum of them |
| `leave_payout` | unused leave hours, hourly rate, payout requirement from Compliance | hours × rate when the requirement is `required` (or `policy` and the company policy pays out); 0 when `not_required` |
| `taxes` | the payroll system's withholding figures for this pay | as returned — never compute tax rates yourself |
| `deductions` | the employee's deductions for this pay | the sum of the amounts returned |
| `net_pay` | gross pay, leave payout, taxes, deductions | gross pay + leave payout − taxes − deductions |
| `first_pay_date` | start date, pay calendar | the first regular payday whose pay period includes the start date |

Rules:

- Round each amount to cents; round only the result, not the inputs.
- Put every input, its source and the formula in the step's `evidence`.
