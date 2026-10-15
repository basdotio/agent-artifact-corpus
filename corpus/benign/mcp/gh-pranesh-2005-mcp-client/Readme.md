# MCP_Client

# 🚀 MCP_Client

Welcome to **MCP_Client** — a modern, extensible client for interacting with Model Context Protocol (MCP) servers. It features seamless integration with Next.js and CopilotKit, enabling context-aware AI interactions in web applications.

---

## 📚 Introduction

**MCP_Client** bridges the gap between cutting-edge AI protocols and front-end applications. Designed for developers building interactive web apps with Next.js, it integrates the [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol) and [CopilotKit](https://github.com/CopilotKit) for powerful, context-driven automation and chat.

---

## ✨ Features

- **MCP Protocol Integration**: Communicate with MCP servers using JSON-RPC and SSE.
- **Next.js & CopilotKit Support**: Out-of-the-box compatibility for chat and tool actions.
- **Extensible Client Interface**: Easily add your own tools and endpoints.
- **Real-time Communication**: Supports SSE client transport for live updates.
- **TypeScript & Modern React**: Built with best practices for reliability and maintainability.

---

## 💾 Installation

1. **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/MCP_Client.git
    cd MCP_Client
    ```

2. **Install dependencies for the Next.js app**
    ```bash
    cd my-app
    npm install
    ```

3. **(Optional) Set up environment variables**
    - Copy `.env.example` to `.env.local` and add your API keys (e.g., OpenAI, Azure).

---

## 🚀 Usage

### Starting the Next.js Client

```bash
cd my-app
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser to view the app.

### Running the MCP Server (Example)

> **Note:** The server code is found in `ap.py` and relies on FastMCP and Starlette.

```bash
# Install required Python packages first
pip install httpx starlette uvicorn mcp

# Run the server
python ap.py
```

### Integrating MCPClient

- Use `MCPClient` from `my-app/src/app/utils/mcp-client.ts` to interact with your MCP server.
- Customize tools and endpoints in the client for your use-case.

---

## 🤝 Contributing

Contributions are welcome! To get started:

1. Fork this repo.
2. Create your feature branch (`git checkout -b feature/my-feature`).
3. Commit your changes (`git commit -am 'Add new feature'`).
4. Push to the branch (`git push origin feature/my-feature`).
5. Open a Pull Request.

Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

> _For questions or support, please open an issue on GitHub._  
> _Happy coding!_ 🚀

## License
This project is licensed under the **MIT** License.

---
🔗 GitHub Repo: https://github.com/Pranesh-2005/MCP_Client