"""Shared fixtures for the garage61-race-engineer-mcp test suite."""

import pytest


# ---------------------------------------------------------------------------
# Telemetry CSV fixtures
# ---------------------------------------------------------------------------

TELEMETRY_COLUMNS = (
    "Speed,LapDistPct,Lat,Lon,Brake,Throttle,RPM,SteeringWheelAngle,"
    "Gear,Clutch,ABSActive,DRSActive,LatAccel,LongAccel,VertAccel,Yaw,YawRate,PositionType"
)


def _make_csv_row(
    *,
    speed: float = 50.0,
    lap_dist_pct: float = 0.1,
    position_type: int = 3,
    abs_active: str = "false",
    drs_active: str = "false",
) -> str:
    return (
        f"{speed},{lap_dist_pct},52.0,4.0,"
        f"0.0,0.8,4000,0.05,"
        f"3,0.0,{abs_active},{drs_active},"
        f"0.1,-0.2,9.8,0.01,0.02,{position_type}"
    )


@pytest.fixture
def sample_row_dict() -> dict:
    """A dict representing one valid telemetry CSV row (all 18 columns)."""
    return {
        "Speed": 50.0,
        "LapDistPct": 0.1,
        "Lat": 52.0,
        "Lon": 4.0,
        "Brake": 0.0,
        "Throttle": 0.8,
        "RPM": 4000.0,
        "SteeringWheelAngle": 0.05,
        "Gear": 3,
        "Clutch": 0.0,
        "ABSActive": "false",
        "DRSActive": "false",
        "LatAccel": 0.1,
        "LongAccel": -0.2,
        "VertAccel": 9.8,
        "Yaw": 0.01,
        "YawRate": 0.02,
        "PositionType": 3,
    }


@pytest.fixture
def valid_csv_text() -> str:
    """A minimal valid telemetry CSV with three on-track rows."""
    rows = [
        TELEMETRY_COLUMNS,
        _make_csv_row(speed=50.0, lap_dist_pct=0.10, position_type=3),
        _make_csv_row(speed=60.0, lap_dist_pct=0.20, position_type=3),
        _make_csv_row(speed=70.0, lap_dist_pct=0.30, position_type=3),
    ]
    return "\n".join(rows)


@pytest.fixture
def mixed_position_csv_text() -> str:
    """CSV with on-track (3), pit lane (1), and off-track (4) rows."""
    rows = [
        TELEMETRY_COLUMNS,
        _make_csv_row(speed=50.0, lap_dist_pct=0.10, position_type=3),
        _make_csv_row(speed=10.0, lap_dist_pct=0.50, position_type=1),  # pit lane
        _make_csv_row(speed=60.0, lap_dist_pct=0.70, position_type=3),
        _make_csv_row(speed=5.0, lap_dist_pct=0.90, position_type=4),  # off track
    ]
    return "\n".join(rows)
