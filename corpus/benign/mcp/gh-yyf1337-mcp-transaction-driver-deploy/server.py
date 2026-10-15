"""Windows kernel-driver deployment MCP server with transaction support.

The workflow — copy driver, create the service, start it, verify — maps
naturally onto a transaction: if verification fails, the service and the
copied file are rolled back automatically. Tools are simulated so the demo
runs anywhere; swap the bodies for vmrun guest operations to go real.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from fastmcp import FastMCP
from mcp_transaction import (
    CheckpointConfig,
    CompensationAction,
    enable_transactions,
    transactional,
)

mcp = FastMCP("driver-deploy")

enable_transactions(
    mcp,
    storage_backend="sqlite",
    storage_config={"database_path": "driver_deploy_transactions.db"},
)


@dataclass
class MachineState:
    """In-memory stand-in for the target machine."""

    files: set[str] = field(default_factory=set)
    services: dict[str, dict] = field(default_factory=dict)


MACHINE = MachineState()
DRIVER_DIR = Path("C:/drivers")


@mcp.tool
@transactional(
    compensations=[
        # dst in copy_driver maps to path in delete_file
        CompensationAction(tool="delete_file", input_from="original_input", input_map={"path": "dst"})
    ]
)
async def copy_driver(src: str, dst: str) -> dict:
    """Copy a driver .sys file into the target's driver directory."""
    MACHINE.files.add(dst)
    return {"dst": dst, "size": 4096, "status": "copied"}


@mcp.tool
async def delete_file(path: str) -> dict:
    """Remove a file from the target (compensation for copy_driver)."""
    MACHINE.files.discard(path)
    return {"path": path, "status": "deleted"}


@mcp.tool
@transactional(
    compensations=[CompensationAction(tool="sc_delete", input_from="original_input", input_map={"name": "name"})]
)
async def sc_create(name: str, path: str) -> dict:
    """Register a kernel driver as a Windows service."""
    if name in MACHINE.services:
        raise RuntimeError(f"service {name!r} already exists")
    MACHINE.services[name] = {"name": name, "path": path, "status": "stopped"}
    return {"name": name, "status": "created"}


@mcp.tool
async def sc_delete(name: str) -> dict:
    """Unregister a service (compensation for sc_create)."""
    MACHINE.services.pop(name, None)
    return {"name": name, "status": "deleted"}


@mcp.tool
@transactional(checkpoint=CheckpointConfig(id="driver_loaded", ttl_seconds=7200))
async def sc_start(name: str) -> dict:
    """Load the driver into the kernel. On a real target this is the step
    that requires a kernel debugger attached for unsigned drivers."""
    svc = MACHINE.services.get(name)
    if svc is None:
        raise RuntimeError(f"service {name!r} not found")
    svc["status"] = "running"
    return {"name": name, "status": "running"}


@mcp.tool
async def verify_driver(name: str) -> dict:
    """Check the driver loaded and its file is in place. Read-only."""
    svc = MACHINE.services.get(name)
    checks = {
        "service_exists": svc is not None,
        "service_running": bool(svc and svc["status"] == "running"),
        "driver_file_present": bool(svc and svc["path"] in MACHINE.files),
    }
    if not all(checks.values()):
        raise RuntimeError(f"verification failed: {checks}")
    return {"name": name, "verified": True, "checks": checks}


@mcp.tool
async def list_machine_state() -> dict:
    """Inspect the simulated machine: files and services."""
    return {"files": sorted(MACHINE.files), "services": MACHINE.services}


if __name__ == "__main__":
    mcp.run()
