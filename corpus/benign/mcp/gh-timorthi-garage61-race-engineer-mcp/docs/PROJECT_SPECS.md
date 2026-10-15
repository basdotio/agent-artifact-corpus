# garage61-race-engineer MCP Server — Project Specification

## 1. System Overview

An MCP server built with FastMCP that acts as a telemetry analysis engine. It interfaces with the Garage61 API to fetch telemetry files for lap times, processes them locally using pandas, and returns high-level coaching insights to the LLM.

---

## 2. Core Constraints

- **Distance-Based Alignment**: All telemetry comparisons must be interpolated to a distance-based x-axis (meters), not time-based.
- **Data Aggregation**: Raw telemetry must be condensed. The server identifies braking events and returns statistics for those events, not every data point.
- **Zero-Cloud Processing**: All math happens within the Python runtime of the MCP server.
- **Separation of Concerns**: Tools must remain composable. No tool should internally chain into another — the agent (or human) decides the next step based on what a tool returns.

---

## 3. Authentication

Garage61 API credentials are passed via environment variable and loaded at startup using `pydantic-settings`.

```
GARAGE61_API_KEY=...
```

The key is sent as a Bearer token on every request:

```
Authorization: Bearer <GARAGE61_API_KEY>
```

No credentials are ever accepted as tool arguments.

---

## 4. Garage61 API

Base URL: `https://garage61.net/api/v1`

The full OpenAPI spec is saved at `docs/garage61_openapi.json`.

### Key endpoints used

| Endpoint | Purpose |
|---|---|
| `GET /laps` | Search laps with filtering (temperature, session type, cleanliness, etc.) |
| `GET /laps/{id}` | Metadata for a specific lap |
| `GET /laps/{id}/csv` | Download telemetry as CSV |
| `GET /tracks` | Enumerate available tracks (for ID lookup) |
| `GET /cars` | Enumerate available cars (for ID lookup) |

### ID types

Track IDs and car IDs are **integers** (`int64`). Lap IDs are **strings**.

### Temperature filtering

`/laps` natively supports `minConditionsAirTemp`, `maxConditionsAirTemp`, `minConditionsTrackTemp`, `maxConditionsTrackTemp`. The `search_similar_conditions` tool maps `target ± temp_tolerance_celsius` directly to these query parameters — no client-side filtering required.

### Telemetry format

Telemetry is a **CSV file** returned from `GET /laps/{id}/csv`. Confirmed columns (verified against a real API response):

| Column | Type | Description |
|---|---|---|
| `Speed` | float | Speed — m/s |
| `LapDistPct` | float | Lap distance fraction 0.0–1.0 |
| `Lat` | float | GPS latitude |
| `Lon` | float | GPS longitude |
| `Brake` | float | Brake pressure 0.0–1.0 |
| `Throttle` | float | Throttle position 0.0–1.0 |
| `RPM` | float | Engine RPM |
| `SteeringWheelAngle` | float | Steering angle — radians |
| `Gear` | int | Current gear |
| `Clutch` | float | Clutch position 0.0–1.0 |
| `ABSActive` | bool | ABS active flag |
| `DRSActive` | bool | DRS active flag |
| `LatAccel` | float | Lateral acceleration — m/s² |
| `LongAccel` | float | Longitudinal acceleration — m/s² |
| `VertAccel` | float | Vertical acceleration — m/s² |
| `Yaw` | float | Yaw angle — radians |
| `YawRate` | float | Yaw rate — rad/s |
| `PositionType` | int | `0`=Unknown, `1`=Pit lane, `2`=Pit stop, `3`=On track, `4`=Off track |

Each row is modelled by `TelemetrySample` in `src/garage61/models.py`.

---

## 5. Tool Definitions

### `list_tracks`

Returns available tracks so the agent can resolve a track name to a numeric `track_id`.

**Inputs:** none

**Output:**
```json
{
  "tracks": [
    { "track_id": 218, "name": "Watkins Glen International" }
  ]
}
```

Track data is loaded from `static/tracks.json` at startup. iRacing track content changes at most a few times per season, so a live API call on every request is unnecessary overhead. If `static/tracks.json` is missing, the server falls back to `GET /tracks` and logs a warning. The same `/tracks` endpoint is used to (re-)seed the static file via the refresh CLI (see §13).

---

### `list_cars`

Returns available cars so the agent can resolve a car name to a numeric `car_id`.

**Inputs:** none

**Output:**
```json
{
  "cars": [
    { "car_id": 97, "name": "Dallara F3" }
  ]
}
```

Same pattern as `list_tracks`: loaded from `static/cars.json` at startup, falls back to `GET /cars` if missing.

---

### `search_similar_conditions`

Finds laps on a given track/car combination with weather conditions close to a target.

**Inputs:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `track_id` | integer | required | Garage61 track ID |
| `car_id` | integer | required | Garage61 car ID |
| `target_air_temp` | float | required | Target air temperature (°C) |
| `target_track_temp` | float | required | Target track temperature (°C) |
| `temp_tolerance_celsius` | float | `3.0` | ±window for temperature matching |
| `session_types` | list[int] | `[1,2,3]` | 1=Practice, 2=Qualifying, 3=Race |

**Logic:**
1. Call `GET /laps` with:
   - `tracks=[track_id]`, `cars=[car_id]`
   - `minConditionsAirTemp = target_air_temp - temp_tolerance_celsius`
   - `maxConditionsAirTemp = target_air_temp + temp_tolerance_celsius`
   - `minConditionsTrackTemp = target_track_temp - temp_tolerance_celsius`
   - `maxConditionsTrackTemp = target_track_temp + temp_tolerance_celsius`
   - `seeTelemetry=true` (only return laps with telemetry available)
   - `sessionTypes=session_types`
   - `group=none` (return all matching laps, not just personal bests)
2. Sort results by lap time ascending (fastest first).

**Output:**
```json
{
  "laps": [
    {
      "lap_id": "string",
      "lap_time_ms": 92450,
      "driver_name": "string",
      "driver_irating": 3200,
      "session_type": 2,
      "air_temp_c": 24.1,
      "track_temp_c": 31.8,
      "temp_delta_air": 0.9,
      "temp_delta_track": 1.8
    }
  ],
  "search_params": {
    "tolerance_used_celsius": 3.0,
    "total_laps_found": 12
  }
}
```

If `laps` is empty, the agent should retry with a wider `temp_tolerance_celsius`. The `search_params` block gives the agent the context it needs to do this intelligently.

> **Note on multi-driver access**: The Garage61 API currently returns only the authenticated user's laps. The tool's output shape is designed to be identical when multi-driver access becomes available — only the underlying API call will change.

---

### `get_lap_comparison`

Compares two laps at a corner-by-corner level and returns coaching insights for where time was lost.

**Inputs:**

| Parameter | Type | Description |
|---|---|---|
| `my_lap_id` | string | The lap to analyse |
| `reference_lap_id` | string | The benchmark lap to compare against |

**Logic:**

1. Fetch telemetry CSV for both laps via `GET /laps/{id}/csv`.
2. Parse CSV into a DataFrame; filter to rows where `PositionType == 3` (on track only).
3. Interpolate both laps onto a common distance axis (1m resolution).
4. Segment the lap into corners (see §6).
5. For each corner, compute all metrics defined in §7.
6. Compute time delta per corner using the speed-integration method (see §7, Time Delta Computation).
7. Rank corners by total time delta and return the top 3–5 where the most time was lost.

**Output:**
```json
{
  "total_time_delta_ms": 680,
  "track_name": "Watkins Glen International",
  "segmentation_source": "track_map",
  "corners": [
    {
      "corner_id": 1,
      "turn_number": 1,
      "turn_name": "The 90",
      "distance_start_m": 228,
      "distance_end_m": 342,
      "time_delta_ms": 210,
      "time_delta_breakdown": {
        "braking_phase_ms": 30,
        "coast_phase_ms": 140,
        "throttle_phase_ms": 40
      },
      "my_lap": { "...": "see §7" },
      "reference_lap": { "...": "see §7" }
    }
  ]
}
```

---

## 6. Corner Segmentation

Corner identification uses a two-tier approach, preferring structured track map data where available and falling back to algorithmic detection.

### Tier 1: Static Track Map (preferred)

A curated JSON file is stored per track under `track_maps/{track_id}.json`. These files define the canonical turn list for that circuit, keyed by `lap_dist_pct` (iRacing's native 0.0–1.0 lap distance percentage). Example schema:

```json
{
  "track_id": 218,
  "track_name": "Watkins Glen International",
  "lap_length_m": 5435,
  "turns": [
    {
      "number": 1,
      "name": "The 90",
      "entry_pct": 0.042,
      "apex_pct": 0.051,
      "exit_pct": 0.063
    }
  ]
}
```

`entry_pct`, `apex_pct`, and `exit_pct` are derived from community sources (primarily CrewChief corner data) and cross-referenced with steering angle peaks and speed minima from reference telemetry. When the server loads a lap, `lap_dist_pct` values are converted to absolute meters using the track's `lap_length_m`.

> **Note**: Track map `track_id` values must match the integer IDs used by the Garage61 API.

**Output fields when using a track map:**
```json
{
  "corner_id": 1,
  "turn_number": 1,
  "turn_name": "The 90",
  "segmentation_source": "track_map"
}
```

### Tier 2: Algorithmic Fallback

Used when no `track_maps/{track_id}.json` exists. A corner is detected as any continuous region where:
- Speed drops more than **15%** below the rolling maximum (200m window), **and**
- The low-speed region persists for at least **50m**.

Corners are numbered sequentially from the start/finish line. Turn names are omitted.

> **Known limitation**: Corners that straddle the start/finish line (distance 0m / lap_length_m) may be split into two partial detections by the rolling window. This is a known edge case of the algorithmic fallback and is not present when using a track map.

**Output fields when using the fallback:**
```json
{
  "corner_id": 3,
  "turn_number": 3,
  "turn_name": null,
  "segmentation_source": "algorithmic"
}
```

`segmentation_source` is always included in tool output so the LLM and user know which method was used.

### Adding New Track Maps

Track map files can be added manually to `track_maps/` without any code changes. The server loads them at startup. Community contributions for common iRacing circuits are encouraged.

---

## 7. Per-Corner Telemetry Metrics

### Time Delta Computation

Time cannot be directly compared between two distance-aligned laps. It is reconstructed by integrating speed over distance:

```
Δt = ∫ (1/v_ref(d) − 1/v_mine(d)) dd
```

Over a corner segment `[d_start, d_end]`, the discrete approximation is:

```python
delta_t_ms = sum((1/v_ref[i] - 1/v_mine[i]) * dd) * 1000
```

where `dd` is the distance step (1m). Positive values mean time lost vs. reference.

The total corner delta is decomposed into three phases:

| Phase | Definition |
|---|---|
| `braking_phase_ms` | From brake initiation to V-min |
| `coast_phase_ms` | During the coast/rotation phase |
| `throttle_phase_ms` | From throttle application to corner exit |

### Braking Zone

| Metric | Definition |
|---|---|
| `brake_initiation_m` | Distance where brake pressure first exceeds 5% |
| `brake_initiation_delta_m` | How many meters earlier/later vs. reference (negative = braking later) |
| `peak_brake_pressure_pct` | Maximum brake value in the zone |
| `brake_work` | Area under the brake pressure curve (integral over distance) |
| `trail_braking_distance_m` | Distance where brake pressure is between 1% and 20% |
| `coast_distance_m` | Distance where both throttle and brake are 0% |

### Corner Apex

| Metric | Definition |
|---|---|
| `v_min_mps` | Minimum speed through the corner (m/s) |
| `v_min_distance_m` | Distance at which minimum speed occurs |
| `v_min_distance_delta_m` | How many meters earlier/later vs. reference |
| `gear_at_v_min` | Gear selected at the point of minimum speed |
| `steering_angle_at_brake_initiation` | Steering input at the moment braking begins (indicator of stability risk) |

### Exit

| Metric | Definition |
|---|---|
| `throttle_application_m` | Distance where throttle first exceeds 10% after apex |
| `throttle_application_delta_m` | How many meters earlier/later vs. reference (negative = throttle earlier) |

---

## 8. Error Handling

Tools return structured errors rather than raising exceptions. The LLM receives actionable context.

```json
{
  "error": "lap_not_found",
  "message": "Lap ID 'abc123' was not found or is not accessible with the current API key.",
  "recoverable": false
}
```

| Error code | When |
|---|---|
| `lap_not_found` | `GET /laps/{id}` returns 404 |
| `telemetry_unavailable` | Lap exists but has no telemetry CSV |
| `telemetry_parse_error` | CSV columns don't match expected schema |
| `api_error` | Upstream Garage61 API returned a non-2xx response |
| `no_laps_found` | `search_similar_conditions` returned zero results |

---

## 9. In-Process Caching

Telemetry payloads are large (potentially 10–50MB per lap) and fetches are expensive. A simple LRU cache keyed on `lap_id` is maintained for the lifetime of the server process, capped at **10 laps** to bound memory use. A lap's telemetry is only fetched once per session.

Track and car data are loaded from `static/tracks.json` and `static/cars.json` at startup and held in memory. These files change infrequently (at most a few times per iRacing season) and are refreshed manually via the seed CLI rather than on every server start.

---

## 10. Human-in-the-Loop Flow

The two-tool design creates a natural pause point for human input:

1. Agent calls `search_similar_conditions` → returns a list of candidate laps with driver names and iRatings.
2. **User reviews the list and selects a reference lap** (or the agent selects automatically if operating autonomously).
3. Agent calls `get_lap_comparison` with the chosen `reference_lap_id`.

`search_similar_conditions` never internally triggers a comparison. The agent or user always controls step 3.

---

## 11. Dependencies

```toml
[project]
dependencies = [
    "fastmcp>=3.1.0",
    "pandas",
    "numpy",
    "httpx",
    "pydantic-settings",
]
```

---

## 12. Project Structure

```
garage61-race-engineer-mcp/
├── src/
│   └── garage61_mcp/
│       ├── __init__.py
│       ├── server.py          # FastMCP app + tool registration
│       ├── garage61_client.py # httpx-based Garage61 API client + LRU cache
│       ├── telemetry.py       # Distance alignment, corner segmentation, metrics
│       └── models.py          # Pydantic models for inputs/outputs
├── track_maps/
│   ├── 218.json               # Watkins Glen (numeric track_id, not slug)
│   └── ...
├── static/
│   ├── tracks.json            # Seeded from GET /tracks; refresh manually each season
│   └── cars.json              # Seeded from GET /cars; refresh manually each season
├── docs/
│   └── garage61_openapi.json  # Full Garage61 OpenAPI spec
├── pyproject.toml
└── PROJECT_SPECS.md
```

---

## 13. Future Work / TODOs

- [x] **Confirm CSV column names**: Verified against a real `GET /laps/{id}/csv` response. Column table updated in §4; `TelemetrySample` model added to `src/garage61/models.py`.
- [x] **Static data seed CLI**: Build a small CLI tool (`scripts/seed_static.py`) that calls `GET /tracks` and `GET /cars` and writes the results to `static/tracks.json` and `static/cars.json`. Run once at setup and again when new iRacing content is released.
- [ ] **Track map bootstrapping CLI**: Build a small CLI tool that runs a reference lap through the algorithmic corner detector and outputs a pre-filled `track_maps/{track_id}.json` stub with turn boundaries, ready for manual annotation.
- [ ] **Multi-driver access**: When Garage61 exposes cross-user lap access, only `garage61_client.py` needs updating — tool output shapes are already designed for it.
