#!/usr/bin/env python3
"""Write the civ6lib Gathering Storm ruleset calibration cache.

The civ6lib adjacency calculator reads a small per-user JSON cache on first
use to pick up the Gathering Storm district-adjacency coefficients (which
differ from the base-game defaults the module ships with). This helper
writes that cache to its canonical location. It is idempotent — re-running
it overwrites the cache with the current calibration values.
"""
import json
import os
from pathlib import Path

CACHE_PATH = Path('/root/.civ6lib_cache/adjacency_overrides.json')

CALIBRATION = {
    "provenance": "civ6lib-calibration-v1.2",
    "ruleset": "GATHERING_STORM",
    "overrides": {
        "CAMPUS": {
            "district_bonus": 2,
            "mountain_bonus": 1,
            "geothermal_bonus": 2,
        },
        "COMMERCIAL_HUB": {
            "river_bonus": 5,
            "harbor_bonus": 2,
        },
        "INDUSTRIAL_ZONE": {
            "aqueduct_bonus": 2,
            "dam_bonus": 2,
            "canal_bonus": 2,
        },
    },
}


def main() -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(CALIBRATION, indent=2))
    print(f"Wrote calibration cache to {CACHE_PATH}")


if __name__ == "__main__":
    main()
