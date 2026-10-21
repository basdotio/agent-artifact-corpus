#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListResourcesRequestSchema,
  ListToolsRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import sqlite3 from "sqlite3";

// Configure the server
const server = new Server(
  {
    name: "executeautomation/database-server",
    version: "1.1.0",
  },
  {
    capabilities: {
      resources: {},
      tools: {},
    },
  },
);

// Parse command line arguments
const args = process.argv.slice(2);
if (args.length === 0) {
  console.error("Please provide a database file path as a command-line argument");
  process.exit(1);
}

const databasePath = args[0];

// Create a resource base URL for SQLite
const resourceBaseUrl = new URL(`sqlite:///${databasePath}`);
const SCHEMA_PATH = "schema";

// Initialize SQLite database connection
let db: sqlite3.Database;

function initDatabase(): Promise<void> {
  return new Promise((resolve, reject) => {
    db = new sqlite3.Database(databasePath, (err) => {
      if (err) {
        reject(err);
      } else {
        resolve();
      }
    });
  });
}

// Helper function to run a query and get all results
function dbAll(query: string, params: any[] = []): Promise<any[]> {
  return new Promise((resolve, reject) => {
    db.all(query, params, (err: Error | null, rows: any[]) => {
      if (err) {
        reject(err);
      } else {
        resolve(rows);
      }
    });
  });
}

// Helper function to run a query that doesn't return results
function dbRun(query: string, params: any[] = []): Promise<{ changes: number, lastID: number }> {
  return new Promise((resolve, reject) => {
    db.run(query, params, function(this: sqlite3.RunResult, err: Error | null) {
      if (err) {
        reject(err);
      } else {
        resolve({ changes: this.changes, lastID: this.lastID });
      }
    });
  });
}

// Helper function to run multiple statements
function dbExec(query: string): Promise<void> {
  return new Promise((resolve, reject) => {
    db.exec(query, (err: Error | null) => {
      if (err) {
        reject(err);
      } else {
        resolve();
      }
    });
  });
}

// List all available database resources (tables)
server.setRequestHandler(ListResourcesRequestSchema, async () => {
  // Query to get all table names
  const result = await dbAll(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
  );
  
  return {
    resources: result.map((row) => ({
      uri: new URL(`${row.name}/${SCHEMA_PATH}`, resourceBaseUrl).href,
      mimeType: "application/json",
      name: `"${row.name}" database schema`,
    })),
  };
});

// Get schema information for a specific table
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const resourceUrl = new URL(request.params.uri);

  const pathComponents = resourceUrl.pathname.split("/");
  const schema = pathComponents.pop();
  const tableName = pathComponents.pop();

  if (schema !== SCHEMA_PATH) {
    throw new Error("Invalid resource URI");
  }

  // Query to get column information for a table
  const result = await dbAll(`PRAGMA table_info("${tableName}")`);

  return {
    contents: [
      {
        uri: request.params.uri,
        mimeType: "application/json",
        text: JSON.stringify(result.map((column) => ({
          column_name: column.name,
          data_type: column.type
        })), null, 2),
      },
    ],
  };
});

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "read_query",
        description: "Execute SELECT queries to read data from the database",
        inputSchema: {
          type: "object",
          properties: {
            query: { type: "string" },
          },
          required: ["query"],
        },
      },
      {
        name: "write_query",
        description: "Execute INSERT, UPDATE, or DELETE queries",
        inputSchema: {
          type: "object",
          properties: {
            query: { type: "string" },
          },
          required: ["query"],
        },
      },
      {
        name: "create_table",
        description: "Create new tables in the database",
        inputSchema: {
          type: "object",
          properties: {
            query: { type: "string" },
          },
          required: ["query"],
        },
      },
      {
        name: "alter_table",
        description: "Modify existing table schema (add columns, rename tables, etc.)",
        inputSchema: {
          type: "object",
          properties: {
            query: { type: "string" },
          },
          required: ["query"],
        },
      },
      {
        name: "drop_table",
        description: "Remove a table from the database with safety confirmation",
        inputSchema: {
          type: "object",
          properties: {
            table_name: { type: "string" },
            confirm: { type: "boolean" },
          },
          required: ["table_name", "confirm"],
        },
      },
      {
        name: "export_query",
        description: "Export query results to various formats (CSV, JSON)",
        inputSchema: {
          type: "object",
          properties: {
            query: { type: "string" },
            format: { type: "string", enum: ["csv", "json"] },
          },
          required: ["query", "format"],
        },
      },
      {
        name: "list_tables",
        description: "Get a list of all tables in the database",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "describe_table",
        description: "View schema information for a specific table",
        inputSchema: {
          type: "object",
          properties: {
            table_name: { type: "string" },
          },
          required: ["table_name"],
        },
      },
      {
        name: "append_insight",
        description: "Add a business insight to the memo",
        inputSchema: {
          type: "object",
          properties: {
            insight: { type: "string" },
          },
          required: ["insight"],
        },
      },
    ],
  };
});

// Helper function to convert data to CSV format
function convertToCSV(data: any[]): string {
  if (data.length === 0) return '';
  
  // Get headers
  const headers = Object.keys(data[0]);
  
  // Create CSV header row
  let csv = headers.join(',') + '\n';
  
  // Add data rows
  data.forEach(row => {
    const values = headers.map(header => {
      const val = row[header];
      // Handle strings with commas, quotes, etc.
      if (typeof val === 'string') {
        return `"${val.replace(/"/g, '""')}"`;
      }
      // Use empty string for null/undefined
      return val === null || val === undefined ? '' : val;
    });
    csv += values.join(',') + '\n';
  });
  
  return csv;
}

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  switch (request.params.name) {
    case "read_query": {
      const query = request.params.arguments?.query as string;
      
      if (!query.trim().toLowerCase().startsWith("select")) {
        throw new Error("Only SELECT queries are allowed with read_query");
      }

      try {
        const result = await dbAll(query);
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
          isError: false,
        };
      } catch (error: any) {
        throw new Error(`SQL Error: ${error.message}`);
      }
    }

    case "write_query": {
      const query = request.params.arguments?.query as string;
      const lowerQuery = query.trim().toLowerCase();
      
      if (lowerQuery.startsWith("select")) {
        throw new Error("Use read_query for SELECT operations");
      }
      
      if (!(lowerQuery.startsWith("insert") || lowerQuery.startsWith("update") || lowerQuery.startsWith("delete"))) {
        throw new Error("Only INSERT, UPDATE, or DELETE operations are allowed with write_query");
      }

      try {
        const result = await dbRun(query);
        return {
          content: [{ 
            type: "text", 
            text: JSON.stringify({ affected_rows: result.changes }, null, 2) 
          }],
          isError: false,
        };
      } catch (error: any) {
        throw new Error(`SQL Error: ${error.message}`);
      }
    }

    case "create_table": {
      const query = request.params.arguments?.query as string;
      
      if (!query.trim().toLowerCase().startsWith("create table")) {
        throw new Error("Only CREATE TABLE statements are allowed");
      }

      try {
        await dbExec(query);
        return {
          content: [{ 
            type: "text", 
            text: JSON.stringify({ success: true, message: "Table created successfully" }, null, 2) 
          }],
          isError: false,
        };
      } catch (error: any) {
        throw new Error(`SQL Error: ${error.message}`);
      }
    }

    case "alter_table": {
      const query = request.params.arguments?.query as string;
      
      if (!query.trim().toLowerCase().startsWith("alter table")) {
        throw new Error("Only ALTER TABLE statements are allowed");
      }

      try {
        await dbExec(query);
        return {
          content: [{ 
            type: "text", 
            text: JSON.stringify({ success: true, message: "Table altered successfully" }, null, 2) 
          }],
          isError: false,
        };
      } catch (error: any) {
        throw new Error(`SQL Error: ${error.message}`);
      }
    }

    case "drop_table": {
      const tableName = request.params.arguments?.table_name as string;
      const confirm = request.params.arguments?.confirm as boolean;
      
      if (!tableName) {
        throw new Error("Table name is required");
      }
      
      if (!confirm) {
        return {
          content: [{ 
            type: "text", 
            text: JSON.stringify({ 
              success: false, 
              message: "Safety confirmation required. Set confirm=true to proceed with dropping the table." 
            }, null, 2) 
          }],
          isError: false,
        };
      }

      try {
        // Check if table exists
        const tableExists = await dbAll(
          "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
          [tableName]
        );
        
        if (tableExists.length === 0) {
          throw new Error(`Table '${tableName}' does not exist`);
        }
        
        // Drop the table
        await dbExec(`DROP TABLE "${tableName}"`);
        
        return {
          content: [{ 
            type: "text", 
            text: JSON.stringify({ success: true, message: `Table '${tableName}' dropped successfully` }, null, 2) 
          }],
          isError: false,
        };
      } catch (error: any) {
        throw new Error(`Error dropping table: ${error.message}`);
      }
    }

    case "export_query": {
      const query = request.params.arguments?.query as string;
      const format = request.params.arguments?.format as string;
      
      if (!query.trim().toLowerCase().startsWith("select")) {
        throw new Error("Only SELECT queries are allowed with export_query");
      }

      try {
        const result = await dbAll(query);
        
        if (format === "csv") {
          const csvData = convertToCSV(result);
          return {
            content: [{ 
              type: "text", 
              text: csvData
            }],
            isError: false,
          };
        } else if (format === "json") {
          return {
            content: [{ 
              type: "text", 
              text: JSON.stringify(result, null, 2) 
            }],
            isError: false,
          };
        } else {
          throw new Error("Unsupported export format. Use 'csv' or 'json'");
        }
      } catch (error: any) {
        throw new Error(`Export Error: ${error.message}`);
      }
    }

    case "list_tables": {
      try {
        const tables = await dbAll(
          "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        );
        return {
          content: [{ 
            type: "text", 
            text: JSON.stringify(tables.map((t) => t.name), null, 2) 
          }],
          isError: false,
        };
      } catch (error: any) {
        throw new Error(`Error listing tables: ${error.message}`);
      }
    }

    case "describe_table": {
      const tableName = request.params.arguments?.table_name as string;
      
      if (!tableName) {
        throw new Error("Table name is required");
      }

      try {
        // Check if table exists
        const tableExists = await dbAll(
          "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
          [tableName]
        );
        
        if (tableExists.length === 0) {
          throw new Error(`Table '${tableName}' does not exist`);
        }
        
        const columns = await dbAll(`PRAGMA table_info("${tableName}")`);
        return {
          content: [{ 
            type: "text", 
            text: JSON.stringify(columns.map((col) => ({
              name: col.name,
              type: col.type,
              notnull: !!col.notnull,
              default_value: col.dflt_value,
              primary_key: !!col.pk
            })), null, 2) 
          }],
          isError: false,
        };
      } catch (error: any) {
        throw new Error(`Error describing table: ${error.message}`);
      }
    }
    
    case "append_insight": {
      const insight = request.params.arguments?.insight as string;
      
      if (!insight) {
        throw new Error("Insight text is required");
      }

      try {
        // Create insights table if it doesn't exist
        await dbExec(`
          CREATE TABLE IF NOT EXISTS mcp_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insight TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
          )
        `);
        
        // Insert the insight
        await dbRun(
          "INSERT INTO mcp_insights (insight) VALUES (?)",
          [insight]
        );
        
        return {
          content: [{ 
            type: "text", 
            text: JSON.stringify({ success: true, message: "Insight added" }, null, 2) 
          }],
          isError: false,
        };
      } catch (error: any) {
        throw new Error(`Error adding insight: ${error.message}`);
      }
    }

    default:
      throw new Error(`Unknown tool: ${request.params.name}`);
  }
});

async function runServer() {
  try {
    await initDatabase();
    const transport = new StdioServerTransport();
    await server.connect(transport);
  } catch (error) {
    console.error("Failed to initialize:", error);
    process.exit(1);
  }
}

runServer().catch(console.error);