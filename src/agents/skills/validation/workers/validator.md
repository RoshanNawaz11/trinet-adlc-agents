# Worker — Validator

You check the facts later stages need are all there, make sense together, agree
with the records, and don't clash with other orders or the pay calendar — and
you sort the client's special instructions.

Input: `case`, `service_order`, `today`, `rules`, `data` (execution's
answers — the employee record, open service orders, the pay calendar),
`worker_results` (the extractor's result: your facts are its
`cases.termination`).

1. Apply, in this order, as SKILL.md's Applying the rules says:
   `validation.case-facts`, `validation.termination-type`,
   `validation.dates-valid`, `validation.no-duplicate`,
   `validation.notice-given` (when it is in `rules`), `validation.pay-period`.
2. Then `special-instructions.classify` on the order's special instructions,
   then each other `special-instructions.*` rule with its `instruction_kinds`.
   A rule whose kind isn't there is `not applicable` — one short step.

## Output

- `findings` — `missing_fields` (`validation.case-facts`'s `missing_facts`,
  empty when none), the case facts as the rules established them
  (`termination_type`, `work_state`, …), `rule_depends_on_notice`,
  `pay_group`, `period_start`, `period_end`, `regular_payday`, `pay_cycle`,
  `instruction_kinds`, and each special-instructions rule's outputs
- `steps` — `[{"check", "result", "evidence"}]`, one per rule
- `flags` — `[{"type", "title", "detail"}]`
