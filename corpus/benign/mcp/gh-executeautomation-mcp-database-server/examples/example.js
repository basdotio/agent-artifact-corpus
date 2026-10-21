// Example of using the SQLite MCP Server

// First, start the server with a SQLite database file:
// npx @modelcontextprotocol/server-sqlite ./example.db

// Then, use the Claude Desktop app with the following config:
/*
{
  "mcpServers": {
    "sqlite": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-sqlite",
        "./example.db"
      ]
    }
  }
}
*/

// Example prompts to use with Claude:

/*
1. Create a table:
   "Create a 'users' table with columns for id, name, email, and created_at"

2. Insert data:
   "Insert a few sample users into the users table"

3. Query data:
   "Show me all users in the database"

4. Describe the schema:
   "What tables exist in the database and what are their structures?"

5. Add an insight:
   "Analyze the user data and add an insight about the user distribution"
*/

// SQLite setup
// 1. Create table example
/*
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
*/

// 2. Insert data example
/*
INSERT INTO users (name, email) VALUES 
('John Doe', 'john@example.com'),
('Jane Smith', 'jane@example.com'),
('Bob Johnson', 'bob@example.com')
*/

// 3. Query example
/*
SELECT * FROM users
*/ 