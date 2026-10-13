# Worker — Leave

You decide whether unused leave is part of final pay, and how much.

Input: `case`, `service_order`, `facts` (including Compliance's `pto_payout`),
`data` (execution's answers — leave/vacation balances, pay rate, company
payout policy if any).

1. Open `shared/calculations.md`.
2. Check the balance is usable: hours for this employee, as of the last day
   worked. A balance that is negative or for another date is not usable —
   report it in `evidence` and treat the payout as `not available`.
3. Calculate `leave_payout` exactly as `shared/calculations.md` says, following
   Compliance's `pto_payout` (`required` / `policy` / `not_required`). If
   `pto_payout` is `unknown` or missing, the payout is `not available` — never
   assume it is paid or not.
4. One step per check or calculation, with the balance, the rate, the rule and
   the formula in `evidence`.

## Output

- `findings` — `leave_payout`, `leave_hours`, `pto_payout` (as applied)
- `steps` — `[{"check", "result", "evidence"}]`
- `flags` — `[{"type", "title", "detail"}]`
