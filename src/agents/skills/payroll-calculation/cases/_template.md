# Case — <Name>

Copy this file to `cases/<case>.md` to add a case type. Only use calculations
from `shared/calculations.md` and checks from `shared/checks.md`; if something
can't be expressed with them, add it there first (and say which worker runs it).

<What pay effect this case works out.>

```yaml
case: <case>                  # lowercase, unique; matches the Planner's `work`
aliases: [<other names the Planner or orders use for this work>]

workers: [<the workers whose calculations and checks this case uses>]

inputs:
  from_validation: [<facts>]  # previous_results.validation.cases.<case>
  from_compliance: [<rules or deadlines>]
  from_execution:  [<pay data>]

calculate: [<calculations>]

checks:
  inputs_present: {fields: [<inputs the calculations can't run without>]}
  # matches_system, one_outcome, payment_method_usable, setup_complete as needed
```

## Case flags

- `<flag>` — `{<payload>}`

## Output fields (`output.cases.<case>`)

- `<field>` — <type>, or null
