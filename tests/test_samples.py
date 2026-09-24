import pytest

from agents.runtime.samples import SAMPLES, format_samples, resolve_query, sample_query


def test_priya_sample_mentions_employee_and_payroll():
    query = sample_query("priya")
    assert "Priya Sharma" in query
    assert "payslip" in query.lower()


def test_sample_query_is_case_insensitive():
    assert sample_query("PRIYA") == SAMPLES["priya"]


def test_unknown_sample_lists_known_names():
    with pytest.raises(KeyError, match="checkout"):
        sample_query("nobody")


def test_resolve_query_uses_priya_sample():
    assert resolve_query(query=None, sample="priya", resume=False) == sample_query("priya")


def test_resolve_query_rejects_query_and_sample_together():
    with pytest.raises(ValueError, match="not both"):
        resolve_query(query="hello", sample="priya", resume=False)


def test_format_samples_includes_priya():
    listing = format_samples()
    assert "priya:" in listing
    assert "Priya Sharma" in listing
