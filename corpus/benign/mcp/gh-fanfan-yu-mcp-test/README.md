# Python MCP Server Starter

![Python](https://img.shields.io/badge/python-3.13%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A beginner-friendly Python implementation of an MCP (Model Context Protocol) server, designed to help newcomers understand MCP server development fundamentals.

## 🚀 TODO Features

## 📋 Prerequisites

- Python 3.13+
- pip package manager

## ⚡ Quick Start

### 1. Clone the repository
```bash
git clone git@github.com:fanfan-yu/mcp-test.git
cd mcp-test
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the server
```bash
python server.py
```
## 📚 Start with mcp inspector

### 1. Clone the repository
```bash
git clone git@github.com:fanfan-yu/mcp-test.git
cd mcp-test
```

### 2. Launch MCP Inspector
Ensure Node.js (with npm and npx) is installed.

```bash
npx @modelcontextprotocol/inspector@0.9
```
#### Next Steps
- Keep the terminal running
- Open http://localhost:6274 in your browser

### 3. Test in mcp inspector

In the browser interface:

| Configuration     | Value           | Description                     |
|-------------------|-----------------|---------------------------------|
| Transport Type    | `STDIO`         | Select standard I/O protocol    |
| Command           | `uv`            | Ensure [uv](https://github.com/astral-sh/uv) is installed |
| Arguments         | `run server.py` | Execution parameters            |


### 4. Verify
- Click 'List Tools'
- Click 'redis_execution'
- Set 'input' and click 'Run Tool'

## 🛠️ Project Structure

```
├── README.md - Project documentation
├── requirements.txt - Dependencies
├── server.py - Server main file
└── config.yaml - Server demo configuration
```

## 📌 TODO List

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a PR for any improvements.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.