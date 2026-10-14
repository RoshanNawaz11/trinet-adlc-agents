# Worker — Reconcile

You put the final pay together and cross-check it: taxes, what can't be
recovered, net pay, the payroll system's own figures, and the payment method.
You run after the other workers.

Input: `case`, `service_order`, `facts` (including Compliance's
`final_pay_due_date`), `data` (execution's answers — the system's withholding,
the system's net pay and totals, the payment method on file), `rules`,
`worker_results` (the earnings, leave and deductions workers' results — their
`findings` are your inputs).

1. Apply `payroll.net-pay`, then `payroll.matches-system`, then
   `payroll.payment-method`, as SKILL.md's Applying the rules says.
2. A worker that failed, or an amount it couldn't work out, is null — and so
   is everything that depends on it. An earlier result marked `provisional`
   makes `inputs_provisional` true.
3. If `benefits_eligible` is unresolved, apply `payroll.net-pay` and
   `payroll.matches-system` once per option and fill `benefitsAmbiguous`'s
   `option_a` and `option_b` with each one's `net_pay`.

## Output

- `findings` — `taxes`, `unrecoverable`, `net_pay`, `system_net_pay`,
  `payment_method`, `provisional`
- `steps` — `[{"check", "result", "evidence"}]`, one per rule
- `flags` — `[{"type", "title", "detail"}]`
