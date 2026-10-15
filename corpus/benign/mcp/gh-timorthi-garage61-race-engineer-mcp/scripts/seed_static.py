"""Seed static reference data from the Garage61 API.

Calls GET /tracks and GET /cars and writes the results to
static/tracks.json and static/cars.json respectively.

Run once at setup and again whenever new iRacing content is released:

    uv run scripts/seed_static.py

The MCP server loads these files at startup instead of hitting the API on
every boot.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime

from garage61.client import Garage61Client
from garage61.constants import STATIC_DIR


async def main() -> None:
    async with Garage61Client.from_env() as client:
        print("Fetching tracks...")
        tracks = await client.get_tracks(use_cache=False)

        print("Fetching cars...")
        cars = await client.get_cars(use_cache=False)

    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now().isoformat(timespec="seconds")

    tracks_path = STATIC_DIR / "tracks.json"
    tracks_path.write_text(
        json.dumps(
            {"generated_at": now, "tracks": [t.model_dump() for t in tracks]}, indent=2
        )
    )
    print(f"Wrote {len(tracks)} tracks to {tracks_path}")

    cars_path = STATIC_DIR / "cars.json"
    cars_path.write_text(
        json.dumps(
            {"generated_at": now, "cars": [c.model_dump() for c in cars]}, indent=2
        )
    )
    print(f"Wrote {len(cars)} cars to {cars_path}")


if __name__ == "__main__":
    asyncio.run(main())
