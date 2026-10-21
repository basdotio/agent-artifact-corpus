# SQL Server Setup Guide

This guide provides instructions for setting up and using the SQL Server adapter with the MCP Database Server.

## Prerequisites

1. Access to a SQL Server instance (2012 or later)
2. Node.js 18 or later
3. Required permissions to connect to the SQL Server database

## Installation

1. Follow the main installation steps in the README.md file
2. Ensure the mssql package is installed:
```bash
npm install mssql
npm install @types/mssql --save-dev
```

## Authentication Options

The SQL Server adapter supports multiple authentication methods:

### SQL Server Authentication

Use the `--user` and `--password` parameters to authenticate with SQL Server credentials:

```bash
node dist/src/index.js --sqlserver --server myserver --database mydatabase --user myuser --password mypassword
```

### Windows Authentication

Omit the `--user` and `--password` parameters to use Windows Authentication (trusted connection):

```bash
node dist/src/index.js --sqlserver --server myserver --database mydatabase
```

### Azure Active Directory

For Azure SQL Database with Azure AD authentication, you'll need to set up connection options:

```json
{
  "mcpServers": {
    "sqlserver": {
      "command": "node",
      "args": [
        "/path/to/mcp-database-server/dist/src/index.js",
        "--sqlserver",
        "--server", "myserver.database.windows.net",
        "--database", "mydatabase",
        "--user", "myuser@mydomain.com",
        "--password", "mypassword"
      ]
    }
  }
}
```

## Configuring Claude

Update your Claude configuration file to add SQL Server support:

```json
{
  "mcpServers": {
    "sqlserver": {
      "command": "node",
      "args": [
        "/path/to/mcp-database-server/dist/src/index.js",
        "--sqlserver",
        "--server", "your-server-name",
        "--database", "your-database-name",
        "--user", "your-username",
        "--password", "your-password"
      ]
    }
  }
}
```

For local SQL Server with Windows Authentication:

```json
{
  "mcpServers": {
    "sqlserver": {
      "command": "node",
      "args": [
        "/path/to/mcp-database-server/dist/src/index.js",
        "--sqlserver",
        "--server", "localhost\\SQLEXPRESS",
        "--database", "your-database-name"
      ]
    }
  }
}
```

## Connection Options

Additional connection options include:

- `--port`: Specify a non-default port (default is 1433)
- Add `--trustServerCertificate true` if you're connecting to a development/test server with a self-signed certificate

## Troubleshooting

### Common Connection Issues

1. **Login failed for user**
   - Verify username and password
   - Check if the SQL Server account is enabled and not locked

2. **Cannot connect to server**
   - Ensure SQL Server is running
   - Check firewall settings
   - Verify server name is correct (including instance name if applicable)

3. **SSL errors**
   - Add `--trustServerCertificate true` for development environments

### Verifying Connection

You can test your SQL Server connection using the standard SQL Server tools:

1. Using SQL Server Management Studio (SSMS)
2. Using the `sqlcmd` utility:
   ```
   sqlcmd -S server_name -d database_name -U username -P password
   ```

## SQL Syntax Differences

Note that there may be syntax differences between SQLite and SQL Server. Here are some common differences:

1. **String concatenation**
   - SQLite: `||`
   - SQL Server: `+`

2. **Limit/Offset**
   - SQLite: `LIMIT x OFFSET y`
   - SQL Server: `OFFSET y ROWS FETCH NEXT x ROWS ONLY`

3. **Date formatting**
   - SQLite: `strftime()`
   - SQL Server: `FORMAT()` or `CONVERT()`

4. **Auto-increment columns**
   - SQLite: `INTEGER PRIMARY KEY AUTOINCREMENT`
   - SQL Server: `INT IDENTITY(1,1)`

When using Claude, be aware of these syntax differences when crafting SQL queries. 