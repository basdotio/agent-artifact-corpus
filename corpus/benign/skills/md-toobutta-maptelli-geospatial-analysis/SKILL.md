---
name: geospatial-analysis
description: Geospatial analysis skill for Maptelli covering PostGIS queries, MapLibre GL JS mapping, Deck.gl visualizations, and spatial data processing.
version: 1.0.0
---

# Geospatial Analysis Skill

## Spatial Data Stack

- **Database**: PostgreSQL + PostGIS
- **Frontend Maps**: MapLibre GL JS + Deck.gl + react-map-gl
- **Processing**: GeoAlchemy2, Shapely, GDAL
- **External APIs**: Mapbox (geocoding, isochrones), NextBillion.ai (routing)

## PostGIS Operations

### Common Queries

```sql
-- Properties within polygon
SELECT * FROM properties 
WHERE ST_Within(geom, ST_GeomFromText('POLYGON(...)', 4326));

-- Distance from point
SELECT *, ST_Distance(geom::geography, point::geography) as dist_m
FROM properties
ORDER BY dist_m;

-- Buffer zone
SELECT ST_Buffer(geom::geography, 1000) as buffer_1km
FROM territories;

-- Area calculation
SELECT ST_Area(geom::geography) / 1000000 as sq_km
FROM territories;
```

## MapLibre GL JS

### Basic Map Setup

```typescript
import Map from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

const map = new Map({
  container: 'map',
  style: 'https://demotiles.maplibre.org/style.json',
  center: [-104.9903, 39.7392],
  zoom: 10
});
```

### Property Layer

```typescript
map.addLayer({
  id: 'properties',
  type: 'circle',
  source: 'properties',
  paint: {
    'circle-radius': 6,
    'circle-color': '#22c55e'
  }
});
```

## Deck.gl Overlays

```typescript
import { ScatterplotLayer, GeoJsonLayer } from '@deck.gl/layers';

const layers = [
  new ScatterplotLayer({
    id: 'properties',
    data: properties,
    getPosition: d => [d.lng, d.lat],
    getFillColor: [34, 197, 94, 200],
    getRadius: 100
  }),
  new GeoJsonLayer({
    id: 'territories',
    data: territoryGeoJson,
    filled: true,
    stroked: true,
    getFillColor: [34, 197, 94, 50]
  })
];
```

## Territory Drawing

- **Polygon**: Freeform drawing with map click events
- **Circle**: Center point + radius input
- **Rectangle**: Click and drag bounds

## Coordinate Systems

- **Storage**: SRID 4326 (WGS84 lat/lng)
- **Distance calculations**: Cast to geography for meters
- **Display**: Web Mercator (map default)

## Performance Tips

1. Use spatial indexes on all geometry columns
2. Simplify large polygons before rendering
3. Cluster points at low zoom levels
4. Use vector tiles for large datasets
