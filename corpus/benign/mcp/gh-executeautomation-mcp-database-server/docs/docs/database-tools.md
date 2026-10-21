# Database Tools Reference

The MCP Database Server provides a set of tools that Claude can use to interact with your databases. This page describes each tool, its parameters, and how to use it effectively.

## Available Tools

| Tool | Description | Required Parameters |
|------|-------------|---------------------|
| `read_query` | Execute SELECT queries to read data | `query`: SQL SELECT statement |
| `write_query` | Execute INSERT, UPDATE, or DELETE queries | `query`: SQL modification statement |
| `create_table` | Create new tables in the database | `query`: CREATE TABLE statement |
| `alter_table` | Modify existing table schema | `query`: ALTER TABLE statement |
| `drop_table` | Remove a table from the database | `table_name`: Name of table<br/>`confirm`: Safety flag (must be true) |
| `list_tables` | Get a list of all tables | None |
| `describe_table` | View schema information for a table | `table_name`: Name of table |
| `export_query` | Export query results as CSV/JSON | `query`: SQL SELECT statement<br/>`format`: "csv" or "json" |
| `append_insight` | Add a business insight to memo | `insight`: Text of insight |
| `list_insights` | List all business insights | None |

## Tool Usage Examples

### Reading Data

To retrieve data from the database:

```
What customers have spent more than $1000 in the past month?
```

Claude will use the `read_query` tool with an appropriate SQL query.

### Writing Data

To insert, update, or delete data:

```
Add a new product called "Deluxe Widget" with price $29.99 to the Products table.
```

Claude will use the `write_query` tool to perform the INSERT operation.

### Schema Management

To create or modify tables:

```
Create a new table called "CustomerFeedback" with columns for customer ID, rating (1-5), and comment text.
```

Claude will use the `create_table` tool to define the new table.

### Exporting Data

To export query results:

```
Export all sales from the last quarter as CSV.
```

Claude will use the `export_query` tool with the format parameter set to "csv".

### Working with Insights

Claude can track important observations during your database analysis:

```
Add an insight that "Sales are 15% higher on weekends compared to weekdays"
```

Claude will use the `append_insight` tool to record this information.

## Best Practices

1. **Be specific in your requests**: Provide clear details about what data you want to retrieve or modify.

2. **Use natural language**: Ask questions as you would to a human analyst. Claude will convert your request into appropriate SQL.

3. **Review before committing**: For data modifications, always review what Claude proposes before confirming.

4. **Consider data volume**: For large tables, use filtering to limit result sets.

5. **Think about performance**: Complex queries on large tables might take time to execute.

## Limitations

1. The server does not support certain database-specific features like stored procedures or triggers.

2. For security reasons, file operations and system commands are not available.

3. There may be slight syntax differences between SQLite, SQL Server, and PostgreSQL. Claude will attempt to adapt queries accordingly.

4. Large result sets might be truncated to prevent memory issues. 