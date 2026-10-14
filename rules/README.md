# Rules

The rules the engine runs (`src/agents/rules_engine/evaluate.py`). Readable
first versions are in `docs/rules/` — reference only; these YAML files are
the rules.

```
facts.yaml             every fact a rule or table may use
tables/state.yaml      each state's final-pay law, by termination type
payroll/               payroll rules
special-instructions/  the client's special instructions
validation/            validation rules
compliance/            compliance rules
```

## A rule file

```yaml
id: payroll.leave-payout       # <folder>.<file name>
version: 2                     # raise it on every change
agent: payroll-calculation     # the agent that runs it (its skill name)
worker: leave                  # the worker, when the agent has workers
purpose: ...                   # one or two sentences, for people
applies_to: {...}              # case types this rule covers — see below
inputs: [...]                  # case facts it reads (rules/facts.yaml)
judgement: [...]               # what the LLM must read from text to fill a fact — not run by the engine
lines: [...]                   # optional: run once per item of a list fact
compute: [...]                 # optional: named values, in order
checks: [...]                  # every matching check applies
cases: [...]                   # the first matching case gives the result
outputs: [...]                 # what the rule returns
not_included: ...              # what other rules handle
to_confirm: [...]              # open questions for the team
```

### Order of evaluation

1. `lines` — each line block runs its own `checks` and `cases` per item,
   then its `total`
2. `compute` — each value in order; later ones can use earlier ones
3. `checks` — every check whose `when` holds adds its flag, note or
   `provisional`
4. `cases` — the first case whose `when` holds gives `result` and the
   outputs

Every name in `outputs` comes from the matching case's `then`; if the case
doesn't set it, from `compute`, a line total, or the facts.

### applies_to

One entry per case type: `any`, or a list of values. A rule runs only when
every entry matches the case.

```yaml
applies_to: {state: any, pay_group: any, employment_type: any, termination_type: [voluntary, involuntary]}
```

## Expressions

`when`, `compute` and a total's `where` are **expressions** — ordinary
formulas over the facts, written in double quotes, with single quotes for
text inside:

```yaml
- when: "balance_hours <= 0"
- when: "requirement == 'required' and policy_pays_out is not False"
- when: "'payout-override' in instruction_kinds"
- when: true                                    # always — the last case
compute:
  - net_before: "gross_pay + leave_payout - system_taxes - deductions - garnishments"
```

You can use `+ - * /`, `< <= > >= == !=`, `and or not`, `is None`,
`is not None`, `in`, `not in`, `x if condition else y`, `[lists]`, numbers,
`'text'`, `True`, `False`, `None`, and these functions:

| Function | Gives |
|---|---|
| `min(a, b, ...)` `max(a, b, ...)` | smallest / largest, skipping values not available |
| `round(x, 2)` `abs(x)` | as usual |
| `within(a, b, 0.01)` | True when a and b differ by no more than 0.01 |
| `missing(a, b, ...)` | True when any of them is not available |
| `missing_of('a', 'b', ...)` | the names (in quotes) of the facts that are not available |
| `mentions(text, ['word', ...])` | True when the text contains any of the words (without case) |
| `lower(text)` | the text in lower case |
| `first(list)` | the list's first item |
| `days_between(d1, d2)` `hours_between(t1, t2)` | d2 − d1 |
| `add_days(date, n)` | date + n days |
| `due_date(form, amount, start, next_payday, period_end)` | applies a deadline form (`facts.yaml` → `due`) |
| `largest_difference(label=[a, b], ...)` | the label whose a and b differ most |
| `smallest(label=x, ...)` | the label of the smallest value |

**Not available.** A fact that is not available is `None`. Any sum,
product or comparison that uses it is not available too: in a `when` it
doesn't hold, in a value it gives `None`. Check for it with `x is None` or
`missing(x)` where it matters.

Dates and times are compared as dates and times.

## then

A `then` sets values. **A text starting with `=` is an expression; anything
else is used as written.**

```yaml
then: {result: pass, line_payout: "= min(balance_hours, plan_max_hours) * payout_rate"}
then: {result: fail, flag: {kind: decision, type: netPayMismatch, title: "...",
                            detail: {system_net_pay: "= system_net_pay"}}}
```

| Key | Means |
|---|---|
| `result` | `pass`, `fail`, `not available`, `not applicable` |
| `outcome` | `stop` (an analyst handles it), `wait` (until someone answers), `note` |
| `reason` | one sentence for the reviewer |
| `flag` / `flags` | `{kind: input / check / decision, type: <flag type>, title: ..., detail: {...}}` |
| `note` | a note for the reviewer, no flag |
| `provisional` | `true` — the amounts may change |
| any output | its value |

A case can also have `why:` — the reason behind it, for people; the engine
ignores it.

### Flag kinds

| Kind | The analyst… |
|---|---|
| `input` | supplies or picks a value |
| `check` | acknowledges that data may be stale or odd |
| `decision` | decides — the agent's result needs judgement |

## Lines

```yaml
lines:
  - for_each: leave_balances               # a list fact
    each: [leave_type, balance_hours, ...]  # the item's facts
    checks: [...]                          # optional: every match, per item
    cases: [...]                           # first match, per item
    total:
      leave_payout: {sum: line_payout}
      overtime_pay: {sum: line_amount, where: "line_kind == 'overtime'"}
```

Inside a line block, an expression can read the item's facts and the
case's. Totals over the items:

| Total | Gives |
|---|---|
| `{sum: field}` | the sum — not available if any item's is; 0 for no items |
| `{count: field}` | how many items |
| `{collect: field}` | the values as a list, skipping ones not available |

Each can take `where: "expression"` to count only the items it holds for.
