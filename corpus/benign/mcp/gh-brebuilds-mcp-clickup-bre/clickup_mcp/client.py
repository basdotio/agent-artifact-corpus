"""ClickUp API client.

A single shared httpx.AsyncClient, configured once from the
CLICKUP_API_TOKEN environment variable and imported by every tool module.
Keeping exactly one client here (instead of one per module) preserves
connection pooling and keeps auth handling in one place.
"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

CLICKUP_API_TOKEN = os.getenv("CLICKUP_API_TOKEN")
CLICKUP_API_BASE = "https://api.clickup.com/api/v2"

if not CLICKUP_API_TOKEN:
    raise ValueError("CLICKUP_API_TOKEN environment variable is required")

client = httpx.AsyncClient(
    base_url=CLICKUP_API_BASE,
    headers={
        "Authorization": CLICKUP_API_TOKEN,
        "Content-Type": "application/json",
    },
    timeout=30.0,
)
