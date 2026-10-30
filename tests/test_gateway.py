"""
Tests for the model gateway's direct Anthropic client configuration.
"""
import pytest
from agents.model.gateway import ModelGateway, MissingAPIKeyError


def test_missing_api_key_raises_error(monkeypatch):
    """Missing ANTHROPIC_API_KEY raises MissingAPIKeyError."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(MissingAPIKeyError, match="ANTHROPIC_API_KEY is not set"):
        gateway = ModelGateway()
        gateway.require_client()

    with pytest.raises(MissingAPIKeyError, match="ANTHROPIC_API_KEY is not set"):
        gateway = ModelGateway()
        gateway.require_skills_client()


def test_default_base_url_when_not_set(monkeypatch):
    """Client uses SDK default base URL when ANTHROPIC_BASE_URL is not set."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-12345")
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)

    gateway = ModelGateway()
    client = gateway.require_client()

    # SDK default is https://api.anthropic.com
    assert client.base_url == "https://api.anthropic.com"


def test_custom_base_url_when_set(monkeypatch):
    """Client uses custom base URL when ANTHROPIC_BASE_URL is set."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-12345")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://custom.example.com")

    gateway = ModelGateway()
    client = gateway.require_client()

    assert client.base_url == "https://custom.example.com"
    assert not any(name.lower().startswith("cf-") for name in client.default_headers)


def test_client_identity(monkeypatch):
    """require_client() and require_skills_client() return the same instance."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-12345")

    gateway = ModelGateway()
    client_a = gateway.require_client()
    client_b = gateway.require_skills_client()

    assert client_a is client_b, "Both methods should return the same client instance"
