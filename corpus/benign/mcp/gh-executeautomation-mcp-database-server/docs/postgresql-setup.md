# PostgreSQL Setup for MCP Database Server

This document describes how to set up and use the PostgreSQL adapter with the MCP Database Server.

## Prerequisites

1. You need to have PostgreSQL installed and running on your system or on a remote server.
2. Ensure the pg package is installed:

```
npm install pg
npm install @types/pg --save-dev
```

## Running the Server with PostgreSQL

To connect to a PostgreSQL database, use the following command-line arguments:

```bash
# Basic connection
node dist/src/index.js --postgresql --host localhost --database yourdb --user postgres --password yourpassword

# With custom port (default is 5432)
node dist/src/index.js --postgresql --host localhost --database yourdb --user postgres --password yourpassword --port 5433

# With SSL enabled
node dist/src/index.js --postgresql --host localhost --database yourdb --user postgres --password yourpassword --ssl true

# With custom connection timeout (in milliseconds)
node dist/src/index.js --postgresql --host localhost --database yourdb --user postgres --password yourpassword --connection-timeout 60000
```

## Command Line Arguments

- `--postgresql` or `--postgres`: Specifies that you want to connect to a PostgreSQL database.
- `--host`: The hostname or IP address of the PostgreSQL server (required).
- `--database`: The name of the database to connect to (required).
- `--user`: The PostgreSQL user to authenticate as.
- `--password`: The password for the PostgreSQL user.
- `--port`: The port the PostgreSQL server is listening on (default: 5432).
- `--ssl`: Whether to use SSL for the connection (true/false).
- `--connection-timeout`: The connection timeout in milliseconds (default: 30000).

## Usage from MCP Client

The MCP client can interact with a PostgreSQL database using the same tools that are available for SQLite and SQL Server. The server automatically translates the generic SQL queries to PostgreSQL-specific formats.

## Supported Features

- Full SQL query support for SELECT, INSERT, UPDATE, and DELETE operations.
- Table management (CREATE TABLE, ALTER TABLE, DROP TABLE).
- Schema introspection.
- Connection pooling for efficient database access.
- SSL support for secure connections.

## Examples

### Create a Table

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Insert Data

```sql
INSERT INTO users (username, email) VALUES ('johndoe', 'john@example.com');
```

### Query Data

```sql
SELECT * FROM users WHERE username = 'johndoe';
```

## Limitations

- For the `run` method with INSERT statements, the adapter attempts to retrieve the last inserted ID by adding a RETURNING clause. This assumes your tables have an 'id' column.
- Complex stored procedures or PostgreSQL-specific features might require custom implementation.

## Troubleshooting

### Connection Issues

If you're having trouble connecting to your PostgreSQL database:

1. Verify that PostgreSQL is running: `pg_isready -h localhost -p 5432`
2. Check that your credentials are correct.
3. Ensure that the database exists and the user has appropriate permissions.
4. Check firewall settings if connecting to a remote database.

### Query Errors

If your queries are failing:

1. Check the syntax against PostgreSQL's SQL dialect.
2. Verify table and column names.
3. Check that the user has proper permissions for the operations.

## Performance Considerations

For optimal performance:

1. Use parameterized queries to prevent SQL injection and improve query caching.
2. Consider indexing frequently queried columns.
3. For large result sets, use LIMIT and OFFSET for pagination. 