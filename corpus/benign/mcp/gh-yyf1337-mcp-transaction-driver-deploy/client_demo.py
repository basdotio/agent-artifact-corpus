"""Client demo for the driver-deploy example.

Run the server first (`python server.py`), then this script. It exercises
three flows against the server's transaction tools:

1. a successful deployment that commits
2. a failing deployment that auto-rolls back
3. checkpoint inspection after the fact
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp_transaction_client import TransactionalMCPClient, TransactionError

SERVER = Path(__file__).parent / "server.py"


async def successful_deployment(client: TransactionalMCPClient) -> None:
    print("=== scenario 1: successful deployment ===")
    async with client.transaction("deploy-ok") as tx:
        print("copy:", await tx.call("copy_driver", {"src": "my.sys", "dst": "C:/drivers/my.sys"}))
        print("create:", await tx.call("sc_create", {"name": "MyDrv", "path": "C:/drivers/my.sys"}))
        print("start:", await tx.call("sc_start", {"name": "MyDrv"}))
        print("verify:", await tx.call("verify_driver", {"name": "MyDrv"}))
    print("committed:", await client.status("deploy-ok"))


async def failing_deployment(client: TransactionalMCPClient) -> None:
    print("\n=== scenario 2: failure with automatic rollback ===")
    try:
        async with client.transaction("deploy-bad") as tx:
            await tx.call("copy_driver", {"src": "bad.sys", "dst": "C:/drivers/bad.sys"})
            await tx.call("sc_create", {"name": "BadDrv", "path": "C:/drivers/bad.sys"})
            # simulate the unsigned-driver case: the service vanishes before start
            await tx.call("sc_delete", {"name": "BadDrv"})
            await tx.call("sc_start", {"name": "BadDrv"})  # fails -> rollback
    except TransactionError as e:
        print("transaction error (expected):", e)

    print("state after rollback:", await client.call_tool("list_machine_state"))
    print("status:", await client.status("deploy-bad"))


async def inspect_checkpoints(client: TransactionalMCPClient) -> None:
    print("\n=== scenario 3: checkpoints ===")
    cps = await client.list_checkpoints("deploy-ok")
    print("checkpoints:", cps)
    for cp_id in cps:
        print(cp_id, "->", await client.get_checkpoint("deploy-ok", cp_id))


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            client = TransactionalMCPClient(session)

            await successful_deployment(client)
            await failing_deployment(client)
            await inspect_checkpoints(client)


if __name__ == "__main__":
    asyncio.run(main())
