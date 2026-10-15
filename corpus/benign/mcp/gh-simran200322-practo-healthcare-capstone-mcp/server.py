"""MCP Server exposing check_appointment_status tool via FastMCP."""
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastmcp import FastMCP
from app.tools import check_appointment_status as _internal_check_status

# Instantiate FastMCP server
mcp = FastMCP(
    name="Practo Healthcare MCP Server",
    instructions="Provides verified clinical appointment status lookups and escalation triage."
)


@mcp.tool()
def check_appointment_status(record_id: str) -> Dict[str, Any]:
    """Look up a clinical appointment by its record ID (e.g., 'APP-0001').
    
    Returns the appointment's status, consultation fee in INR, follow-up necessity,
    and a mathematically designed clinical escalation score between 0.0 and 1.0.
    
    Args:
        record_id: Synthetic appointment identifier formatted as 'APP-XXXX'.
        
    Returns:
        Structured dictionary containing record details, escalation score, and triage recommendation.
    """
    return _internal_check_status(record_id)


if __name__ == "__main__":
    # fastmcp HTTP transport mounts at /mcp by default (e.g. http://127.0.0.1:8000/mcp)
    print("Starting Practo FastMCP server on http://127.0.0.1:8000/mcp ...")
    mcp.run(transport="http", host="127.0.0.1", port=8000)
