# ASKG MCP Server

This directory contains the Model Context Protocol (MCP) server implementation for the ASKG (Agent-Server Knowledge Graph) project. The MCP server provides semantic search capabilities for MCP servers stored in the Neo4j knowledge graph database.

## Overview

The ASKG MCP server allows you to search for MCP servers using natural language prompts. It performs semantic search across:

- Server names and descriptions
- Server categories (database, file system, API integration, etc.)
- Server operations (read, write, execute, query, etc.)
- Server metadata (author, language, popularity, etc.)

## Features

- **Semantic Search**: Multi-faceted search using text, categories, and operations
- **Confidence Scoring**: Results are ranked by relevance score
- **Flexible Queries**: Natural language prompts for finding servers
- **Rich Metadata**: Returns comprehensive server information
- **MCP Protocol Compliant**: Follows the official MCP specification

## Installation

1. Install the MCP server dependencies:
   ```bash
   cd mcp
   pip install -r requirements.txt
   ```

2. Ensure you have access to a Neo4j database with ASKG data loaded.

3. Configure the database connection in `.config.yaml` (in the parent directory).

## Usage

### Running the MCP Server

#### Using the Official MCP Library

```bash
# Run the MCP server using stdio (for MCP clients)
python mcp_server.py --config ../.config.yaml --instance local
```

#### Using the Simple HTTP Server

```bash
# Run the simple HTTP server for testing
python server.py --config ../.config.yaml --instance local --port 8200
```

### Using the Client Example

```bash
# Run example searches
python client_example.py --mode example

# Run interactive search
python client_example.py --mode interactive

# Test database connection
python client_example.py --mode test
```

### Example Search Queries

The MCP server understands natural language queries like:

- "Find database servers for SQL operations"
- "Show me file system servers for reading and writing files"
- "I need API integration servers for REST APIs"
- "Find AI and machine learning servers"
- "Show me development tools and utilities"
- "I want servers for data processing and ETL"
- "Find authentication and security servers"
- "Show me monitoring and logging servers"

## API Reference

### ServerSearchRequest

```python
class ServerSearchRequest(BaseModel):
    prompt: str                    # Search prompt describing desired MCP servers
    limit: int = 10               # Maximum number of servers to return
    min_confidence: float = 0.5   # Minimum confidence score for results
```

### ServerSearchResult

```python
class ServerSearchResult(BaseModel):
    servers: List[MCPServer]      # List of matching MCP servers
    total_found: int              # Total number of servers found
    search_metadata: Dict[str, Any] # Search metadata and terms
```

### MCPServer

The returned servers include comprehensive metadata:

- Basic info: name, description, version, author
- Technical details: language, installation, capabilities
- Categorization: categories, operations, data types
- Registry info: source, popularity, last updated
- Tools, resources, and prompts exposed by the server

## Search Algorithm

The semantic search uses a multi-faceted approach:

1. **Text Relevance**: Matches against server names and descriptions
2. **Category Matching**: Identifies relevant server categories from the prompt
3. **Operation Matching**: Identifies relevant operations from the prompt
4. **Popularity Bonus**: Considers server popularity in ranking
5. **Combined Scoring**: Weights and combines all factors for final ranking

### Scoring Weights

- Text match in name: 3.0 points
- Text match in description: 2.0 points
- Category match: 2.0 points per matching category
- Operation match: 1.5 points per matching operation
- Popularity bonus: 0.1 × popularity_score

## Configuration

The MCP server uses the same configuration as the main ASKG project:

```yaml
neo4j:
  local:
    uri: "bolt://localhost:7687"
    user: "neo4j"
    password: "password"
  remote:
    uri: "neo4j+s://your-instance.neo4j.io"
    user: "neo4j"
    password: "your-password"
```

## Integration with MCP Clients

### Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "askg": {
      "command": "python",
      "args": ["/path/to/askg/mcp/mcp_server.py", "--config", "/path/to/askg/.config.yaml"],
      "env": {}
    }
  }
}
```

### Other MCP Clients

The server follows the standard MCP protocol and can be integrated with any MCP-compatible client.

## Development

### Adding New Search Features

1. Extend the `_extract_search_terms` method to recognize new patterns
2. Add new scoring factors in `_build_search_query`
3. Update the search metadata to include new information

### Testing

```bash
# Run tests
pytest tests/

# Test specific functionality
python client_example.py --mode test
```

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Troubleshooting

### Connection Issues

- Verify Neo4j is running and accessible
- Check credentials in `.config.yaml`
- Ensure the database contains ASKG data

### No Results

- Try lowering the `min_confidence` threshold
- Use more general search terms
- Check if the database has been populated with server data

### Import Errors

- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that the parent `src/` directory is accessible
- Verify Python path includes the project root

## Contributing

1. Follow the existing code style and patterns
2. Add tests for new functionality
3. Update documentation for new features
4. Ensure MCP protocol compliance

## License

This project is part of ASKG and follows the same license terms. 