from rules_engine.tables import catalogue, load_table, lookup


def test_a_state_and_termination_type_give_that_row():
    il = lookup("state", {"state": "IL", "termination_type": "involuntary"})
    assert il["requirement"] == "required"
    assert il["due"] == "next_regular_payday"

    ca = lookup("state", {"state": "CA", "termination_type": "involuntary"})
    assert ca["due"] == "immediately"
    assert ca["allowed_methods"] == ["live_check"]

    assert lookup("state", {"state": "NY", "termination_type": "voluntary"})["requirement"] == "policy_else_required"


def test_a_state_without_rows_is_not_available_never_another_state():
    row = lookup("state", {"state": "OR", "termination_type": "voluntary"})
    assert set(row.values()) == {None}


def test_a_missing_key_is_not_available():
    row = lookup("state", {"state": "CA", "termination_type": None})
    assert set(row.values()) == {None}


def test_every_value_is_one_the_catalogue_allows():
    facts, table = catalogue(), load_table("state")
    for row in table["rows"]:
        for name in (*table["keys"], *table["values"]):
            allowed = facts[name].get("values")
            value = row[name]
            if not isinstance(allowed, (list, dict)) or value is None:
                continue
            for v in value if isinstance(value, list) else [value]:
                assert v in allowed, f"{row['state']}/{row['termination_type']}: {name}={v!r}"


def test_each_state_and_termination_type_appears_once():
    rows = load_table("state")["rows"]
    keys = [(r["state"], r["termination_type"]) for r in rows]
    assert len(keys) == len(set(keys))
