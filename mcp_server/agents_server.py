from fastmcp import FastMCP

import json
import requests

mcp = FastMCP("agents-server")


_DUMMY_TICKETS = [
    {"id": "TCK-1", "title": "Login page throws 500 on submit", "status": "open", "priority": "high"},
    {"id": "TCK-2", "title": "Dark mode toggle resets on refresh", "status": "open", "priority": "low"},
    {"id": "TCK-3", "title": "Export to CSV missing header row", "status": "closed", "priority": "medium"},
    {"id": "TCK-4", "title": "Slow response on /reports endpoint", "status": "open", "priority": "high"},
]


@mcp.tool
def get_tickets(query: str) -> str:
    """
    this tool is used to get the tickets from the database by querying the database with the query
    """
    query = (query or "").lower().strip()
    if not query:
        matches = _DUMMY_TICKETS
    else:
        matches = [
            t for t in _DUMMY_TICKETS
            if query in t["title"].lower() or query in t["status"] or query in t["id"].lower()
        ]
    return json.dumps(matches)