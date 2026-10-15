# 🧠 News Agent MCP Server

## 1. Introduction

The **News Agent MCP Server** is a lightweight, schema-backed capability engine designed for LLM-based agents. It provides structured and semi-structured information retrieval tools over a streamable HTTP interface, enabling agents to perform iterative research workflows.

This server is **not intended to be exposed as a public API**. Instead, it operates as an internal execution layer within a larger system, where orchestration, safety, and control are handled externally.

---

## 2. System Role in Architecture

This MCP server is part of a modular LLM system with clear separation of responsibilities:

- **Agent (LLM Layer)**  
  Handles reasoning, decision-making, and tool selection

- **MCP Server (This Repository)**  
  Executes capabilities such as news retrieval and web scraping

- **Gateway Layer (Go-based)**  
  Manages rate limiting, authentication, routing, and safety constraints

This separation ensures:
- Cleaner system design  
- Easier scalability  
- Independent evolution of components  

---

## 3. Design Philosophy

The server is intentionally designed with the following principles:

- **Minimal Core Engine**  
  Focus only on capability execution, not orchestration or control

- **Schema Where Needed, Flexibility Where Needed**  
  - Structured outputs for predictable data (news)
  - Flexible outputs for rich content (web scraping)

- **LLM-First Interface**  
  All inputs and outputs are strings to ensure seamless integration with LLM agents

- **Externalized Concerns**  
  Features like rate limiting, authentication, and recursion control are handled outside this service

---

## 4. Architecture Overview

- Built using **FastMCP (Python)**
- Tools are exposed via `@tool` decorators
- Runs as a **streamable HTTP server**
- Endpoint exposed at: `/mcp`
- Designed to be deployed as a **Docker container**

---

## 5. Capabilities

### 5.1 `get_latest_news` — Discovery Layer

Fetches recent news articles based on a given topic.

**Input**
- `topic` (string)

**Output**
- JSON string (serialized)

Internally backed by a Pydantic model:

```python
class Article(BaseModel):
    article_id: Optional[str] = None
    link: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    creator: Optional[list[str]] = None
    country: Optional[list[str]] = None
    category: Optional[list[str]] = None
    pubDate: Optional[str] = None
    image_url: Optional[str] = None
    source_url: Optional[str] = None
```

External Dependency:
- newsdata.io

Role:
- Acts as the entry point for discovery
- Provides structured, machine-consumable data for agents
 
 ---

 ## 6. Deep Research Pattern

This server is designed to support iterative research workflows:
```
Topic → News → URLs → Scrape → Extract Insights → Discover New URLs → Repeat (bounded)
```

This pattern enables agents to:

- Start with high-level discovery
- Expand into detailed content
- Traverse information progressively

The MCP server provides the building blocks, while:

- The agent controls reasoning
- The gateway enforces limits and safety

---

## 7. Interface Contract
Input/Output Design
- All tools accept string inputs
- All tools return string outputs

### Internal vs External Representation

| Layer    | Representation               |
|----------|------------------------------|
| Internal | Structured (Pydantic models) |
| External | Serialized strings           |

Rationale
- Eliminates parsing friction for LLMs
- Keeps integration simple and predictable
- Maintains flexibility across tools

---

## 8. Setup & Deployment
Environment Variables
```bash
NEWSDATA_API_KEY=your_api_key
FIRECRAWL_API_KEY=your_api_key
```

---

### Running with Docker
The server is containerized and can be run using Docker:
```bash
docker run -p <host_port>:<container_port> <image_name>
```
Endpoint
```bash
/mcp
```

---

## 9. Limitations (Intentional)

This server intentionally avoids implementing:
- Rate limiting
- Authentication
- Request validation layers
- Recursion or depth control

### Why?
These concerns are handled by the upstream gateway layer, allowing this service to remain:
- Simple
- Focused
- Easy to maintain

---

## 10. Future Enhancements

Potential improvements include:
- Optional structured output mode for all tools
- Tool metadata and schema exposure for dynamic discovery
- Built-in safety primitives (optional, toggle-based)
- Observability hooks (logging, tracing)
- Configurable content limits (size, depth, etc.)

---

## Final Note

This MCP server is designed as a modular capability engine, not a full application. Its strength lies in:

- Clean separation of concerns
- LLM-friendly interface design
- Support for iterative, multi-step research workflows

It is best used as part of a larger system where reasoning, control, and safety are handled externally.

---

## 👤 Maintainer
Tuhin Kumar Dutta

- 🌐 Website: https://www.tuhindutta.com/
- 💼 LinkedIn: https://www.linkedin.com/in/t-k-dutta

---

## ⭐ Contribute
Pull requests and issues are welcome.
```bash
git clone https://github.com/tuhindutta/news-agent-mcp-server.git
```
DockerHub: [https://hub.docker.com/r/tkdutta/news-agent-mcp-server](https://hub.docker.com/r/tkdutta/news-agent-mcp-server)
