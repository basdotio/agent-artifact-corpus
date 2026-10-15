# Communicating with Microsoft Fabric from Python MCP Server

## Overview
Microsoft Fabric provides unified analytics platform with REST APIs and SQL endpoints. This guide shows how to integrate Fabric into your MCP server for data discovery and analytics.

## Architecture

```mermaid
graph TD
    A[MCP Server] -->|REST API| B[Fabric API<br/>api.fabric.microsoft.com]
    A -->|SQL Connection| C[Lakehouse SQL Endpoint<br/>ODBC Driver]
    
    subgraph "Microsoft Fabric"
        D[Workspaces]
        E[Lakehouses]
        F[Tables & Data]
        G[SQL Analytics Endpoint]
    end
    
    B --> D
    D --> E
    E --> F
    E --> G
    C --> G
    
    subgraph "Authentication"
        H[Service Principal]
        I[Client ID + Secret]
        J[Azure AD Token]
    end
    
    A --> H
    H --> I
    I --> J
    J --> B
    J --> C
```

## Authentication Setup

### Dual Authentication Support
The server supports two authentication modes that are automatically selected based on environment configuration:

#### Interactive Authentication (Default)
- **Device Code Flow**: User-friendly browser-based authentication
- **Power BI Client ID**: Uses well-known Power BI client ID (`ea0616ba-638b-4df5-95b9-636659ae5121`)
- **Token Caching**: Tokens cached in `~/.fabric_mcp_token_cache.json` with automatic refresh
- **Multi-tenant Support**: Works with any Microsoft account using 'common' tenant
- **User Experience**: Auth prompt appears in MCP server output logs with device code and URL

#### Service Principal Authentication
- **Azure AD App Registration**: Create service principal with appropriate permissions
- **Trigger**: Automatically used when `FABRIC_CLIENT_SECRET` environment variable is set
- **Token Acquisition**: Uses MSAL `ConfidentialClientApplication` for client credentials flow
- **Environment Variables**: Requires CLIENT_ID, CLIENT_SECRET, TENANT_ID
- **Authority URL**: Format as `https://login.microsoftonline.com/{TENANT_ID}`

### Key Authentication Points
- **Power BI API Scope**: Use `https://analysis.windows.net/powerbi/api/.default` for Fabric access
- **Fabric Permission**: Requires Power BI API access, not just Azure Resource Manager
- **Token Refresh**: MSAL handles silent token refresh using cached refresh tokens
- **Error Handling**: Handle token acquisition failures gracefully with user-friendly messages
- **Scope Configuration**: Single scope `.default` is sufficient for most Fabric operations

## REST API Integration

### Centralized API Client Architecture
- **Base URL**: All Fabric APIs use `https://api.fabric.microsoft.com/v1` as base
- **Authentication Headers**: Include Bearer token in Authorization header for all requests
- **HTTP Client**: Use async HTTP library (httpx) for non-blocking operations
- **Response Handling**: Parse JSON responses and handle HTTP status codes appropriately
- **Error Management**: Convert HTTP errors into user-friendly error messages

### Common API Endpoints
- **Workspaces**: `/workspaces` - List all accessible workspaces
- **Lakehouses**: `/workspaces/{id}/lakehouses` - List lakehouses in workspace
- **Tables**: Access via SQL endpoint, not REST API
- **Items**: Generic `/workspaces/{id}/items` for broader resource discovery

### API Response Patterns
- **List Responses**: Most list endpoints return `{"value": [array_of_items]}`
- **Item Structure**: Items typically have `id`, `displayName`, and `properties`
- **Properties Object**: Contains service-specific metadata and connection info
- **Error Responses**: Include status code, error message, and request correlation ID

## SQL Endpoint Integration

### Connection Architecture
- **ODBC Driver**: Use "ODBC Driver 17 for SQL Server" (or 18) for lakehouse connections
- **SQL Endpoint**: Extract server address from lakehouse properties via REST API call
- **Database Name**: Use lakehouse `displayName` as database name in connection
- **Authentication**: Access token-based authentication using `attrs_before` parameter
- **Token Format**: Token length (4 bytes, little-endian) + UTF-16-LE encoded token bytes
- **Connection Security**: Enable encryption, disable certificate trust for managed service

### Schema Discovery Approach
- **SQL-Based Discovery**: Use `INFORMATION_SCHEMA.TABLES` for universal lakehouse support
- **Schema-Enabled Support**: SQL approach works with both schema-enabled and schema-less lakehouses
- **Table Listing**: Query `TABLE_SCHEMA`, `TABLE_NAME`, `TABLE_TYPE` from system views
- **Column Details**: Retrieve data types, nullability, precision, and ordinal position from `INFORMATION_SCHEMA.COLUMNS`
- **Simple Queries**: Avoid complex JOINs - use basic SELECT statements for reliability
- **Performance**: Query specific tables rather than entire schema when possible

### Data Sampling Strategy
- **TOP Clause**: Use `SELECT TOP N` syntax for consistent row limiting
- **Table Brackets**: Wrap table names in brackets to handle special characters
- **Result Formatting**: Convert query results to list of dictionaries for JSON serialization
- **Error Handling**: Catch and convert pyodbc errors to user-friendly messages

### SQL Analytics Capabilities
- **Custom Queries**: Allow execution of arbitrary SQL for analytics and reporting
- **Query Validation**: Validate SQL syntax before execution to prevent errors
- **Result Limiting**: Implement row limits to prevent excessive data transfer
- **Performance Monitoring**: Track query execution time and result set sizes

## Integration Workflow

### Progressive Discovery Pattern
1. **Workspaces**: Start by listing all accessible Fabric workspaces
2. **Lakehouses**: Discover lakehouses within selected workspace
3. **Tables**: Query lakehouse for available tables and views
4. **Schema**: Examine table structure and column definitions
5. **Data**: Sample table content and execute analytics queries

## Key Dependencies
- **MCP Framework**: `fastmcp` for Model Context Protocol server implementation
- **Authentication**: `msal` for Azure AD token acquisition (both interactive and service principal)
- **HTTP Client**: `httpx` for async REST API calls
- **Database**: `pyodbc` for SQL connectivity (requires ODBC Driver 17 or 18 for SQL Server)
- **Environment**: `python-dotenv` for configuration management
