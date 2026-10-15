# 🌐 LifeFlow Remote FastMCP Servers (Cloud Intelligence Hub)

[![FastMCP](https://img.shields.io/badge/FastMCP-v4.0.11-blue.svg)](https://github.com/jlowin/fastmcp)
[![Python](https://img.shields.io/badge/Python-3.12%2B-brightgreen.svg)](https://python.org)
[![Protocol](https://img.shields.io/badge/Protocol-MCP%20SSE-orange.svg)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**LifeFlow Remote MCP** is a cloud-deployable, standalone **Model Context Protocol (MCP)** microservice built with **FastMCP** communicating over **Server-Sent Events (SSE / HTTP)** transport.

It provides real-time public telemetry and global market intelligence to any AI client worldwide — **without requiring local workstation access**.

---

## ⚡ Live Cloud Deployment URL

Once deployed on **FastMCP Cloud** (Prefect Horizon) or any cloud container, this server is accessible at:

```
https://2in1cryptoweather.fastmcp.app/mcp
```
*(Or your local/custom SSE endpoint: `http://localhost:8001/sse`)*

---

## 🛠️ Exposed Tools & Capabilities

All tools are bundled into the unified **`LifeFlowCloudIntelligence`** server:

| Tool Name | Parameters | Description | Data Source |
|---|---|---|---|
| `convert_currency` | `amount`, `from_curr`, `to_curr` | Live fiat currency conversion with current exchange rates | Open Exchange Rates API |
| `get_crypto_price` | `coin` (bitcoin, ethereum, solana) | Real-time market prices in both USD & INR | CoinGecko API |
| `get_city_weather` | `city` | Live temperature, humidity, and outdoor commute status | Open-Meteo Geocoding API |
| `get_city_living_tips` | `city` | Cost of living guides, transit budget, and dining estimates | Curated Metro Index |

### 📦 Exposed Resources
- `resource://cloud/status` — Live health telemetry and external API availability check.

---

## 🔌 How to Connect to Claude Desktop or Cursor IDE

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "lifeflow_remote_cloud": {
      "url": "https://2in1cryptoweather.fastmcp.app/mcp"
    }
  }
}
```

Now Claude Desktop can immediately convert currencies, look up cryptocurrency values, and check weather/living costs globally without installing anything locally!

---

## 🚀 Local Development & Testing

### 1. Clone & Install
```bash
git clone https://github.com/yashsham/lifeflow-remote-mcp.git
cd lifeflow-remote-mcp
pip install -r requirements.txt
```

### 2. Run Server
```bash
# Start server on http://localhost:8001/sse
python server.py
```

---

## 🐳 Docker Container Deployment

```bash
# Build Docker image
docker build -t lifeflow-remote-mcp .

# Run container on port 8001
docker run -d -p 8001:8001 --name lifeflow-remote lifeflow-remote-mcp
```

---

## 🔗 Related Ecosystem Projects

- 🏠 **[lifeflow-local-mcp](https://github.com/yashsham/lifeflow-local-mcp)**: Privacy-first on-device FastMCP servers for personal finance and habits via `stdio`.
- ⚡ **[lifeflow-mcp](https://github.com/yashsham/lifeflow-mcp)**: Full-stack master platform with Custom MCP Client, NVIDIA NIM AI Brain, and Live Protocol Inspector.

---

## 📄 License
Released under the [MIT License](LICENSE).
