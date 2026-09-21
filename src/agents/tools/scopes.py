"""Which agent node may reach which dummy MCP/GraphQL tool.

"""

from __future__ import annotations

MCP_SERVERS: dict[str, str] = {
    "agents": "http://localhost:8003/mcp",
}

GRAPHQL_SERVERS: dict[str, str] = {
    "trinet": "http://localhost:8002/graphql",
}

# node name -> MCP tool names it may call, per server key above
NODE_MCP_SCOPES: dict[str, dict[str, set[str]]] = {
    "orchestrator": {"agents": {"get_employees"}},
    "planner": {},
    "expert": {},
    "worker": {"agents": {"get_employees"}},
}

# node name -> GraphQL field names it may query, per server key above
NODE_GRAPHQL_SCOPES: dict[str, dict[str, set[str]]] = {
    "orchestrator": {"trinet": {"employees"}},
    "planner": {},
    "expert": {},
    "worker": {"trinet": {"employees"}},
}


class ScopeError(PermissionError):
    pass


def assert_mcp_allowed(node: str, server: str, tool_name: str) -> None:
    allowed = NODE_MCP_SCOPES.get(node, {}).get(server, set())
    if tool_name not in allowed:
        raise ScopeError(
            f"node {node!r} is not scoped to call MCP tool {tool_name!r} on {server!r}"
        )


def assert_graphql_allowed(node: str, server: str, field_name: str) -> None:
    allowed = NODE_GRAPHQL_SCOPES.get(node, {}).get(server, set())
    if field_name not in allowed:
        raise ScopeError(
            f"node {node!r} is not scoped to query GraphQL field {field_name!r} on {server!r}"
        )
