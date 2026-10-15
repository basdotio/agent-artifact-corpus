import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import intake_server  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_roster():
    """Every test starts with an empty roster and review queue."""
    intake_server.ROSTER.reset()
    yield intake_server.ROSTER
    intake_server.ROSTER.reset()
