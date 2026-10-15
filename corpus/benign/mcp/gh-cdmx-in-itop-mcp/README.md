# iTop MCP Server

A Model Context Protocol (MCP) server for integrating with iTop ITSM (IT Service Management) systems. This server provides AI assistants with the ability to interact with iTop through its REST API, enabling operations like ticket management, CI (Configuration Item) management, and more.

## 🚀 Features

The iTop MCP server provides the following tools:

**🧠 Smart Query Processor V2 (New Enhanced Version):**
- **smart_query_v2**: Revolutionary natural language query processor with class-specific intelligence
  - **Automatic Class Detection**: Intelligently detects target iTop class from natural language
  - **12+ Specialized Handlers**: Dedicated processors for UserRequest, Ticket, Change, Incident, Problem, Server, PC, VirtualMachine, NetworkDevice, Person, Team, Organization
  - **Advanced Query Features**: Grouping, filtering, SLA analysis, deadline tracking, and statistical breakdowns
  - **Smart Field Mapping**: User-friendly field aliases automatically mapped to iTop schema
  - **Fuzzy Matching**: Intelligent name matching for servers, people, and other entities
  - **Real-time Schema Discovery**: Uses `*+` fields for automatic field detection
  - **Enhanced Formatting**: Class-specific output with icons, detailed/summary modes, and grouped results

**Core iTop Operations:**
- **list_operations**: List all available iTop REST API operations
- **smart_query_v2**: Process natural language queries with intelligent class detection and specialized handlers

**Legacy Support (Deprecated):**
- Note: Previous versions included additional tools (get_objects, create_object, update_object, delete_object, apply_stimulus, get_related_objects, check_credentials) which have been streamlined in favor of the more powerful smart_query_v2 approach

## Installation

### Option 1: Install from PyPI (Recommended)

```bash
# Install from PyPI
pip install itop-mcp

# Or using uv
uv add itop-mcp
```

### Node.js Implementation

```bash
# Install from npm (coming soon)
npm install itop-mcp-nodejs

# Or clone and build locally
git clone https://github.com/roneydsilva/itop-mcp.git
cd itop-mcp/nodejs
npm install
npm run build
```

## 🔧 MCP Configuration

### Prerequisites

1. **iTop Instance**: Access to an iTop instance with REST API enabled
2. **iTop User Account**: User account with "REST Services User" profile
3. **Environment Variables**: Set the following environment variables:
   ```bash
   export ITOP_BASE_URL="https://your-itop-instance.com"
   export ITOP_USER="your-username"
   export ITOP_PASSWORD="your-password"
   export ITOP_VERSION="1.4"  # Optional, defaults to 1.4
   ```

### Claude Desktop Configuration

Add to your Claude Desktop configuration file:

**For Python implementation:**

```json
{
  "mcpServers": {
    "itop": {
      "command": "python",
      "args": ["-m", "main"],
      "cwd": "/path/to/itop-mcp",
      "env": {
        "ITOP_BASE_URL": "https://your-itop-instance.com",
        "ITOP_USER": "your-username", 
        "ITOP_PASSWORD": "your-password",
        "ITOP_VERSION": "1.4"
      }
    }
  }
}
```

**For installed package:**

```json
{
  "mcpServers": {
    "itop": {
      "command": "itop-mcp",
      "env": {
        "ITOP_BASE_URL": "https://your-itop-instance.com",
        "ITOP_USER": "your-username",
        "ITOP_PASSWORD": "your-password", 
        "ITOP_VERSION": "1.4"
      }
    }
  }
}
```

**For Node.js implementation:**

```json
{
  "mcpServers": {
    "itop": {
      "command": "node",
      "args": ["dist/index.js"],
      "cwd": "/path/to/itop-mcp/nodejs",
      "env": {
        "ITOP_BASE_URL": "https://your-itop-instance.com",
        "ITOP_USER": "your-username",
        "ITOP_PASSWORD": "your-password",
        "ITOP_VERSION": "1.4"
      }
    }
  }
}
```

### Other MCP Clients

For other MCP clients, use similar configuration with the appropriate command and environment variables.

## 🧠 Smart Query Processor V2

The Smart Query Processor V2 represents a major advancement in natural language query processing for iTop. It features class-specific handlers that understand the unique characteristics and relationships of different iTop object types.

### Supported Classes & Handlers

#### 🎫 Ticket Management
- **UserRequest**: User service requests with SLA tracking
- **Ticket**: Generic ticket operations
- **Change**: Change management tickets
- **Incident**: Incident management
- **Problem**: Problem management

#### 🖥️ Infrastructure
- **Server**: Physical servers with hardware details
- **PC**: Personal computers and workstations  
- **VirtualMachine**: Virtual machine management
- **NetworkDevice**: Network equipment (switches, routers, firewalls)

#### 👥 People & Organization
- **Person**: Individual contacts and users
- **Team**: Team management and assignments
- **Organization**: Organizational structure

### Key Features

#### 🎯 Automatic Class Detection
The system intelligently detects which iTop class you're querying:
```
"Show me all critical servers" → Detects: Server class
"List user requests from last week" → Detects: UserRequest class
"Find network switches in production" → Detects: NetworkDevice class
```

#### 🔍 Advanced Query Capabilities
- **Grouping & Breakdown**: "Show servers grouped by organization"
- **SLA Analysis**: "Find tickets with SLA breaches"
- **Status Filtering**: "List production servers"
- **Multi-criteria**: "Critical VMs owned by Database team"
- **Fuzzy Matching**: Handles typos and variations in names

#### 📊 Enhanced Output Formatting
Each class handler provides:
- **Class-specific icons** (🖥️ for servers, 🎫 for tickets, etc.)
- **Relevant field selection** based on query context
- **Statistical summaries** for grouping queries
- **Detailed vs summary modes** based on query type
- **Rich metadata** including applied filters and query details

#### 🔧 Smart Field Mapping
User-friendly terms are automatically mapped to iTop schema fields:
```
"organization" → "org_name"
"owner" → "owner_friendlyname"  
"critical" → "business_criticity = critical"
"production" → "status = production"
```

### Example Queries

#### Infrastructure Queries
```
"Show all production servers"
"List critical VMs by organization" 
"Find network switches in Datacenter A"
"Count PCs by location"
"Show servers with Windows OS"
```

#### Ticket Management
```
"Show high priority user requests"
"List incidents created this week"
"Find changes scheduled for next month"
"Group tickets by status"
"Show SLA breached requests"
```

#### People & Organization
```
"List active people in IT department"
"Show teams by organization"
"Find managers in Engineering"
"Count users by location"
```

### Advanced Features

#### 🎯 Software Focus Mode
For infrastructure queries, automatic detection of software-related intent:
```
"Show software on Server2" → Returns installed applications
"List applications on production servers" → Software-focused output
```

#### 📈 Statistical Analysis
Automatic grouping and statistical breakdowns:
```
"Servers by organization" → Groups servers and shows counts per org
"Ticket status breakdown" → Shows distribution across statuses
"SLA compliance by team" → Analyzes SLA performance by team
```

#### 🔄 Fallback Support
- Generic handler for classes without specific implementations
- Intelligent field detection for unknown classes
- Graceful degradation with helpful error messages

## 🧪 Development & Testing

### Running Tests

```bash
# Run all tests
python tests/run_tests.py

# Run specific test types
python tests/run_tests.py --unit        # Unit tests only
python tests/run_tests.py --live        # Live tests only (requires iTop instance)
python tests/run_tests.py --nodejs      # Node.js tests only
python tests/run_tests.py --lint        # Linting only

# Auto-fix linting issues
python tests/run_tests.py --fix
```

### Code Quality

The project includes comprehensive linting and formatting:

- **Black**: Code formatting
- **isort**: Import sorting  
- **Flake8**: Code linting
- **mypy**: Type checking (Python)
- **ESLint**: TypeScript linting (Node.js)

### Live Testing

Set environment variables and run live tests against your iTop instance:

```bash
export ITOP_BASE_URL="https://your-itop-instance.com"
export ITOP_USER="your-username"
export ITOP_PASSWORD="your-password"

python tests/test_live.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python tests/run_tests.py`
5. Submit a pull request

## 📋 Example Usage

Once configured, you can ask Claude:

- "Show me all new support tickets with SLA status"
- "Get user requests that have breached SLA"
- "List incidents by priority with table format"
- "Find tickets assigned to John Smith"
- "Create a new user request for printer issues"

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Repository**: https://github.com/roneydsilva/itop-mcp
- **PyPI Package**: https://pypi.org/project/itop-mcp/
- **Issues**: https://github.com/roneydsilva/itop-mcp/issues
- **iTop Documentation**: https://www.itophub.io/wiki/page?id=latest%3Aadvancedtopics%3Arest_json
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Clone and install
   git clone https://github.com/roneydsilva/itop-mcp.git
   cd itop-mcp
   uv sync
   ```

3. **Configure iTop connection**:
   ```bash
   # Copy the example configuration
   cp .env.example .env
   
   # Edit the .env file with your iTop details
   nano .env
   ```

   Required environment variables:
   - `ITOP_BASE_URL`: Your iTop instance URL (e.g., https://itop.yourcompany.com)
   - `ITOP_USER`: Username with REST Services User profile
   - `ITOP_PASSWORD`: Password for the user
   - `ITOP_VERSION`: API version (optional, default: 1.4)

## Usage

### Running the Server

```bash
# Activate the virtual environment
source .venv/bin/activate

# Run the server
uv run main.py
```

### Connecting to Claude Desktop

#### Option 1: Using PyPI Installation

To use this server with Claude Desktop, add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "itop": {
      "command": "itop-mcp",
      "env": {
        "ITOP_BASE_URL": "https://your-itop-instance.com",
        "ITOP_USER": "your_username",
        "ITOP_PASSWORD": "your_password"
      }
    }
  }
}
```

#### Option 2: Using Source Installation

```json
{
  "mcpServers": {
    "itop": {
        "command": "uv",
        "args": [
            "run",
            "--directory",
            "/path/to/itop-mcp",
            "itop-mcp"
        ],
        "env": {
            "ITOP_BASE_URL": "https://your-itop-instance.com",
            "ITOP_USER": "your_username",
            "ITOP_PASSWORD": "your_password",
            "ITOP_VERSION": "1.3"
        }
    }
  }
}
```

> **Note**: This works because we've configured `itop-mcp` as an entry point in `pyproject.toml`. You need to run this from the project directory where `pyproject.toml` is located, or uv needs to be able to find the project.
```

### Example Operations

Once connected, you can ask your AI assistant to perform operations like:

**Basic Operations:**
- "List all open user requests in iTop"
- "Create a new incident ticket for server downtime"
- "Find all CIs related to the mail server"
- "Update the priority of ticket #123 to high"
- "Resolve ticket #456 with resolution details"

**Enhanced Queries:**
- "Get the latest 5 tickets created today"
- "Show me all tickets assigned to John Smith"
- "Find all tickets reported by Jane Doe"
- "Get detailed information for ticket R-000123"
- "List organizations containing 'Tech' in their name"

**Smart Ticket Creation:**
- "Create a new user request for printer issues reported by John from IT Department"

**AI-Powered Smart Queries:**
- "Get me PC count"
- "Give me status-based stats for the PCs"
- "Get me active tickets generated by PC-wise"
- "Change requests completed vs not completed on time"
- "Tickets closed vs not closed on time based on SLA"
- "List all servers in the production environment"
- "Show me all virtual machines running"

## iTop Class Examples

Common iTop classes you can work with:

- **UserRequest**: User requests/tickets
- **Incident**: Incident tickets
- **Person**: Users and contacts
- **Organization**: Organizations/companies
- **Server**: Server configuration items
- **Application**: Application configuration items
- **Service**: IT services
- **Contract**: Contracts and SLAs

## Advanced Features (Updated July 2025)

This server now supports advanced, AI-powered natural language queries and smart schema discovery. Key features include:

- **Smart Query Processor**: Use natural language to ask for any iTop data (e.g., "Show all virtual machines running", "List all servers in production", "Tickets closed vs not closed on time based on SLA").
- **Automatic Class & Field Detection**: The server dynamically discovers iTop classes and fields, so you don't need to hardcode field names.
- **Flexible Output**: Results can be formatted as tables, summaries, JSON, or detailed views.
- **SLA & Time Analysis**: Supports queries about SLA compliance, overdue tickets, and on-time completion.
- **Multi-Query Comparison**: Easily compare stats (e.g., closed vs not closed, completed on time vs not on time).
- **Relationship & Grouping**: Group results by status, organization, or any field, and link related objects (e.g., network devices with locations).
- **Extensible Tools**: Add new tools by decorating async functions with `@mcp.tool()`.

### Example Smart Queries

- "Get me PC count"
- "Give me status-based stats for the PCs"
- "Get me active tickets generated by PC-wise"
- "Change requests completed vs not completed on time"
- "Tickets closed vs not closed on time based on SLA"
- "List all servers in the production environment"
- "Show me all virtual machines running"

### How it Works

- The main server logic is in `main.py`.
- Uses a class taxonomy and dynamic schema discovery to map natural language to iTop REST API queries.
- Handles errors gracefully and provides suggestions if a query returns no results.
- Supports both simple and complex queries, including grouping, filtering, and comparisons.

---

## Security Notes

- Always use HTTPS for your iTop instance in production
- Store credentials securely (use environment variables, not hardcoded values)
- The user account should have minimal necessary permissions
- Test operations in a development environment first
- Use simulation mode for delete operations until you're confident

## Troubleshooting

### Common Issues

1. **Authentication errors**: Ensure your user has the "REST Services User" profile in iTop
2. **Connection errors**: Verify the ITOP_BASE_URL is correct and accessible
3. **Permission errors**: Check that the user has appropriate rights on the objects you're trying to access

### Testing the Connection

Use the `check_credentials` tool to verify your configuration:

```python
# The server will automatically test credentials on startup
# You can also ask the AI assistant: "Check my iTop credentials"
```

## Development

To extend the server:

1. Add new tools by creating functions decorated with `@mcp.tool()`
2. Follow the iTop REST API documentation for available operations
3. Handle errors gracefully and provide informative messages
4. Test thoroughly in a development environment
5. Use the smart query processor for rapid prototyping and testing of new query types

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source. See the LICENSE file for details.

## References

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- [iTop REST API Documentation](https://www.itophub.io/wiki/page?id=latest:advancedtopics:rest_json)
- [iTop Official Website](https://www.combodo.com/itop)