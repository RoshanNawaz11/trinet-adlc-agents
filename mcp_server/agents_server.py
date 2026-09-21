from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import uvicorn
from fastmcp import FastMCP, Context
from fastmcp.server.dependencies import get_http_request

_SRC_ROOT = str(Path(__file__).resolve().parent.parent / "src")
if _SRC_ROOT not in sys.path:
    sys.path.insert(0, _SRC_ROOT)

from agents.tools.scopes import GRAPHQL_SERVERS, ScopeError, assert_graphql_allowed

mcp = FastMCP("agents-server")

TRINET_URL = GRAPHQL_SERVERS["trinet"]

_EMPLOYEES_QUERY = """
query Employees($department: String, $companyId: String, $nameContains: String, $limit: Int!) {
  employees(
    department: $department
    companyId: $companyId
    nameContains: $nameContains
    limit: $limit
  ) {
    employeeId
    fullName
    workEmail
    jobTitle
    department
    companyId
    location
    employmentStatus
    hireDate
  }
}
"""


def _caller_node(ctx: Context) -> str:
    """Caller identity from the HTTP request, not from tool arguments.

    Prefer FastMCP's HTTP request helper — `ctx.request_context.request` is
    the MCP protocol request and often has no custom headers.
    """
    headers = {}
    try:
        headers = get_http_request().headers
    except Exception:
        request = getattr(getattr(ctx, "request_context", None), "request", None)
        headers = getattr(request, "headers", {}) or {}
    node = headers.get("x-agent-node") if headers is not None else None
    if not node:
        raise ScopeError("missing caller identity (x-agent-node header)")
    return node


@mcp.tool
async def get_employees(
    ctx: Context,
    department: str | None = None,
    company_id: str | None = None,
    name_contains: str | None = None,
    limit: int = 20,
) -> str:
    """Look up employee details in the HR Passport directory. Filter by
    `department`, `company_id`, or a `name_contains` substring match on the
    employee's name; omit all three to page through the directory. `limit`
    caps how many records come back and must be between 1 and 100."""
    node = _caller_node(ctx)
    assert_graphql_allowed(node, "trinet", "employees")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TRINET_URL,
            json={
                "query": _EMPLOYEES_QUERY,
                "variables": {
                    "department": department or None,
                    "companyId": company_id or None,
                    "nameContains": name_contains or None,
                    "limit": limit,
                },
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()

    if "errors" in data:
        raise RuntimeError(f"employees GraphQL error: {data['errors']}")

    return json.dumps(data["data"]["employees"])


app = mcp.http_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)