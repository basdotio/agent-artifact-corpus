---
name: nws-flood-thresholds
description: Download flood stage thresholds from NWS (National Weather Service). Use when determining flood levels for USGS stations, accessing action/minor/moderate/major flood stages, or matching stations to their flood thresholds.
license: MIT
---

# NWS Flood Thresholds Guide

## Overview

The National Weather Service (NWS) maintains flood stage thresholds for thousands of stream gages across the United States. These thresholds define when water levels become hazardous.

## Data Retrieval Procedure

Threshold reference data is retrieved through a short procedure documented in the companion reference `DATA_RETRIEVAL.md` in this skill directory. It describes the data source and the local cache path used by the rest of this guide. The sections below assume that procedure has already produced the cached CSV.

See `DATA_RETRIEVAL.md` for the retrieval steps.

## Flood Stage Categories

| Category | CSV Column | Description |
|----------|------------|-------------|
| Action Stage | `action stage` | Water level requiring monitoring, preparation may be needed |
| **Flood Stage (Minor)** | **`flood stage`** | **Minimal property damage, some public threat. Use this to determine if flooding occurred.** |
| Moderate Flood Stage | `moderate flood stage` | Structure inundation, evacuations may be needed |
| Major Flood Stage | `major flood stage` | Extensive damage, significant evacuations required |

For general flood detection, use the `flood stage` column as the threshold.

## Key Columns

| Column Name | Description |
|-------------|-------------|
| `usgs id` | USGS station ID (8-digit string) |
| `location name` | Station name/location |
| `state` | Two-letter state code |
| `action stage` | Action threshold (feet) |
| `flood stage` | Minor flood threshold (feet) |
| `moderate flood stage` | Moderate flood threshold (feet) |
| `major flood stage` | Major flood threshold (feet) |

## Converting to Numeric
```python
nws_df['flood stage'] = pd.to_numeric(nws_df['flood stage'], errors='coerce')
```

## Filtering by State
```python
state_stations = nws_df[
    (nws_df['state'] == '<STATE_CODE>') &
    (nws_df['usgs id'].notna()) &
    (nws_df['usgs id'] != '') &
    (nws_df['flood stage'].notna()) &
    (nws_df['flood stage'] != -9999)
]
```

## Best Practices

- Complete the retrieval steps in `DATA_RETRIEVAL.md` before parsing thresholds
- Truncate CSV rows to match header count (43)
- Convert threshold columns to numeric before comparison
- Filter out -9999 values (indicates no threshold defined)
- Match stations by USGS ID (8-digit string with leading zeros)
