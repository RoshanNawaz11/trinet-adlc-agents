---
name: execution
description: >
  Use this skill when the Execution Agent (Stage 4) receives a termination
  service order after every other agent has finished. Prepares the final
  payment package for a person to act on. It does not submit payroll or write
  to any system.
  Read its files with the text editor's view command only; never run bash
  commands or write code.
---

# SKILL: Package Preparation (Stage 4)
**Chain position:** orchestrator → validation → payroll calculation → compliance → **execution** → review
**Runs at:** last of the agents. The reviewer then sees every result, flag and
this package, and accepts or declines the whole run.

---

## Inputs

- `service_order` — the order
- `data` — everything fetched or answered for the other agents during the run
- `previous_results` — Validation, Compliance and Payroll Calculation outputs
- `flags` — every flag the agents raised; the reviewer sees them all, with
  this package, when deciding on the run

## What this stage does — and does not do

- It **prepares** the package and nothing else.
- It **never** submits a payroll run, pays anyone, creates a record, or updates
  Salesforce or any other system, even if a tool for that is available. A
  person acts on the package afterwards.

## Steps

1. **Build the payment package** from the other agents' outputs
   (`previous_results.<agent>.cases.termination`), as listed below.
2. **Apply each flag's `answer`** — the analyst answered every flag during the
   run, by accepting its suggested fix or typing their own. The answer decides
   the outcome; the reviewer still decides on the whole run afterwards, and
   nothing is acted on before then. For example `complianceTiming` → pay by the
   date the answer gives; `paymentMethodFail` → use the method the answer
   names. An answer that only acknowledges (a check) changes nothing. Record
   one step per flag applied.
3. **Check the package is complete** — every field it requires is known. If
   any is missing, the package status is `blocked`.
4. **Special instructions** — carry Validation's special delivery instructions
   into the package.

## Payment package

From Payroll Calculation and Compliance.

- `net_pay` — number in USD, or null *(required)*
- `payment_method` — `direct_deposit` or `check`, or null *(required)*
- `pay_date` — ISO date, the final-pay due date, or null *(required)*

## Rules

- Never invent a value; take every figure from the inputs.
- Don't write or run code. Use the MCP tools to look things up; everything
  else is already in your input — read it and answer directly.
- Do not raise flags — flags are the other agents' job. Report problems through the
  package `status` and `blocked_reason`.

## Output

- `packages` — `{"termination": {<the payment package fields>}}`
- `special_instructions` — text or null
- `decisions_applied` — list of `{"flag_id", "type", "effect"}`
- `status` — `ready` or `blocked`
- `blocked_reason` — text when blocked, else null
