# MCP FastAPI Server

## 專案介紹

這是一個結合 Model Context Protocol (MCP) 與 FastAPI 的示範性伺服器專案。該專案展示了如何在現代 Python Web 框架中整合 MCP 協議，實現 AI 工具函數的高效調用與通信。

## 功能特色

- **FastMCP 獨立服務器**：提供基於 SSE 的 MCP 工具函數服務
- **FastAPI 整合**：示範如何在 FastAPI 應用中掛載 MCP 服務
- **VS Code 支援**：內建 VS Code MCP 客戶端配置
- **實用工具函數**：提供簡單實用的示範函數

## 專案結構

```
.
├── main.py          # FastMCP 獨立服務器實現
├── test.py          # FastAPI 與 MCP 整合實現
├── .vscode/         # VS Code 配置
│   └── mcp.json     # MCP 客戶端配置
└── __pycache__/     # Python 編譯緩存
```

## 技術規格

- **Python 版本**：3.12+
- **主要依賴**：
  - FastAPI
  - FastMCP
  - fastapi-mcp
  - uvicorn

## 功能模組

### 1. FastMCP 獨立服務器 (main.py)

運行於 9000 端口的獨立 MCP 服務器，提供以下工具函數：

- `add(a, b)`: 加法計算函數，接收兩個整數並返回其和
- `pick_one(options)`: 隨機選擇函數，從提供的選項列表中隨機返回一個元素

### 2. FastAPI 與 MCP 整合 (test.py)

運行於 8000 端口的 FastAPI 應用，展示了如何將 MCP 協議整合到 RESTful API 中：

- **REST API 端點**：
  - `GET /`: 返回歡迎訊息
  - `GET /users/{user_id}`: 返回指定用戶ID的資訊

- **MCP 整合**：
  - 通過 `/mcp` 路徑暴露 MCP 服務接口
  - 使用 FastApiMCP 將 API 操作整合為可調用的 MCP 工具

## 安裝說明

### 前置需求

- Python 3.12 或更高版本
- pip (Python 包管理工具)

### 安裝步驟

1. 克隆專案到本地
   ```bash
   git clone https://github.com/your-username/mcp-fastapi-server.git
   cd mcp-fastapi-server
   ```

2. 安裝依賴包
   ```bash
   pip install fastapi fastmcp fastapi-mcp uvicorn
   ```

## 使用指南

### 啟動 FastMCP 獨立服務器

```bash
python main.py
```

服務器將在 http://localhost:9000 上啟動，使用 SSE 作為傳輸協議。

### 啟動 FastAPI 整合服務器

```bash
python test.py
```

服務器將在 http://localhost:8000 上啟動，MCP 服務可通過 http://localhost:8000/mcp 訪問。

### VS Code 中使用 MCP

1. 安裝 VS Code MCP 擴展
2. 使用專案中的 `.vscode/mcp.json` 配置
3. 打開命令面板 (Ctrl+Shift+P) 並輸入 "MCP: Open Connection Explorer"
4. 選擇 "my-fastapi" 連接
5. 使用提供的工具函數

### API 調用示例

#### 使用 curl 調用 REST API

```bash
# 獲取歡迎訊息
curl http://localhost:8000/

# 獲取用戶資訊
curl http://localhost:8000/users/123
```

#### 使用 MCP 客戶端調用工具函數

通過支持 MCP 協議的客戶端（如 VS Code MCP 擴展）調用：

- `add(a=5, b=3)` - 計算 5+3 的結果
- `pick_one(options=["蘋果", "香蕉", "橘子"])` - 從水果列表中隨機選擇

## 開發與擴展

### 添加新的工具函數

在 `main.py` 中添加新的 MCP 工具：

```python
@mcp.tool()
def your_function(param1: type, param2: type) -> return_type:
    """
    函數說明文檔
    """
    # 實現邏輯
    return result
```

### 添加新的 API 端點

在 `test.py` 中添加新的 FastAPI 端點：

```python
@app.get("/your-endpoint")
def your_endpoint():
    return {"data": "your data"}
```

## 常見問題

- **Q: 如何變更伺服器端口？**  
  A: 修改 `main.py` 或 `test.py` 中的 port 參數。

- **Q: 如何在生產環境中部署？**  
  A: 建議使用 Gunicorn 或其他 ASGI 服務器，配置 HTTPS 和適當的安全措施。

## 致謝

本專案使用了以下開源技術：
- FastAPI - https://fastapi.tiangolo.com/
- Model Context Protocol - https://github.com/microsoft/model-context-protocol

## 授權協議

MIT License

---

*最後更新日期: 2025 年 5 月 16 日*