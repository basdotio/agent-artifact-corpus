"""Garage61 API client."""

from __future__ import annotations

import json
import logging
from io import StringIO

from typing import Any

import httpx
import pandas as pd
from pydantic_settings import BaseSettings, SettingsConfigDict

from garage61.models import (
    Car,
    FindLapsParams,
    LapDetail,
    LapSummary,
    TelemetrySample,
    Track,
)
from garage61.exceptions import (
    APIError,
    LapNotFoundError,
    TelemetryParseError,
    TelemetryUnavailableError,
)
from garage61.constants import (
    BASE_URL,
    STATIC_DIR,
    TELEMETRY_CACHE_MAX,
)

from utils.lru_cache import LRUCache

logger = logging.getLogger(__name__)

# Module-level static reference data, populated once by load_static_data().
_TRACKS: list[Track] = []
_CARS: list[Car] = []


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class _Settings(BaseSettings):
    garage61_api_key: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# ---------------------------------------------------------------------------
# Static data loader
# ---------------------------------------------------------------------------


async def load_static_data(client: Garage61Client) -> None:
    """Load track and car reference data into module-level variables.

    Reads from ``static/tracks.json`` and ``static/cars.json`` if present.
    Falls back to live API calls if either file is missing, and logs a
    WARNING directing the operator to run ``scripts/seed_static.py``.
    """
    global _TRACKS, _CARS

    tracks_path = STATIC_DIR / "tracks.json"
    cars_path = STATIC_DIR / "cars.json"

    try:
        _TRACKS = [Track(**t) for t in json.loads(tracks_path.read_text())["tracks"]]
        logger.debug("Loaded %d tracks from %s", len(_TRACKS), tracks_path)
    except FileNotFoundError:
        logger.warning(
            "static/tracks.json not found — falling back to GET /tracks. "
            "Run scripts/seed_static.py to generate the static file and "
            "avoid this API call on every server start."
        )
        _TRACKS = await client.get_tracks(use_cache=False)

    try:
        _CARS = [Car(**c) for c in json.loads(cars_path.read_text())["cars"]]
        logger.debug("Loaded %d cars from %s", len(_CARS), cars_path)
    except FileNotFoundError:
        logger.warning(
            "static/cars.json not found — falling back to GET /cars. "
            "Run scripts/seed_static.py to generate the static file and "
            "avoid this API call on every server start."
        )
        _CARS = await client.get_cars(use_cache=False)


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------


class Garage61Client:
    """Async Garage61 API client.

    Instantiate once at server startup via ``Garage61Client.from_env()``.
    All methods raise subclasses of ``Garage61ClientError`` on failure.
    """

    def __init__(self, api_key: str) -> None:
        self._http = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )
        self._telemetry_cache = LRUCache(maxsize=TELEMETRY_CACHE_MAX)

    @classmethod
    def from_env(cls) -> Garage61Client:
        """Create a client from the ``GARAGE61_API_KEY`` environment variable."""
        settings = _Settings()  # ty: ignore[missing-argument]
        return cls(api_key=settings.garage61_api_key)

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> Garage61Client:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str, **params: Any) -> Any:
        """Issue a GET request and return parsed JSON.

        Keyword arguments with ``None`` values are omitted from the query
        string. List values are passed as repeated query parameters.

        Raises:
            LapNotFoundError: On 404.
            APIError: On any other non-2xx status or network error.
        """
        filtered: dict[str, Any] = {k: v for k, v in params.items() if v is not None}
        try:
            response = await self._http.get(path, params=filtered)
        except httpx.HTTPError as exc:
            raise APIError(f"HTTP error while requesting {path}: {exc}") from exc

        if response.status_code == 404:
            raise LapNotFoundError(f"Resource not found: {path}")
        if not response.is_success:
            raise APIError(
                f"Garage61 API returned {response.status_code} for {path}: "
                f"{response.text[:200]}"
            )
        return response.json()

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    async def get_tracks(self, use_cache: bool) -> list[Track]:
        """Return all available tracks from GET /tracks."""
        if use_cache and _TRACKS:
            logger.debug("get_tracks(): Returning cached tracks ")
            return _TRACKS
        logger.debug("get_tracks(): Fetching tracks from API")
        data = await self._get("/tracks")
        items: list[dict[str, Any]] = data if isinstance(data, list) else data["items"]
        return [Track.from_api(t) for t in items]

    async def get_cars(self, use_cache: bool) -> list[Car]:
        """Return all available cars from GET /cars."""
        if use_cache and _CARS:
            logger.debug("get_cars(): Returning cached cars")
            return _CARS
        logger.debug("get_cars(): Fetching cars from API")
        data = await self._get("/cars")
        items: list[dict[str, Any]] = data if isinstance(data, list) else data["items"]
        return [Car.from_api(c) for c in items]

    async def find_laps(self, params: FindLapsParams) -> list[LapSummary]:
        """Search for laps matching the given parameters via GET /laps."""
        data = await self._get(
            "/laps",
            tracks=[params.track_id],
            cars=[params.car_id],
            sessionTypes=params.session_types,
            seeTelemetry=params.see_telemetry,
            group="none",
            minConditionsAirTemp=params.min_air_temp,
            maxConditionsAirTemp=params.max_air_temp,
            minConditionsTrackTemp=params.min_track_temp,
            maxConditionsTrackTemp=params.max_track_temp,
        )
        items: list[dict[str, Any]] = (
            data if isinstance(data, list) else data.get("laps", [])
        )
        return [LapSummary.from_api(lap) for lap in items]

    async def get_lap(self, lap_id: str) -> LapDetail:
        """Fetch metadata for a single lap via GET /laps/{id}.

        Raises:
            LapNotFoundError: If the lap does not exist or is not accessible.
        """
        data = await self._get(f"/laps/{lap_id}")
        return LapDetail.from_api(data)

    async def get_lap_telemetry(self, lap_id: str, lap_length_m: float) -> pd.DataFrame:
        """Fetch, parse, and cache telemetry CSV for a lap.

        Filters rows to ``PositionType == 3`` (on track only) and adds a
        ``distance_m`` column computed as ``LapDistPct * lap_length_m``.

        Results are LRU-cached (cap: 10 laps) keyed by ``lap_id``.

        Args:
            lap_id: The Garage61 lap identifier (string).
            lap_length_m: Track lap length in metres, used to convert
                ``LapDistPct`` (0.0–1.0) to absolute distance.

        Raises:
            TelemetryUnavailableError: If the API returns 404 for the CSV.
            TelemetryParseError: If expected columns are absent in the CSV.
            APIError: For any other non-2xx response or network error.
        """
        cached = self._telemetry_cache.get(lap_id)
        if cached is not None:
            logger.debug("Telemetry cache hit for lap %s", lap_id)
            return cached

        try:
            response = await self._http.get(f"/laps/{lap_id}/csv")
        except httpx.HTTPError as exc:
            raise APIError(
                f"HTTP error fetching telemetry for lap {lap_id}: {exc}"
            ) from exc

        if response.status_code == 404:
            raise TelemetryUnavailableError(
                f"No telemetry available for lap {lap_id} (404)."
            )
        if not response.is_success:
            raise APIError(
                f"Garage61 API returned {response.status_code} for lap "
                f"{lap_id} CSV: {response.text[:200]}"
            )

        df = self._parse_telemetry_csv(response.text, lap_length_m)
        self._telemetry_cache.put(lap_id, df)
        logger.debug(
            "Fetched and cached telemetry for lap %s (%d on-track rows)",
            lap_id,
            len(df),
        )
        return df

    @staticmethod
    def _parse_telemetry_csv(
        csv_text: str,
        lap_length_m: float,
    ) -> pd.DataFrame:
        """Parse raw CSV text into a filtered, distance-aligned DataFrame.

        Validates the CSV schema by parsing the first row as a
        ``TelemetrySample``. Filters to rows where ``PositionType == 3``
        (on track) and adds ``distance_m = LapDistPct * lap_length_m``.

        Raises:
            TelemetryParseError: If the CSV schema does not match ``TelemetrySample``.
        """
        df = pd.read_csv(StringIO(csv_text))

        try:
            TelemetrySample.from_api(df.iloc[0].to_dict())
        except Exception as exc:
            raise TelemetryParseError(
                f"Telemetry CSV schema does not match TelemetrySample: {exc}. "
                f"Present columns: {list(df.columns)}"
            ) from exc

        df = df[df["PositionType"] == 3].copy()
        df["distance_m"] = df["LapDistPct"] * lap_length_m
        return df.reset_index(drop=True)
