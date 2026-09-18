"""Which agent node may reach which dummy MCP/GraphQL tool.

Both dummy servers live in mcp_server/: `agents_server.py` (hand-written MCP
tools, port 8003) and `graphql_server.py` (GraphQL schema auto-exposed as MCP
tools + a raw /graphql endpoint, port 8002). Nodes don't get free access to
either — every call in mcp_client.py / graphql_client.py is checked against
the maps below first, so adding a new tool doesn't silently open it up to
every agent.
"""

from __future__ import annotations

MCP_SERVERS: dict[str, str] = {
    "agents": "http://localhost:8003/mcp",
}

GRAPHQL_SERVERS: dict[str, str] = {
    "tickets": "http://localhost:8002/graphql",
}

# node name -> MCP tool names it may call, per server key above
NODE_MCP_SCOPES: dict[str, dict[str, set[str]]] = {
    "orchestrator": {"agents": {"get_tickets"}},
    "planner": {},
    "expert": {},
    "worker": {"agents": {"get_tickets"}},
}

# node name -> GraphQL field names it may query, per server key above
NODE_GRAPHQL_SCOPES: dict[str, dict[str, set[str]]] = {
    "orchestrator": {"tickets": {"tickets"}},
    "planner": {},
    "expert": {},
    "worker": {"tickets": {"tickets"}},
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
