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

    mcp_server: AnyHttpUrl = Field(alias="MCP_SERVER")


MCP_SERVER: str = str(ScopeSettings().mcp_server)
