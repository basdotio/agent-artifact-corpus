# MCP 顺丰物流查询服务示例

这是一个基于 FastMCP 框架开发的顺丰物流查询服务示例项目。该项目展示了如何使用 FastMCP 构建一个简单的物流查询服务。

## 环境要求

- Python 3.12 或更高版本
- uv 包管理器

## 安装

1. 克隆项目：

```bash
git clone https://github.com/CynicalHeart/mcp-started-guide.git
cd mcp-started-guide
```

2. 使用 uv 创建虚拟环境并安装依赖：

```bash
uv venv
uv pip install -e .
```

3. 配置环境变量：

复制 `.env.example` 文件为 `.env`，并填写必要的配置信息：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入以下信息：

```env
# 服务器配置
HOST=127.0.0.1
PORT=8080
MCP_PATH=/mcp

# 云枢配置（需要替换为实际值）
APP_KEY=your_app_key_here
APP_SECRET=your_app_secret_here
REQUEST_URL=your_request_url_here
```

## 运行服务

```bash
python main.py
```

服务将在 http://127.0.0.1:8080/mcp 启动。

## 客户端连接

### 使用 Cursor 连接

1. 在 Cursor 中，打开命令面板（Ctrl+Shift+P）
2. 输入 "Connect to MCP Server"
3. 输入服务器地址：http://127.0.0.1:8080/mcp/sf

### 注意事项

- 本项目使用 streamable-http 传输方式，不是所有客户端都支持这种传输方式
- 目前已知支持 streamable-http 的客户端：
  - Cursor
  - VS Code（需要安装 MCP 插件）
- 不支持 streamable-http 的客户端将无法连接到服务

## 功能说明

- 提供顺丰物流查询服务
- 支持通过快递单号和手机号查询物流信息
- 所有配置参数（appKey、appSecret、requestUrl）需要由客户端传入
- 服务器配置（host、port、path）可通过环境变量修改

## 参数说明

调用 `query_route` 函数时需要提供以下参数：

- `appKey`: 云枢的 appKey
- `appSecret`: 云枢的 appSecret
- `sfCode`: 顺丰的快递单号
- `phone`: 快递接收方手机号信息
- `requestUrl`: 云枢顺丰接口请求地址（可选）

## 许可证

MIT License

