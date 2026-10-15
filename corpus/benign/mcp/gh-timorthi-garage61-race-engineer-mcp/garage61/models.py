"""Pydantic v2 models for Garage61 API inputs and outputs."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class Track(BaseModel):
    track_id: int
    track_id_in_iracing: int
    name: str
    variant: Optional[str]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Track:
        return cls(
            track_id=int(data["id"]),
            track_id_in_iracing=int(data["platform_id"]),
            name=str(data["name"]),
            variant=str(data["variant"]) if data["variant"] else None,
        )


class Car(BaseModel):
    car_id: int
    car_id_in_iracing: int
    name: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Car:
        return cls(
            car_id=int(data["id"]),
            car_id_in_iracing=int(data["platform_id"]),
            name=str(data["name"]),
        )


class LapSummary(BaseModel):
    """Lap metadata returned by the /laps search endpoint."""

    lap_id: str
    lap_time_ms: int
    driver_name: str
    driver_irating: Optional[int] = None
    session_type: int
    air_temp_c: Optional[float] = None
    track_temp_c: Optional[float] = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> LapSummary:
        """Construct from a /laps response item.

        NOTE: Field names (e.g. "lapTime", "iRating", "airTemp") are ASSUMED
        based on camelCase REST conventions. Verify against a real API response.
        """
        conditions: dict[str, Any] = data.get("conditions") or {}
        driver: dict[str, Any] = data.get("driver") or {}
        return cls(
            lap_id=str(data["id"]),
            lap_time_ms=int(data["lapTime"]),
            driver_name=str(driver.get("name", "")),
            driver_irating=driver.get("iRating"),
            session_type=int(data.get("sessionType", 0)),
            air_temp_c=conditions.get("airTemp"),
            track_temp_c=conditions.get("trackTemp"),
        )


class LapDetail(BaseModel):
    """Full single-lap metadata returned by GET /laps/{id}."""

    lap_id: str
    lap_time_ms: int
    driver_name: str
    driver_irating: Optional[int] = None
    session_type: int
    track_id: int
    car_id: int
    air_temp_c: Optional[float] = None
    track_temp_c: Optional[float] = None
    has_telemetry: bool = False

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> LapDetail:
        """Construct from a /laps/{id} response.

        NOTE: Field names (e.g. "lapTime", "trackId", "carId", "hasTelemetry")
        are ASSUMED based on camelCase REST conventions. Verify against a real
        API response.
        """
        conditions: dict[str, Any] = data.get("conditions") or {}
        driver: dict[str, Any] = data.get("driver") or {}
        return cls(
            lap_id=str(data["id"]),
            lap_time_ms=int(data["lapTime"]),
            driver_name=str(driver.get("name", "")),
            driver_irating=driver.get("iRating"),
            session_type=int(data.get("sessionType", 0)),
            track_id=int(data["trackId"]),
            car_id=int(data["carId"]),
            air_temp_c=conditions.get("airTemp"),
            track_temp_c=conditions.get("trackTemp"),
            has_telemetry=bool(data.get("hasTelemetry", False)),
        )


class FindLapsParams(BaseModel):
    """Typed wrapper for the /laps query parameters used by search_similar_conditions."""

    track_id: int
    car_id: int
    min_air_temp: Optional[float] = None
    max_air_temp: Optional[float] = None
    min_track_temp: Optional[float] = None
    max_track_temp: Optional[float] = None
    session_types: list[int] = Field(default_factory=lambda: [1, 2, 3])
    see_telemetry: bool = True


class TelemetrySample(BaseModel):
    """A single row from a Garage61 telemetry CSV (GET /laps/{id}/csv).

    Column names are the exact strings present in the CSV header, mapped to
    snake_case fields. ``ABSActive`` and ``DRSActive`` arrive as the strings
    ``"true"``/``"false"`` when parsed by pandas; ``from_api`` normalises them
    to Python bools.
    """

    speed_mps: float  # Speed — m/s
    lap_dist_pct: float  # Lap distance fraction 0.0–1.0
    lat: float  # GPS latitude
    lon: float  # GPS longitude
    brake: float  # Brake pressure 0.0–1.0
    throttle: float  # Throttle position 0.0–1.0
    rpm: float  # Engine RPM
    steering_wheel_angle: float  # Steering angle — radians
    gear: int  # Current gear
    clutch: float  # Clutch position 0.0–1.0
    abs_active: bool  # ABS active flag
    drs_active: bool  # DRS active flag
    lat_accel: float  # Lateral acceleration — m/s²
    long_accel: float  # Longitudinal acceleration — m/s²
    vert_accel: float  # Vertical acceleration — m/s²
    yaw: float  # Yaw angle — radians
    yaw_rate: float  # Yaw rate — rad/s
    position_type: int  # 0=Unknown 1=Pit lane 2=Pit stop 3=On track 4=Off track

    @classmethod
    def from_api(cls, row: dict[str, Any]) -> TelemetrySample:
        """Construct from a single CSV row dict (e.g. from ``df.to_dict('records')``)."""
        return cls(
            speed_mps=float(row["Speed"]),
            lap_dist_pct=float(row["LapDistPct"]),
            lat=float(row["Lat"]),
            lon=float(row["Lon"]),
            brake=float(row["Brake"]),
            throttle=float(row["Throttle"]),
            rpm=float(row["RPM"]),
            steering_wheel_angle=float(row["SteeringWheelAngle"]),
            gear=int(row["Gear"]),
            clutch=float(row["Clutch"]),
            abs_active=str(row["ABSActive"]).lower() == "true",
            drs_active=str(row["DRSActive"]).lower() == "true",
            lat_accel=float(row["LatAccel"]),
            long_accel=float(row["LongAccel"]),
            vert_accel=float(row["VertAccel"]),
            yaw=float(row["Yaw"]),
            yaw_rate=float(row["YawRate"]),
            position_type=int(row["PositionType"]),
        )


class Garage61Error(BaseModel):
    """Structured error payload returned to the MCP tool layer."""

    error: str
    message: str
    recoverable: bool
