# Case — <Name>

Copy this file to `cases/<case>.md` to add a case type. Only use checks from
`workers/checks.md`; if a rule can't be expressed with their settings, add a
check there first.

<What this case decides: which rules, deadlines and obligations.>

```yaml
case: <case>                  # lowercase, unique; matches the Planner's `work`
aliases: [<other names the Planner or orders use for this work>]

facts:                        # from validation (previous_results.validation.cases.<case>)
  - <fact>

rules:                        # ask execution, never from memory
  - {name: <rule>, keys: [<facts that pick the rule>]}

checks:
  facts_present: {fields: [<facts the rules can't be applied without>]}
  rule_found:    {rule: <rule>, keys: [...]}
  # deadline, deadline_met, requirement, obligation as needed
```

## Case flags

- `<flag>` — `{<payload>}`

## Output fields (`output.cases.<case>`)

- `<field>` — <type>, or null
