"""Two minutes, no API keys, no ports: the calls a support agent would make on a regulated
iGaming desk, sent through gatehouse in memory, with what the model actually gets back.

    python examples/igaming/demo.py
"""
import asyncio
import importlib.util
import json
import logging
from pathlib import Path

from fastmcp import Client

from gatehouse import load
from gatehouse.server import build

logging.getLogger("client").setLevel(logging.ERROR)   # the client warns when a tool is hidden; that is the point

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("backend", HERE / "backend.py")
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)

CALLS = [
    ("get_player", {"player_id": "P-1001"}, "look up the player"),
    ("get_ticket", {"ticket_id": "T-501"}, "read a ticket with an IBAN in it"),
    ("update_bank_account", {"player_id": "P-1001", "iban": "ES76 2077 0024 0031 0257 5766"},
     "player asks to change the payout IBAN"),
    ("apply_bonus", {"player_id": "P-1001", "amount_eur": 10, "reason": "slow withdrawal"},
     "10 EUR goodwill bonus"),
    ("apply_bonus", {"player_id": "P-1001", "amount_eur": 10, "reason": "slow withdrawal"},
     "model retries after a timeout"),
    ("apply_bonus", {"player_id": "P-1001", "amount_eur": 120, "reason": "angry player"},
     "120 EUR bonus"),
    ("set_self_exclusion", {"player_id": "P-1002", "months": 6}, "player asks to self-exclude"),
    ("close_ticket", {"ticket_id": "T-501"}, "close with no resolution"),
    ("export_player_data", {"player_id": "P-1001"}, "a tool in no profile"),
]


def short(result) -> str:
    data = result.structured_content if result.structured_content is not None else result.data
    if isinstance(data, dict) and data.get("error"):
        return f"{data['error'].upper()}  [{data['rule']}]"
    if "iban" in data:            # what the model sees of a player record
        gone = [k for k in ("date_of_birth", "document_number") if k not in data]
        return f"iban {data['iban']}, phone {data['phone']}, email {data['email']}, dropped {', '.join(gone)}"
    if "description" in data:
        return f'"{data["description"]}"'
    return json.dumps(data, ensure_ascii=False)


async def main():
    gate = load(HERE / "gatehouse.yaml")
    gate.audit_log = str(HERE / "audit.jsonl")
    Path(gate.audit_log).unlink(missing_ok=True)

    async with Client(backend.mcp) as c:
        raw = {t.name for t in await c.list_tools()}
    for profile in ("support-read", "support-write"):
        async with Client(build(gate, profile, upstream=backend.mcp)) as c:
            seen = sorted(t.name for t in await c.list_tools())
        print(f"{profile:14} sees {len(seen)} of {len(raw)} upstream tools: {', '.join(seen)}")
    print()

    async with Client(build(gate, "support-write", upstream=backend.mcp)) as c:
        for tool, args, why in CALLS:
            result = await c.call_tool(tool, args, raise_on_error=False)
            print(f"  {why:40} {tool:20} -> {short(result)}")

    print(f"\nbalance after two identical 10 EUR calls: {backend.PLAYERS['P-1001']['balance_eur']:.2f} EUR "
          f"(started at 42.50)")
    print(f"audit log: {gate.audit_log}")


if __name__ == "__main__":
    asyncio.run(main())
