# Fulfil Data Warehouse Queries

## Key Tables

### shipments
Customer shipments with nested `moves` array for line items.

**Important columns:**
- `id`, `number` - Shipment identifiers
- `state` - assigned, waiting, done, packed, cancel
- `warehouse`, `warehouse_code` - Fulfillment location
- `shipped_date`, `shipped_at` - When shipped
- `picking_status` - Picking state
- `line_items_count` - Number of lines

**Nested moves array:**
- `moves.product_code` - SKU
- `moves.product_name` - Product name
- `moves.quantity` - Units
- `moves.order_channel_name` - Sales channel
- `moves.move_type` - 'outgoing' for customer shipments
- `moves.state` - Move state (exclude 'cancelled')
- `moves.from_location_name` - Pick location

### products
Product master data.

**Key columns:**
- `code` - SKU
- `template_name` - Product template
- `quantity_per_case` - Case pack size (often null)
- `default_box_type_name` - Cartonization box

### inventory_by_location
Current inventory positions.

**Key columns:**
- `product_code` - SKU
- `location_name` - Bin/location
- `warehouse_name` - Warehouse
- `quantity_on_hand`, `quantity_available`

## Common Query Patterns

### Discover Channels
```sql
SELECT DISTINCT moves.order_channel_name
FROM shipments, UNNEST(moves) as moves
WHERE moves.order_channel_name IS NOT NULL
LIMIT 50
```

### Verify Warehouse Filter
```sql
SELECT warehouse, warehouse_code, COUNT(DISTINCT id) as shipments
FROM shipments s, UNNEST(s.moves) as m
WHERE m.order_channel_name = '[Channel]'
  AND s.state = 'assigned'
GROUP BY warehouse, warehouse_code
```

### Order State Distribution
```sql
SELECT s.state, COUNT(DISTINCT s.id) as shipments
FROM shipments s, UNNEST(s.moves) as m
WHERE m.order_channel_name = '[Channel]'
  AND m.state != 'cancelled'
GROUP BY s.state
ORDER BY shipments DESC
```

### Unit Distribution
```sql
WITH shipment_units AS (
  SELECT s.id, SUM(m.quantity) as total_units
  FROM shipments s, UNNEST(s.moves) as m
  WHERE m.order_channel_name = '[Channel]'
    AND s.state = 'assigned'
    AND s.warehouse = '[Warehouse]'
    AND m.state != 'cancelled'
    AND m.move_type = 'outgoing'
  GROUP BY s.id
)
SELECT 
  CASE 
    WHEN total_units = 1 THEN '1 unit'
    WHEN total_units = 2 THEN '2 units'
    WHEN total_units = 3 THEN '3 units'
    WHEN total_units BETWEEN 4 AND 5 THEN '4-5 units'
    ELSE '6+ units'
  END as bucket,
  COUNT(*) as shipments,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as pct
FROM shipment_units
GROUP BY bucket
ORDER BY MIN(total_units)
```

### SKU Line Distribution
```sql
WITH shipment_skus AS (
  SELECT s.id, COUNT(DISTINCT m.product_code) as sku_count
  FROM shipments s, UNNEST(s.moves) as m
  WHERE [filters]
  GROUP BY s.id
)
SELECT 
  CASE 
    WHEN sku_count = 1 THEN '1 SKU'
    WHEN sku_count = 2 THEN '2 SKUs'
    WHEN sku_count = 3 THEN '3 SKUs'
    ELSE '4+ SKUs'
  END as bucket,
  COUNT(*) as shipments,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as pct
FROM shipment_skus
GROUP BY bucket
ORDER BY MIN(sku_count)
```

### Top SKUs by Order Frequency
```sql
SELECT 
  m.product_code as sku,
  m.product_name,
  COUNT(DISTINCT s.id) as orders,
  SUM(m.quantity) as units,
  ROUND(COUNT(DISTINCT s.id) * 100.0 / [total_orders], 1) as pct
FROM shipments s, UNNEST(s.moves) as m
WHERE [filters]
GROUP BY m.product_code, m.product_name
ORDER BY orders DESC
LIMIT 20
```

### Single-SKU Single-Unit Orders by SKU
```sql
WITH shipment_composition AS (
  SELECT s.id, 
         COUNT(DISTINCT m.product_code) as sku_count,
         MAX(m.product_code) as single_sku
  FROM shipments s, UNNEST(s.moves) as m
  WHERE [filters]
  GROUP BY s.id
)
SELECT single_sku, COUNT(*) as single_sku_orders
FROM shipment_composition
WHERE sku_count = 1
GROUP BY single_sku
ORDER BY single_sku_orders DESC
LIMIT 20
```

### Product Pairs (Co-location Analysis)
```sql
WITH shipment_products AS (
  SELECT s.id as shipment_id, m.product_code as sku, m.product_name
  FROM shipments s, UNNEST(s.moves) as m
  WHERE [filters]
),
multi_sku_shipments AS (
  SELECT shipment_id FROM shipment_products
  GROUP BY shipment_id HAVING COUNT(DISTINCT sku) >= 2
),
pairs AS (
  SELECT 
    LEAST(a.sku, b.sku) as sku1,
    GREATEST(a.sku, b.sku) as sku2,
    LEAST(a.product_name, b.product_name) as product1,
    GREATEST(a.product_name, b.product_name) as product2
  FROM shipment_products a
  JOIN shipment_products b ON a.shipment_id = b.shipment_id AND a.sku < b.sku
  WHERE a.shipment_id IN (SELECT shipment_id FROM multi_sku_shipments)
)
SELECT sku1, sku2, product1, product2, COUNT(*) as frequency
FROM pairs
GROUP BY sku1, sku2, product1, product2
ORDER BY frequency DESC
LIMIT 15
```

### Shipping Velocity (Last 7 Days)
```sql
SELECT 
  s.shipped_date,
  COUNT(DISTINCT s.id) as shipments,
  SUM(m.quantity) as units
FROM shipments s, UNNEST(s.moves) as m
WHERE m.order_channel_name = '[Channel]'
  AND s.state = 'done'
  AND s.shipped_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND m.state != 'cancelled'
  AND m.move_type = 'outgoing'
GROUP BY s.shipped_date
ORDER BY s.shipped_date DESC
```

### Primary Pick Locations for Top SKUs
```sql
WITH inventory_ranked AS (
  SELECT product_code, location_name, quantity_available,
         ROW_NUMBER() OVER (PARTITION BY product_code ORDER BY quantity_available DESC) as rank
  FROM inventory_by_location
  WHERE product_code IN ([top_skus])
    AND warehouse_name = '[Warehouse]'
    AND quantity_available > 0
    AND location_name NOT LIKE '%Zone%'
)
SELECT product_code, location_name as primary_location, quantity_available
FROM inventory_ranked WHERE rank = 1
```

### Bundle SKU Identification
```sql
SELECT DISTINCT m.product_code, m.product_name
FROM shipments s, UNNEST(s.moves) as m
WHERE [filters]
  AND (UPPER(m.product_code) LIKE '%BUNDLE%' OR UPPER(m.product_name) LIKE '%BUNDLE%')
```

### Case Quantities and Default Boxes
```sql
SELECT code, template_name, quantity_per_case, default_box_type_name
FROM products
WHERE code IN ([top_skus])
ORDER BY code
```
