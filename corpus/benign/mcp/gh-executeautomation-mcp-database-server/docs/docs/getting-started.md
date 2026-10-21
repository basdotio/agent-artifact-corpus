# Getting Started

This guide will help you get up and running with the MCP Database Server and Claude.

## Installation

Install the MCP Database Server using NPM:

```bash
npm install -g @executeautomation/database-server
```

## Setup Steps

1. **Choose your database type**: The MCP Database Server supports SQLite, SQL Server, and PostgreSQL
2. **Configure Claude Desktop**: Update your Claude configuration file to connect to your database
3. **Restart Claude Desktop**: Apply the configuration changes
4. **Start a conversation**: Begin interacting with your database through Claude

## Example Configurations

Below are sample configurations for each supported database type:

### SQLite

```json
{
  "mcpServers": {
    "sqlite": {
      "command": "npx",
      "args": [
        "-y",
        "@executeautomation/database-server",
        "/path/to/your/database.db"
      ]
    }
  }
}
```

### SQL Server

```json
{
  "mcpServers": {
    "sqlserver": {
      "command": "npx",
      "args": [
        "-y",
        "@executeautomation/database-server",
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

### PostgreSQL

```json
{
  "mcpServers": {
    "postgresql": {
      "command": "npx",
      "args": [
        "-y",
        "@executeautomation/database-server",
        "--postgresql",
        "--host", "your-host-name",
        "--database", "your-database-name",
        "--user", "your-username",
        "--password", "your-password"
      ]
    }
  }
}
```

## Your First Conversation

Once your MCP Database Server is set up, you can start interacting with your database through Claude. Here's an example conversation:

**You**: "What tables are in the database?"

**Claude**: *Uses the list_tables tool and displays the tables in your database*

**You**: "Show me the structure of the Customers table"

**Claude**: *Uses the describe_table tool to show the schema of the Customers table*

**You**: "Find all customers who placed orders in the last month"

**Claude**: *Uses the read_query tool to execute a SQL query and display the results*

## Workflow Patterns

The typical workflow for database interaction consists of:

1. **Exploration**: Discovering what tables and data are available
2. **Analysis**: Running queries to extract insights from the data
3. **Modification**: Making changes to the data or schema when needed
4. **Iteration**: Refining queries based on initial results

## Next Steps

Once you're comfortable with the basics, explore the following topics:

- See [Database Tools Reference](database-tools.md) for details on all available tools
- Visit [Usage Examples](usage-examples.md) for more complex scenarios
- Check the setup guides for your specific database:
  - [SQLite Setup](sqlite-setup.md)
  - [SQL Server Setup](sql-server-setup.md)
  - [PostgreSQL Setup](postgresql-setup.md) 