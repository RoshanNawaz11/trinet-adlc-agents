# Calculations

How every amount a case can ask for is computed, and which worker computes it.
A case file only names calculations from this list. A calculation whose inputs
are missing is `not available` — never fill an input with a guess.

| Calculation | Worker | Inputs | How |
|---|---|---|---|
| `regular_pay` | earnings | regular hours, hourly rate — or salary per period, days worked in the period, working days in the period | hourly: hours × rate. Salaried: salary per period × days worked ÷ working days |
| `overtime_pay` | earnings | overtime hours, hourly rate, overtime multiplier (from the payroll system) | hours × rate × multiplier |
| `gross_pay` | earnings | the case's earnings items | the sum of them |
| `leave_payout` | leave | unused leave hours, hourly rate, payout requirement from Compliance | hours × rate when the requirement is `required` (or `policy` and the company policy pays out); 0 when `not_required` |
| `deductions` | deductions | the employee's deductions for this pay, benefits eligibility | the sum of the amounts that apply — benefit deductions only if eligible |
| `garnishments` | deductions | active garnishment orders, their withholding rules (from the payroll system) | the amount each order takes from this pay, as the system's rules give it — never compute a legal limit yourself |
| `benefits_billed_to_client` | deductions | benefit premiums the employee no longer pays from final pay | the amounts the client is billed instead |
| `taxes` | reconcile | the payroll system's withholding figures for this pay | as returned — never compute tax rates yourself |
| `unrecoverable` | reconcile | gross pay, leave payout, taxes, deductions, garnishments | what can't be taken from this pay because it would go below zero or past a limit the system gives; reported, and left out of `net_pay` |
| `net_pay` | reconcile | gross pay, leave payout, taxes, deductions, garnishments, unrecoverable | gross pay + leave payout − taxes − (deductions + garnishments − unrecoverable) |
| `first_pay_date` | setup | start date, pay calendar | the first regular payday whose pay period includes the start date |

Rules:

- Round each amount to cents; round only the result, not the inputs.
- Put every input, its source and the formula in the step's `evidence`.
- Amounts are numbers in USD; null for anything not available.
