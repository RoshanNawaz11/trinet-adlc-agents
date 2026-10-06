---
name: execution
description: >
  Use this skill when the Execution Agent (Stage 4) receives a service order
  after every other agent has finished. Prepares the final package
  for a person to act on — the final payment for a termination, the setup
  package for an onboarding. It does not submit payroll or write to any system.
---

# SKILL: Package Preparation (Stage 4)
**Chain position:** orchestrator → validation → payroll calculation → compliance → **execution** → review
**Runs at:** last of the agents. The reviewer then sees every result, flag and
this package, and accepts or declines the whole run.

---

## Inputs

- `service_order` — the order
- `work` — the kinds of work the Planner found
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

1. **Pick the package** from `work`: `termination` → payment package,
   `onboarding` → onboarding package. One package per kind of work.
2. **Build it from the other agents' outputs** (`previous_results.<agent>.cases.<case>`),
   as listed below.
3. **Apply each flag's `recommendation`** as the proposed outcome — the
   reviewer decides on the whole run afterwards, and nothing is acted on before
   then. For example `complianceTiming` → pay by the earlier legal
   due date; `paymentMethodFail` → use the recommended method. A flag whose
   `recommendation` is null (a data problem, e.g. `missingData`) changes
   nothing — the field it names stays null. Record one step per flag applied.
4. **Check the package is complete** — every field it requires is known. If
   any is missing, the package status is `blocked`.
5. **Special instructions** — carry Validation's special delivery instructions
   into the package.

## Payment package — termination

From Payroll Calculation and Compliance.

- `net_pay` — number in USD, or null *(required)*
- `payment_method` — `direct_deposit` or `check`, or null *(required)*
- `pay_date` — ISO date, the final-pay due date, or null *(required)*

## Onboarding package — onboarding

From Validation, Compliance and Payroll Calculation. Items the new hire has
not provided yet (`setup_to_collect`, an I-9 not yet completed) are part of
the package as to-dos — they never make it `blocked`.

- `employee` — `{name, job_title, employment_type, work_state, start_date}` *(required)*
- `pay_setup` — `{pay_group, pay_rate, first_pay_date}` *(required)*
- `deadlines` — `{i9_due_date, new_hire_report_due_date}`, each with its rule
- `to_collect` — what the new hire must still provide (tax forms, payment
  method, I-9 documents)

## Rules

- Never invent a value; take every figure from the inputs.
- Don't write or run code. Use the MCP tools to look things up; everything
  else is already in your input — read it and answer directly.
- Do not raise flags — flags are the other agents' job. Report problems through the
  package `status` and `blocked_reason`.

## Output

- `packages` — `{<case>: {<that package's fields>}}` for every kind of work
- `special_instructions` — text or null
- `decisions_applied` — list of `{"flag_id", "type", "effect"}`
- `status` — `ready` or `blocked`
- `blocked_reason` — text when blocked, else null
