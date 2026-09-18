from pydantic import BaseModel

from graphql_api import GraphQLAPI, field
import uvicorn
from graphql_mcp import GraphQLMCP


class Ticket(BaseModel):
    id: str
    title: str
    status: str
    priority: str


_DUMMY_TICKETS = [
    Ticket(id="TCK-1", title="Login page throws 500 on submit", status="open", priority="high"),
    Ticket(id="TCK-2", title="Dark mode toggle resets on refresh", status="open", priority="low"),
    Ticket(id="TCK-3", title="Export to CSV missing header row", status="closed", priority="medium"),
    Ticket(id="TCK-4", title="Slow response on /reports endpoint", status="open", priority="high"),
]


class HelloAPI:
    @field
    def hello(self, name: str = "World") -> str:
        """Say hello to someone."""
        return f"Hello, {name}!"

    @field
    def tickets(self, query: str = "") -> list[Ticket]:
        """Look up dummy tickets by id, title, or status."""
        q = query.lower().strip()
        if not q:
            return _DUMMY_TICKETS
        return [
            t for t in _DUMMY_TICKETS
            if q in t.title.lower() or q in t.status or q in t.id.lower()
        ]


api = GraphQLAPI(root_type=HelloAPI)
server = GraphQLMCP.from_api(api, name="Hello")
app = server.http_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)