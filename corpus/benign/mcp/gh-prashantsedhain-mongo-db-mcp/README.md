# MongoDB MCP Server

A Model Context Protocol (MCP) server for MongoDB that allows querying MongoDB collections through a simple interface for local integrations and command line tools.

## Overview

This project implements an MCP server that connects to MongoDB and provides a `query` tool to retrieve data from collections. It currently only supports read-only transactions. Project includes:

- A MongoDB MCP server that exposes database querying capabilities
- A client application for interacting with the server
- Utilities for MongoDB connection and transaction management

## Prerequisites

- Node.js (v16 or higher)
- npm
- MongoDB database (local or cloud-based)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/mongo-db-mcp.git
   cd mongo-db-mcp
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create a `.env` file in the root directory with your MongoDB connection string:
   ```
   MONGO_CONNECTION_STRING=your_mongodb_connection_string
   ```

## Building the Project

Build the TypeScript code:
```bash
npm run build
```

## Running the client

```bash
node dist/client/client.js dist/index.js
```


