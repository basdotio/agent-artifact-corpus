---
name: sql-server
description: Microsoft SQL Server database management for day-to-day operations. Use when the user needs to run SQL queries, inspect schemas, manage tables, monitor performance, handle backups, or administer a SQL Server database via sqlcmd or a connection string.
---

# SQL Server

Microsoft SQL Server management — queries, schema inspection, inserts, updates, and performance monitoring.

## Setup

```bash
export SQLCMDSERVER="localhost"
export SQLCMDUSER="sa"
export SQLCMDPASSWORD="yourpassword"   # Avoids passwords in shell history
export SQLCMDDBNAME="mydb"
```

Connect using `sqlcmd`:

```bash
sqlcmd -S "$SQLCMDSERVER" -U "$SQLCMDUSER" -P "$SQLCMDPASSWORD" -d "$SQLCMDDBNAME"
# or inline:
sqlcmd -S localhost -U sa -P pass -d mydb
# or with explicit port:
sqlcmd -S "tcp:myserver.database.windows.net,1433" -U user -P pass -d mydb
```

Run a single query without entering the interactive shell:

```bash
sqlcmd -S localhost -U sa -P pass -d mydb -Q "SELECT TOP 10 * FROM Orders"
```

Run a SQL script file:

```bash
sqlcmd -S localhost -U sa -P pass -d mydb -i script.sql
```

## Installation

```bash
# Linux (Debian/Ubuntu) — mssql-tools
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list \
  | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y mssql-tools unixodbc-dev
echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bashrc
source ~/.bashrc

# mssql-cli (interactive alternative with autocomplete)
pip install mssql-cli
```

## Essential sqlcmd Options

| Option | Description |
|---|---|
| `-S` | Server (`host` or `host,port` or `tcp:host,port`) |
| `-U` | Username |
| `-P` | Password (prefer `SQLCMDPASSWORD` env var) |
| `-d` | Database |
| `-E` | Use Windows integrated authentication |
| `-Q` | Run query and exit |
| `-q` | Run query, stay in interactive mode |
| `-i` | Input SQL file |
| `-o` | Output file |
| `-h -1` | Remove column headers |
| `-s ","` | Set column separator (e.g. for CSV output) |
| `-W` | Remove trailing spaces from columns |

## Common Operations

### Query

```sql
SELECT TOP 10 * FROM Users;
SELECT column1, column2 FROM TableName WHERE condition ORDER BY column1 DESC;
```

### Insert / Update / Delete

```sql
INSERT INTO Users (Name, Email) VALUES ('Alice', 'alice@example.com');
UPDATE Users SET Email = 'new@example.com' WHERE Id = 1;
DELETE FROM Users WHERE Id = 1;
```

### Schema Inspection

```sql
-- List all tables in current database
SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_SCHEMA, TABLE_NAME;

-- Describe a table (columns, types, nullability)
SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'Orders'
ORDER BY ORDINAL_POSITION;

-- List indexes on a table
SELECT i.name AS index_name, i.type_desc, c.name AS column_name
FROM sys.indexes i
JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE OBJECT_NAME(i.object_id) = 'Orders';

-- List foreign keys
SELECT
  fk.name AS fk_name,
  OBJECT_NAME(fk.parent_object_id) AS parent_table,
  c.name AS parent_column,
  OBJECT_NAME(fk.referenced_object_id) AS ref_table,
  rc.name AS ref_column
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
JOIN sys.columns c ON fkc.parent_object_id = c.object_id AND fkc.parent_column_id = c.column_id
JOIN sys.columns rc ON fkc.referenced_object_id = rc.object_id AND fkc.referenced_column_id = rc.column_id;
```

### Schema Changes

```sql
-- Create table
CREATE TABLE Orders (
  Id        INT IDENTITY(1,1) PRIMARY KEY,
  UserId    INT NOT NULL REFERENCES Users(Id),
  Total     DECIMAL(10,2),
  CreatedAt DATETIME2 DEFAULT SYSDATETIME()
);

-- Add / drop column
ALTER TABLE Orders ADD Status NVARCHAR(50) DEFAULT 'pending';
ALTER TABLE Orders DROP COLUMN Status;

-- Create index
CREATE INDEX IX_Orders_UserId ON Orders(UserId);
-- Non-clustered covering index:
CREATE NONCLUSTERED INDEX IX_Orders_Status ON Orders(Status) INCLUDE (Total, CreatedAt);
```

### Transactions

```sql
BEGIN TRANSACTION;
  UPDATE Accounts SET Balance = Balance - 100 WHERE Id = 1;
  UPDATE Accounts SET Balance = Balance + 100 WHERE Id = 2;
COMMIT;
-- or ROLLBACK; to undo
```

## Performance & Monitoring

```sql
-- Currently running queries
SELECT
  r.session_id,
  r.status,
  r.cpu_time,
  r.total_elapsed_time,
  r.logical_reads,
  t.text AS query_text
FROM sys.dm_exec_requests r
CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) t
WHERE r.session_id != @@SPID;

-- Top CPU-consuming queries (from plan cache)
SELECT TOP 10
  qs.total_worker_time / qs.execution_count AS avg_cpu_time,
  qs.execution_count,
  SUBSTRING(st.text, (qs.statement_start_offset/2)+1,
    ((CASE qs.statement_end_offset WHEN -1 THEN DATALENGTH(st.text)
      ELSE qs.statement_end_offset END - qs.statement_start_offset)/2)+1) AS query_text
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
ORDER BY avg_cpu_time DESC;

-- Active connections
SELECT session_id, login_name, status, host_name, program_name, database_id, cpu_time
FROM sys.dm_exec_sessions
WHERE is_user_process = 1;

-- Table sizes
SELECT
  t.NAME AS table_name,
  p.rows AS row_count,
  SUM(a.total_pages) * 8 AS total_kb,
  SUM(a.used_pages) * 8 AS used_kb
FROM sys.tables t
JOIN sys.indexes i ON t.object_id = i.object_id
JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
JOIN sys.allocation_units a ON p.partition_id = a.container_id
GROUP BY t.NAME, p.rows
ORDER BY total_kb DESC;

-- Explain query plan
SET STATISTICS IO ON;
SET STATISTICS TIME ON;
SELECT * FROM Orders WHERE UserId = 42;

-- Or view estimated plan without running (SSMS/Azure Data Studio syntax)
-- Prefix query with: SET SHOWPLAN_TEXT ON; GO
```

## Backup & Restore

```bash
# Backup (T-SQL via sqlcmd)
sqlcmd -S localhost -U sa -P pass -Q \
  "BACKUP DATABASE [mydb] TO DISK = N'/var/opt/mssql/backup/mydb.bak' WITH NOFORMAT, INIT, STATS=10"

# Restore
sqlcmd -S localhost -U sa -P pass -Q \
  "RESTORE DATABASE [mydb] FROM DISK = N'/var/opt/mssql/backup/mydb.bak' WITH REPLACE, STATS=10"
```

## Bulk Import/Export (BCP)

```bash
# Export table to CSV
bcp mydb.dbo.Orders out orders.csv -S localhost -U sa -P pass -c -t ','

# Import CSV into table
bcp mydb.dbo.Orders in orders.csv -S localhost -U sa -P pass -c -t ','

# Export query result to CSV
bcp "SELECT * FROM mydb.dbo.Orders WHERE Status = 'pending'" queryout pending.csv \
  -S localhost -U sa -P pass -c -t ','
```

## Safety Rules

1. **Always confirm** before running `DELETE`, `DROP`, or `TRUNCATE`
2. **Always backup** before schema migrations
3. **Use transactions** for multi-step data changes
4. Use `SET STATISTICS IO ON` / execution plans to preview query cost before running on large tables
5. Prefer targeted indexes over broad ones — over-indexing slows writes
6. Use `SQLCMDPASSWORD` environment variable instead of `-P` flag to keep passwords out of shell history

## Reference

Full `sqlcmd` documentation: <https://learn.microsoft.com/en-us/sql/tools/sqlcmd/sqlcmd-utility>
