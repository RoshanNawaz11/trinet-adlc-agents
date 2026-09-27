"""The MCP server agents reach."""

from __future__ import annotations

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScopeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mcp_server: AnyHttpUrl | None = Field(default=None, alias="MCP_SERVER")


# None when MCP_SERVER isn't set — the agents then run without MCP tools.
_server = ScopeSettings().mcp_server
MCP_SERVER: str | None = str(_server) if _server else None
