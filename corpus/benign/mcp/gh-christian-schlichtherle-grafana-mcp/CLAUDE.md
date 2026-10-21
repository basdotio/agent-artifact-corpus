# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository provides a fully implemented MCP (Model Context Protocol) server for CRUD operations on Grafana dashboards with comprehensive tag-based security. The MCP server:

- Tags created dashboards to mark itself as the origin
- Implements dual security: separate tag requirements for read vs write operations
- Provides stealth security where unauthorized resources become invisible (404-like behavior)
- Supports chroot-style folder access restrictions for complete isolation
- Supports multi-cluster Grafana configurations
- Uses FastMCP framework for MCP tool implementation
- Uses efficient set-based tag operations for optimal performance

## Dependencies and Environment

The project uses Python 3.11+ with these key dependencies:
- `httpx>=0.28.1` - HTTP client for Grafana API calls
- `mcp[cli]>=1.10.1` - MCP server framework

Dependency management is handled by `uv` (based on presence of `uv.lock`).

## Configuration

The MCP server is configured via environment variables:

- `GRAFANA_CLUSTER_URLS` - Space-separated key=value pairs defining cluster URLs
- `GRAFANA_API_TOKENS` - Space-separated key=value pairs defining cluster API tokens (optional)
- `GRAFANA_READ_ACCESS_TAGS` - Space-separated set of tags required for read access (defaults to empty = unrestricted)
- `GRAFANA_WRITE_ACCESS_TAGS` - Space-separated set of tags required for write access (defaults to "MCP")
- `GRAFANA_ROOT_FOLDER` - Root folder path acting as access boundary (defaults to "/")

Examples:
```bash
# Local development without authentication
export GRAFANA_CLUSTER_URLS="localhost=http://localhost:3000"

# Mixed environment (local without auth, prod with auth)
export GRAFANA_CLUSTER_URLS="localhost=http://localhost:3000 prod=https://grafana.prod.com"
export GRAFANA_API_TOKENS="prod=glsa_def456"

# Security restrictions with equal read/write tags (most restrictive)
export GRAFANA_CLUSTER_URLS="dev=https://grafana.dev.com prod=https://grafana.prod.com"
export GRAFANA_API_TOKENS="dev=glsa_abc123 prod=glsa_def456"
export GRAFANA_READ_ACCESS_TAGS="MCP AI_GENERATED"
export GRAFANA_WRITE_ACCESS_TAGS="MCP AI_GENERATED"
export GRAFANA_ROOT_FOLDER="/mcp-managed"

# Partial read restrictions (read ⊆ write, allows reading some external dashboards)
export GRAFANA_CLUSTER_URLS="dev=https://grafana.dev.com prod=https://grafana.prod.com"
export GRAFANA_API_TOKENS="dev=glsa_abc123 prod=glsa_def456"
export GRAFANA_READ_ACCESS_TAGS="MCP"
export GRAFANA_WRITE_ACCESS_TAGS="MCP AI_GENERATED CUSTOM"
export GRAFANA_ROOT_FOLDER="/mcp-managed"
```

## Development Commands

- Install dependencies: `uv sync` or `pip install -e .`
- Run the MCP server: `python main.py`
- The server validates configuration at startup and lists all available tools

## Architecture

### Code Structure
```
grafana_mcp/
├── __init__.py
├── config.py              # Environment variable parsing and validation
├── client.py              # HTTP client for Grafana API operations
├── tools/
│   ├── __init__.py
│   ├── base.py            # DRY utilities and decorators for tools
│   ├── clusters.py        # Cluster management tools
│   ├── dashboards.py      # Dashboard CRUD tools
│   ├── folders.py         # Folder management tools (NEW)
│   └── datasources.py     # Datasource tools
└── security/
    ├── __init__.py
    └── validators.py      # Tag and folder validation
```

### Available MCP Tools

#### Discovery

Tools for discovering and exploring Grafana resources across clusters.

**Cluster Management:**
- `list_clusters()` - List all configured Grafana cluster names
- `check_cluster_health(cluster: str)` - Check health and connectivity of a Grafana cluster

**Search Operations:**
- `search(cluster: str, *, query: str = "", tags: list = [], starred: bool = False, folder_uids: list = [], dashboard_uids: list = [], dashboard_ids: list = [], type: str = "", limit: int = 1000, page: int = 1)` - Search dashboards and folders with comprehensive filtering options

**Dashboard Discovery:**
- `read_dashboard(cluster: str, dashboard_uid: str)` - Read dashboard configuration and metadata (subject to read access tags)
- `inspect_dashboard(cluster: str, dashboard_uid: str)` - Detailed structural analysis including panels, datasources, variables, layout, and validation issues (subject to read access tags)

**Folder Discovery:**
- `list_folders(cluster: str, *, parent_uid: str = "")` - List folders with metadata, optionally under a parent folder
- `get_folder(cluster: str, folder_uid: str)` - Get detailed folder information including hierarchy and permissions

**Datasource Discovery:**
- `list_datasources(cluster: str)` - List all datasources with name, type, UID, and other metadata

#### Editing

Tools for creating, modifying, and managing Grafana resources with tag-based security controls.

**Dashboard Management:**
- `create_dashboard(cluster: str, dashboard_json: dict, *, folder_uid: str = "")` - Create dashboard with automatic protection tags and folder assignment
- `update_dashboard(cluster: str, dashboard_uid: str, dashboard_json: dict)` - Update existing dashboard (requires protection tags)
- `delete_dashboard(cluster: str, dashboard_uid: str)` - Delete dashboard (requires protection tags)
- `copy_dashboard(source_cluster: str, source_uid: str, new_title: str, *, target_cluster: str = "", folder_uid: str = "", target_uid: str = "")` - Copy dashboard with intelligent UID handling, auto-overwrite, and folder preservation

**Folder Management:**
- `create_folder(cluster: str, title: str, *, parent_uid: str = "")` - Create folder, optionally as subfolder under parent
- `update_folder(cluster: str, folder_uid: str, title: str, *, parent_uid: str = "")` - Update/rename folder and optionally move to different parent
- `delete_folder(cluster: str, folder_uid: str, *, force_delete_rules: bool = False)` - Delete folder with optional alert rule cleanup

#### Testing

Tools for validating, testing, and analyzing dashboard quality and data accuracy.

**Validation & Quality Assurance:**
- `validate_dashboard(cluster: str, dashboard_uid: str)` - Comprehensive schema validation and best practices checking with pass/fail status
- `compare_dashboards(cluster: str, dashboard_uid_a: str, dashboard_uid_b: str, *, compare_cluster_b: str = "")` - Compare two dashboards showing structural and configuration differences

**Data Verification & Testing:**
- `snapshot_dashboard(cluster: str, dashboard_uid: str, *, snapshot_name: str = "", expires_hours: int = 24, time_from: str = "now-6h", time_to: str = "now")` - Create snapshot with current data for inspection and testing (expires after 24 hours by default)
- `test_panel_render(cluster: str, dashboard_uid: str, panel_id: int, *, width: int = 1000, height: int = 500, time_from: str = "now-6h", time_to: str = "now", save_to_file: str = "")` - Render panel as PNG for visual validation and quality assurance

### Key Implementation Details

1. **DRY Architecture**: Base utilities in `tools/base.py` eliminate code duplication:
   - `@grafana_tool` decorator handles cluster validation, client creation, and error handling
   - `@cluster_only_tool` for tools that only need cluster validation
   - Consistent error handling and HTTP client management across all tools

2. **Stateless Architecture**: Server maintains no internal state for optimal remote HTTP operation:
   - All tools require explicit cluster parameter
   - No current/active cluster concept - perfect for multi-client environments
   - AI agents maintain cluster context within conversation scope

3. **MCP Parameter Handling**: Uses falsy defaults (`""`, `[]`, `False`) instead of `None` for optional parameters to work with MCP protocol

4. **Named Parameters**: All tools except cluster parameter use named parameters (with `*` separator)

5. **Folder Hierarchy Support**: Complete folder management with hierarchical structure:
   - Navigate parent-child folder relationships
   - Create subfolders and move folders between parents
   - Explore folder tree structure for AI agent navigation

6. **Enhanced Search**: Generic `search()` tool:
   - Searches both dashboards and folders with type filtering

7. **Cross-Cluster Dashboard Copying**: Advanced `copy_dashboard()` tool with intelligent UID handling and auto-overwrite:
   - **Same-cluster copying**: Generates new UID automatically (unless explicit `target_uid` provided)
   - **Cross-cluster copying**: Preserves source UID by default (for consistent deployment)
   - **Auto-overwrite**: When target dashboard exists, validates security tags and updates automatically
   - **Explicit control**: Optional `target_uid` parameter overrides all default behavior
   - **Stateless operation**: All operations require explicit cluster parameter
   - **Folder inheritance**: Automatically inherits source folder unless overridden

8. **Security Model**: 
   - Auto-adds protection tags to created/copied dashboards
   - Validates tags before allowing updates/deletes
   - Implements dual read/write security with stealth mode
   - Prevents dashboard overwrites during creation

9. **Error Handling**: Comprehensive validation with helpful error messages, including HTTP status code translation

10. **HTTP Client**: Context manager pattern with proper connection management

11. **Automatic Version Management**: Dashboard version handling is delegated to Grafana's API:
   - Version fields are removed from all dashboard operations (create, update, copy)
   - Grafana automatically increments versions during updates with `overwrite: true`
   - Eliminates manual version tracking complexity and prevents version conflicts
   - Ensures optimal concurrency control through Grafana's built-in version management

### Authentication

- **Optional Authentication**: Clusters can run with or without authentication
- **Service Account Tokens**: For authenticated clusters, uses Bearer tokens via `GRAFANA_API_TOKENS`
- **Local Development**: Supports unauthenticated Grafana instances (common in Docker containers)
- **Mixed Environments**: Can have both authenticated and unauthenticated clusters configured simultaneously
- **Automatic Detection**: HTTP client automatically includes/excludes Authorization header based on token presence

### Security Features

- Tag-based access control for both read and write operations
- Chroot-style folder access restrictions 
- Stealth mode for unauthorized resource access
- UID collision prevention
- Automatic protection tag injection
- Set-based tag validation for optimal performance

## Security Model

### Tag-Based Access Control
The MCP server implements comprehensive tag-based security for both read and write operations using set-based tag matching:

**Read Protection:**
- Controlled by `GRAFANA_READ_ACCESS_TAGS` environment variable
- Default: Empty set (unrestricted read access)
- When set: Resource must contain ALL specified tags to be accessible
- Unauthorized resources return 404 errors and are excluded from search results

**Write Protection:**
- Controlled by `GRAFANA_WRITE_ACCESS_TAGS` environment variable  
- Default: {"MCP"}
- Must not be empty - at least one tag is required
- Resources must contain ALL specified tags to be modified
- Created/copied dashboards automatically receive protection tags

**Critical Configuration Requirement:**
- `GRAFANA_READ_ACCESS_TAGS` must be a subset of `GRAFANA_WRITE_ACCESS_TAGS`
- This ensures the MCP server can read dashboards it creates
- The server validates this at startup and will fail with a clear error message if violated
- Example: If write tags are `"MCP AI_GENERATED"`, read tags can be `""`, `"MCP"`, `"AI_GENERATED"`, or `"MCP AI_GENERATED"`

### Folder-Based Access Control (Chroot-style)
The `GRAFANA_ROOT_FOLDER` environment variable acts as a chroot-style access boundary:

- **Default**: "/" (unrestricted access to all folders)
- **Restricted**: "/mcp-managed" - only allows access to the "mcp-managed" folder and its subfolders
- **Behavior**: Like Unix chroot, the MCP server cannot access anything outside this folder tree
- **Applies to**: All dashboard and folder operations (read and write)
- **Security**: Prevents access to folders outside the designated boundary

### Security Behavior
- **Stealth Mode**: Unauthorized resources become invisible (simulate 404)
- **Search Filtering**: Results exclude unauthorized dashboards
- **Complete Coverage**: All read and write operations are protected
- **Tag Inheritance**: Created resources automatically get protection tags
- **Folder Isolation**: Operations restricted to root folder boundary
- **Set-based Matching**: Efficient tag validation using set operations

## Dashboard Testing and Validation Workflow

The MCP server provides comprehensive tools for testing and validating Grafana dashboards. This workflow addresses the visibility problem when creating or modifying dashboards programmatically.

### Testing Workflow Phases

#### 1. Development Phase - Structural Analysis
Use `inspect_dashboard` to understand dashboard structure before making changes:

```python
# Get detailed structural analysis
inspection = inspect_dashboard("fret-dev", "dashboard-uid")

# Review:
# - Panel configurations and datasources
# - Template variables and their types  
# - Grid positions and layout
# - Query structures (without execution)
# - Validation issues (missing datasources, overlaps)
```

**Benefits:**
- Understand existing dashboard without guessing
- Identify all datasources and variables used
- Spot layout and configuration issues
- Get panel-by-panel breakdown

#### 2. Validation Phase - Schema Compliance  
Run `validate_dashboard` for comprehensive validation:

```python
# Validate against schema and best practices
validation = validate_dashboard("fret-dev", "dashboard-uid")

# Check validation_status: "PASS" or "FAIL"
# Review issues, warnings, and info messages
# Fix any schema violations before deployment
```

**Validation Categories:**
- **Schema**: Required fields, UID format, title length
- **Layout**: Grid positions, overlapping panels, dimensions
- **Panels**: IDs, types, datasource references
- **Queries**: RefIDs, query structure
- **Variables**: Names, types, duplicates
- **Performance**: Refresh rates, panel count
- **Best Practices**: Grafana recommendations

#### 3. Data Verification - Snapshot Creation
Create snapshots to see actual data without executing queries directly:

```python
# Create snapshot with current data for last 30 days
snapshot = snapshot_dashboard(
    "fret-prod", 
    "dashboard-uid",
    snapshot_name="Transaction Analysis - Test Data",
    expires_hours=24,
    time_from="now-30d",
    time_to="now"
)

# View snapshot at: snapshot["url"] 
# Inspect actual query results and data
# Verify visualizations match expectations
```

**Benefits:**
- See real data without Druid MCP dependency
- Respects Grafana's variable interpolation
- Uses correct cluster authentication
- Creates shareable dashboard states
- Perfect for debugging data issues

#### 4. Visual Quality Assurance
Use `test_panel_render` for visual validation:

```python
# Render individual panels as PNG images
render_result = test_panel_render(
    "fret-prod", 
    "dashboard-uid", 
    panel_id=15,
    width=1200,
    height=600,
    time_from="now-7d",
    save_to_file="/tmp/revenue_chart.png"
)

# Review rendered image to verify:
# - Data visualization correctness
# - Chart formatting and colors
# - Legends and labels
# - Time series accuracy
```

#### 5. Version Control - Dashboard Comparison
Use `compare_dashboards` for change tracking:

```python
# Compare dashboard versions across environments
comparison = compare_dashboards(
    "fret-dev", 
    "dashboard-uid",
    "dashboard-uid", 
    compare_cluster_b="fret-prod"
)

# Review differences before deployment:
# - Panel changes and additions
# - Query modifications  
# - Variable updates
# - Layout adjustments
```

### Recommended Testing Patterns

#### Before Dashboard Creation:
1. `inspect_dashboard` on similar existing dashboards for reference
2. `validate_dashboard` on template/base dashboards
3. `list_datasources` to verify available data sources

#### During Development:
1. `validate_dashboard` after each major change
2. `snapshot_dashboard` to verify data and queries
3. `test_panel_render` for visual verification of key panels

#### Before Deployment:
1. `validate_dashboard` must pass (status = "PASS")
2. `compare_dashboards` to review all changes
3. `snapshot_dashboard` for final data verification
4. `copy_dashboard` with auto-overwrite for deployment

#### Troubleshooting Data Issues:
1. `inspect_dashboard` to check datasource references
2. `snapshot_dashboard` with different time ranges to isolate issues
3. `test_panel_render` to visualize query results
4. Use browser DevTools on snapshot URL for detailed query inspection

### Integration with CI/CD

These tools can be integrated into automated pipelines:

```bash
# Validation pipeline
python -c "
result = validate_dashboard('fret-dev', 'dashboard-uid')
if result['validation_status'] != 'PASS':
    print('Validation failed:', result['summary'])
    exit(1)
"

# Comparison pipeline  
python -c "
diff = compare_dashboards('fret-dev', 'old-uid', 'new-uid')
if diff['summary']['total_differences'] > 0:
    print('Changes detected:', diff['summary'])
"
```

### Best Practices

1. **Always validate before deployment** - Use `validate_dashboard` to catch issues early
2. **Create snapshots for important states** - Document known-good dashboard configurations  
3. **Compare before overwriting** - Use `compare_dashboards` to understand changes
4. **Test with realistic time ranges** - Use actual date ranges that match production usage
5. **Save rendered panels for documentation** - Keep visual records of dashboard states
6. **Use meaningful snapshot names** - Include purpose, time range, and data context
7. **Snapshot expiration defaults** - Snapshots expire after 24 hours by default to prevent accumulation. Use `expires_hours=0` for permanent snapshots when needed

### Limitations and Workarounds

- **Snapshot API limitations**: Basic Grafana snapshots may not include all data. For comprehensive data snapshots, consider using external tools like `grafana-snapshots-tool`
- **Render API dependencies**: Panel rendering requires Grafana's image renderer to be installed
- **Variable interpolation**: Snapshots show actual interpolated variables, but inspection shows raw variable references
- **Cross-cluster authentication**: Ensure all clusters have proper authentication configured

This comprehensive testing workflow provides the visibility and validation needed for confident dashboard development and deployment while respecting Grafana's architecture and security model.

## Troubleshooting

### Configuration Issues

**"GRAFANA_READ_ACCESS_TAGS must be a subset of GRAFANA_WRITE_ACCESS_TAGS" Error**

This error occurs when read access tags contain tags not present in write access tags.

```bash
# ❌ Invalid configuration (will fail at startup)
export GRAFANA_READ_ACCESS_TAGS="MCP AI_GENERATED CUSTOM"
export GRAFANA_WRITE_ACCESS_TAGS="MCP AI_GENERATED"

# ✅ Valid configurations
export GRAFANA_READ_ACCESS_TAGS=""  # No read restrictions
export GRAFANA_WRITE_ACCESS_TAGS="MCP AI_GENERATED"

export GRAFANA_READ_ACCESS_TAGS="MCP"  # Subset of write tags
export GRAFANA_WRITE_ACCESS_TAGS="MCP AI_GENERATED"

export GRAFANA_READ_ACCESS_TAGS="MCP AI_GENERATED"  # Equal sets
export GRAFANA_WRITE_ACCESS_TAGS="MCP AI_GENERATED"
```

**Solution:**
- Remove extra tags from `GRAFANA_READ_ACCESS_TAGS`, or
- Add missing tags to `GRAFANA_WRITE_ACCESS_TAGS`

**"Dashboard not found" for Recently Created Dashboards**

This typically indicates a tag configuration mismatch where the MCP server created a dashboard but cannot read it back.

**Causes:**
- Modified tag configuration after dashboard creation
- Manual tag removal from dashboards
- Incorrect tag configuration (should be caught by startup validation now)

**Solution:**
- Verify current tag configuration is valid
- Check dashboard tags in Grafana UI match expected security requirements
- Recreate problematic dashboards with current configuration

## Development Principles

- Never commit without asking for permission.
- Never mention yourself, Claude, in git commit messages.