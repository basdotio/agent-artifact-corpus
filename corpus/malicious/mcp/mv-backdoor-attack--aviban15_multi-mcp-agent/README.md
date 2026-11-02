# Multi-MCP AI Agent

An Agentic AI agent system that leverages multiple MCP (Model Control Protocol) servers to provide a wide range of capabilities, from basic mathematical operations to advanced external service integrations like Google Workspace and web scraping. The agent includes a Telegram bot interface and Server-Sent Events (SSE) for real-time communication.

## 🌟 Features

- **Multi-MCP Architecture**: Utilizes multiple MCP servers for distributed processing and diverse capabilities
- **Cognitive Modules**: Implements perception, decision-making, memory, and action modules
- **External Service Integration**:
  - Google Workspace (Gmail, Google Drive, Google Sheets)
  - Web scraping and content extraction
  - DuckDuckGo search integration
- **Real-time Communication**:
  - Telegram Bot interface
  - Server-Sent Events (SSE) for live updates
- **Core Components**:
  - Agent loop management
  - Session handling
  - Context management
  - Strategic decision making

## 🏗️ Project Structure

```
├── agent.py              # Main agent entry point
├── core/                 # Core agent components
│   ├── context.py        # Context management
│   ├── loop.py           # Main agent loop
│   ├── session.py        # Session handling
│   └── strategy.py       # Strategic decision making
├── modules/              # Cognitive modules
│   ├── action.py         # Action execution
│   ├── decision.py       # Decision making
│   ├── memory.py         # Memory management
│   ├── model_manager.py  # Model management
│   ├── perception.py     # Input processing
│   └── tools.py          # Tool definitions
├── config/               # Configuration files
│   ├── models.json       # Model configurations
│   └── profiles.yaml     # MCP server profiles
└── mcp_server_*.py       # MCP server implementations
```

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- UV package manager
- Telegram Bot Token (for bot functionality)
- Google Cloud credentials (for Google Workspace integration)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Create and activate a virtual environment:
```bash
uv venv
venv\Scripts\activate  # On Mac: source venv/bin/activate
```

3. Install dependencies using UV:
```bash
uv sync
```

4. Set up environment variables:
   - Create `.env` with Gemini API key and Telegram Bot token.
   - Generate `credentials.json` using Google OAuth client.

### Configuration

1. Configure MCP servers in `config/profiles.yaml`
2. Set up model configurations in `config/models.json`
3. Configure Google Cloud credentials:
   - Place `credentials.json` in the root directory
   - Run the application once to generate `token.json`

## 🎮 Usage

### Starting the Agent

```bash
uv run agent.py
```

### Starting the Telegram Bot Server

```bash
uv run telegram_sse_server.py
```

## 🛠️ MCP Servers

### MCP Server 1: Basic Operations
- Mathematical operations
- Image processing
- File operations

### MCP Server 2: Document Processing
- Document indexing
- Semantic search
- Content extraction
- Image captioning

### MCP Server 3: Web Integration
- DuckDuckGo search
- Web content fetching
- Rate-limited requests

### MCP Server 4: Google Workspace
- Gmail integration
- Google Sheets operations
- Google Drive management
- F1 standings fetcher (URL scraper)

## 📡 Communication

### Telegram Bot
- Command handling
- Message processing
- Real-time responses

### SSE Server
- Real-time event streaming
- Client connection management
- Event broadcasting

## 🧠 Cognitive Architecture

The agent implements a cognitive architecture with the following modules:

- **Perception**: Processes input and extracts relevant information
- **Memory**: Manages state and historical data
- **Decision**: Makes strategic decisions based on input and context
- **Action**: Executes decided actions through appropriate tools

## 📝 License

MIT License
