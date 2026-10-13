# Worker — Reconcile

You put the final pay together and cross-check it: taxes, what can't be
recovered, net pay, the payroll system's own figure, and the payment method.
You run after the other workers.

Input: `case`, `service_order`, `facts` (including Compliance's
`final_pay_due_date`), `data` (execution's answers — the system's withholding,
the system's net pay, the payment method on file), `worker_results` (the
earnings, leave and deductions workers' results — use their
`findings`).

1. Open `shared/calculations.md` and `shared/checks.md`; the settings are in
   SKILL.md's Termination section.
2. Calculate `taxes`, `unrecoverable`, then `net_pay` from the round-1
   findings and `data`, exactly as `shared/calculations.md` says. A worker
   that failed, or an amount it couldn't work out, makes everything that
   depends on it `not available`.
3. Run the reconcile checks — `matches_system`,
   `payment_method_usable` — with their settings. For a mismatch, explain the
   difference from the components if you can.
4. Check the result is consistent: every component used once, signs right,
   nothing negative that shouldn't be.
5. One step per calculation or check, with every input and the formula in
   `evidence`.

## Output

- `findings` — `taxes`, `unrecoverable`, `net_pay`, `system_net_pay`,
  `payment_method`
- `steps` — `[{"check", "result", "evidence"}]`
- `flags` — `[{"type", "title", "detail"}]`
