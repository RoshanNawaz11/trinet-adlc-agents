"""Edit QUERY below, then run: python run_query.py"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from agents.observability.langwatch_setup import langwatch_setup
from agents.runtime.worker import _setup_logging, run_query

QUERY = """
HR request from Priya Sharma: she asked for a copy of her latest payslip
and confirmation of her current department, job title, location, and
employment status. Please look her up, summarize the request, and
classify its priority.
""".strip()

THREAD_ID = None  # set to a previous thread_id to resume it
RESUME = False


def _print_summary(out: dict) -> None:
    values = out.get("values") or {}
    flagged = " (flagged)" if values.get("flagged") else ""
    print(f"Thread:  {out.get('thread_id')}")
    print(f"Status:  {values.get('status')}{flagged}")
    if out.get("paused"):
        print(f"Paused before: {', '.join(out.get('next') or [])}")

    for r in values.get("mcp_results") or []:
        mark = "ERROR" if r.get("error") else "ok"
        args = json.dumps(r.get("input") or {}, default=str)
        print(f"\n[{mark}] {r.get('tool')}({args}) -> {r.get('result')}")

    step_results = values.get("step_results") or []
    if step_results:
        print("\nSteps:")
        for r in step_results:
            output = r.get("output") or {}
            line = f"  [{r.get('step_id')}] {r.get('agent')}"
            if r.get("error"):
                line += f" -> ERROR: {r['error']}"
            elif output.get("bounced"):
                line += f" -> bounced ({output['bounced'].get('reason')})"
            else:
                line += f" -> confidence={r.get('confidence')}"
                if r.get("escalation"):
                    line += f" escalation={r['escalation'].get('reason')}"
            print(line)
            if output.get("summary"):
                print(f"      {output['summary']}")
            if output.get("label"):
                print(f"      label={output['label']}")

    if values.get("final_output") is not None:
        print("\nFinal output:")
        print(json.dumps(values["final_output"], indent=2, default=str))


async def _main() -> None:
    _setup_logging()
    langwatch_setup()
    out = await run_query(QUERY, thread_id=THREAD_ID, resume=RESUME)
    _print_summary(out)


if __name__ == "__main__":
    asyncio.run(_main())
