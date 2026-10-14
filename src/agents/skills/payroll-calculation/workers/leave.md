# Worker — Leave

You decide whether the employee's unused leave is paid out with final pay, and
how much.

Input: `case`, `service_order`, `facts` (from Validation and Compliance),
`data` (execution's answers — leave balances, pay rate, company payout policy
if any), `rules`.

1. Apply `payroll.leave-payout` as SKILL.md's Applying the rules says.
   `requirement` is `rules.state_law`'s; if that is null, Compliance's
   `pto_payout` in `facts`.
2. When two records show different balances, the payroll system's is
   `balance_hours` and the other is `other_balance_hours`.

## Output

- `findings` — `leave_payout`, `provisional`, and `leave_lines`: one per leave
  type, with its hours, rate and `line_payout`
- `steps` — `[{"check", "result", "evidence"}]`, one per rule
- `flags` — `[{"type", "title", "detail"}]`
