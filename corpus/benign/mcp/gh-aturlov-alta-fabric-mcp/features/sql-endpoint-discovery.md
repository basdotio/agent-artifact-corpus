# Fabric SQL Endpoint Discovery (Design Notes)

## Context
- Current MCP server focuses on lakehouses. `FabricSQLClient` infers the SQL connection string from the lakehouse display name, which limits support to lakehouses only.
- Manual testing of the `GET /v1/workspaces/{workspaceId}/sqlEndpoints` REST API shows it returns only generic SQL endpoints (type always `SQLEndpoint`) and omits Fabric Warehouses.
- Other Fabric APIs such as `/warehouses` expose SQL metadata, so a broader discovery solution must stitch together results from multiple endpoints.

## Goal
Create a reusable MCP tool that aggregates metadata for every Fabric analytical store that exposes a SQL endpoint (lakehouses, warehouses, mirrored databases, etc.). The tool should provide enough information for downstream features—such as query execution—to select a target endpoint without coupling discovery logic to the SQL client implementation.

## High-Level Requirements
1. **Input**: `workspace_id` (required). Optional filters can be considered later.
2. **Output**: JSON payload containing one entry per SQL-capable item. Each entry should include:
   - `workspaceId`
   - `itemId`
   - `itemType`
   - `displayName`
   - `sqlEndpointId` (when available)
   - `server`, `database`, `connectionString` (any combination we can reliably produce)
   - `source`: API used to retrieve the metadata (e.g., `lakehouses`, `warehouses`, `mirroredDatabases`, `sqlEndpoints`)
   - Optional `notes` or `warnings` when values are inferred or partially missing
3. **Auth Support**: Maintain the existing dual-mode auth (interactive + service principal). Ensure scopes satisfy all API calls:
   - `Workspace.Read.All` for listing items (interactive tokens only per docs)
   - `SqlEndpoint.Read.All` or `Item.Read.All` for retrieving connection strings
4. **Pagination**: Handle `continuationToken` for APIs that page results.
5. **Extensibility**: Modular design to add new resource types in the future.

## Proposed Architecture
- **Discovery Orchestrator (New MCP Tool)**
  - Located in `main.py` (or a dedicated module) as `list_sql_endpoints`.
  - Calls individual discovery helpers and merges their outputs.
- **API Helpers (New methods in `fabric_api_client.py`)**
  - `list_lakehouses(workspace_id)` (existing)
  - `get_lakehouse_details(workspace_id, lakehouse_id)` (existing)
  - `list_warehouses(...)`, `get_warehouse_details(...)`
  - `list_mirrored_databases(...)`, `get_mirrored_database_details(...)`
  - `list_sql_endpoints(...)`, `get_sql_endpoint_connection_string(...)`
- **SQL Client (`fabric_sql_client.py`)**
  - Refactor later to accept explicit `server/database/connection_string` inputs.
  - Remove discovery responsibilities once the tool is in place.

## Implementation Notes
- **Lakehouses**: Already return a `connectionString` under `properties.sqlEndpointProperties`. Parse the server host and database name when possible.
- **Warehouses**: REST API exposes connection strings directly. Confirm whether the response contains server/database; otherwise, synthesize from display name.
- **Mirrored Databases / Warehouse mirrors**: Investigate corresponding endpoints for SQL metadata. If missing, capture with `notes` explaining limitations.
- **Generic SQL Endpoints API**: Use as a fallback to ensure we capture any endpoint not surfaced elsewhere.
- **Deduplication**: Use `(workspaceId, sqlEndpointId)` as the primary key. When an item appears in multiple sources, merge fields favoring the most specific API (e.g., warehouse info over generic endpoint info).
- **Error Handling**: Collect errors per resource type and return a `metadataErrors` array so callers understand partial failures.

## Testing Strategy
1. Manual verification against workspaces containing:
   - Lakehouses with SQL endpoints
   - Warehouses
   - Mirrored SQL databases
2. Ensure the tool returns consistent entries even when some APIs are unavailable (e.g., lack of permissions for warehouses).
3. Future automated tests can mock API responses to validate merging logic.

## Future Coding Prompt
> Implement the `list_sql_endpoints` MCP tool described in `features/sql-endpoint-discovery.md`. The tool should aggregate metadata for all SQL-capable Fabric items in the target workspace, using the discovery helper methods outlined in the document. Ensure the response structure matches the "Output" specification and that the implementation gracefully handles missing or partial data.

---
This document captures the current design direction so we can turn it into implementation tasks later without redoing the research.
