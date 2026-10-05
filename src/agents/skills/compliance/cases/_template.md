# Case — <Name>

Copy this file to `cases/<case>.md` to add a case type. Only use checks from
`shared/checks.md`; if a rule can't be expressed with their settings, add a
check there first (and say which worker runs it).

<What this case decides: which rules, deadlines and obligations.>

```yaml
case: <case>                  # lowercase, unique; matches the Planner's `work`
aliases: [<other names the Planner or orders use for this work>]

workers: [<the workers whose checks this case uses: timing, obligations, exceptions>]

facts:                        # from validation (previous_results.validation.cases.<case>)
  - <fact>

rules:                        # ask execution, never from memory
  - {name: <rule>, keys: [<facts that pick the rule>]}

records:                      # ask execution; only if a check needs one
  - {name: <record>, keys: [<facts that pick it>]}

checks:
  facts_present: {fields: [<facts the rules can't be applied without>]}
  rule_found:    {rule: <rule>, keys: [...]}
  # timing: deadline, deadline_met, cutoff · obligations: requirement, obligation · exceptions: exception
```

## Case flags

- `<flag>` — `{<payload>}`

## Output fields (`output.cases.<case>`)

- `<field>` — <type>, or null
