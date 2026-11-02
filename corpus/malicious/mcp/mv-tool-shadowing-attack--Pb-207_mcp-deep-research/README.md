# 🔍 McpDeepResearch
### An MCP (Model-Context-Protocol) Server for Deep Academic Research  
一个用于深度学术研究的 MCP 服务器

---

[English](#english) | [简体中文](#简体中文)

---

## <span id="english">English</span>

McpDeepResearch is a lightweight but powerful [MCP](https://modelcontextprotocol.io/) (Model-Context-Protocol) server that helps you quickly discover, retrieve, and read academic papers from the web using the familiar **Google Scholar** interface.

### ✨ Features
* **search_scholar_papers** – Google Scholar search with optional year-filter & date-sort  
* **fetch_md** – Convert *any* public web page to clean Markdown  
* **fetch_paper** – Auto-detect the paper content (title, abstract, body, references) and strip the rest  

### 🛠️ Prerequisites
- Python ≥ 3.10
- Google Chrome/Chromium (for headless fetching via [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/))
- Environment variables
  ```bash
  export CDP_ENDPOINT="http://localhost:9222"   # Chrome debugging port
  export GOOGLE_PROXY="http://proxy:port"        # (optional) HTTP(S) proxy
  ```

### ⚙️ Quick Start
1. **Install via pip**
   ```bash
   pip install 
   ```

2. **(Optional) Manually launch Chrome if it isn’t already running**  
   The server will automatically launch a Chrome instance; if not successfully launched, you can launch it manually with:  
   ```bash
   google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-profile &
   ``

3. **Run the MCP server**
   ```bash
   # Launch with SSE
   mcp-deep-research --transport sse --port 8000
   # Launch with STDIO
   mcp-deep-research --transport stdio
   ```

   The server exposes 3 read-only tools to any MCP-capable client.

### 🧑‍🎓 Example Workflow in a Chat-UI
1. **Search**  
   *“Find recent papers on diffusion models after 2022.”*  
   → `search_scholar_papers("diffusion models", year=2022, sort_bd=True)`

2. **Fetch**  
   Pick an interesting PDF link from the results and call  
   `fetch_paper("https://arxiv.org/abs/2304.12345")`

3. **Read**  
   The cleaned Markdown (title, abstract, full text) appears directly in the chat.

### 🔒 Security
- 100 % read-only; no writes, no uploads, no local file access.  
- All traffic respects the original site’s robots.txt.  
- Proxies can be configured to stay within institutional or regional firewalls.

### 🤝 Contributing
PRs are welcome!  

---

## <span id="简体中文">简体中文</span>

McpDeepResearch 是一个轻量级、但功能完备的 [MCP](https://modelcontextprotocol.io/)（Model-Context-Protocol）服务器，帮助你在 **Google Scholar** 上快速发现、抓取并阅读学术文献。

### ✨ 功能一览
* **search_scholar_papers** – 使用关键词在 Google Scholar 中搜索，可过滤年份 / 按日期排序  
* **fetch_md** – 将任意公开网页渲染为整洁的 Markdown  
* **fetch_paper** – 智能提取网页中的论文主体，去除广告、导航条等噪声  

### 🛠️ 前置条件
- Python ≥ 3.10
- Google Chrome / Chromium（通过 [CDP](https://chromedevtools.github.io/devtools-protocol/) 进行无头抓取）
- 环境变量
  ```bash
  export CDP_ENDPOINT="http://localhost:9222"   # Chrome 调试端口
  export GOOGLE_PROXY="http://proxy:port"        # 可选：HTTP(S) 代理
  ```

### ⚙️ 快速开始
1. **通过 pip 安装**
   ```bash
   pip install 
   ```

2. **（可选）如果 Chrome 尚未启动可手动启动**  
   服务器启动时会自动运行 Chrome 实例。若未成功启动，可手动启动：  
   ```bash
   google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-profile &
   ```

3. **启动 MCP 服务器**
   ```bash
   # 以 SSE 启动
   mcp-deep-research --transport sse --port 8000
   # 以 STDIO 启动
   mcp-deep-research --transport stdio
   ```

   服务器会对外暴露 3 个只读工具。

### 🧑‍🎓 对话界面中的典型工作流
1. **搜索**  
   *“找 2022 年之后关于扩散模型的论文。”*  
   → `search_scholar_papers("diffusion models", year=2022, sort_bd=True)`

2. **抓取**  
   从结果中挑选一篇 PDF 链接，调用  
   `fetch_paper("https://arxiv.org/abs/2304.12345")`

3. **阅读**  
   清洗后的 Markdown（含标题、摘要、全文）直接展示在聊天窗口。

### 🔒 安全性
- 完全只读，不修改、不上传、不写入本地文件。  
- 所有请求均尊重目标站点的 robots.txt。  
- 可配置代理以符合校园网或公司网络的安全策略。

### 🤝 如何贡献
欢迎提 PR！  

---
