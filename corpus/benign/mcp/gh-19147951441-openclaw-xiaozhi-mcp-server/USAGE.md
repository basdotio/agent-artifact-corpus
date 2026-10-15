# OpenClaw-xiaozhi MCP Server 使用指南

详细的使用说明文档，帮助您快速上手 OpenClaw-xiaozhi MCP Server。

## 📋 目录

- [快速开始](#快速开始)
- [基础使用](#基础使用)
- [进阶用法](#进阶用法)
- [工具使用示例](#工具使用示例)
- [集成到应用](#集成到应用)
- [最佳实践](#最佳实践)

---

## 快速开始

### 5 分钟快速配置

#### 步骤 1: 安装依赖

```bash
# 进入项目目录
cd C:\Users\user\Desktop\openclaw-mcp-server

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

#### 步骤 2: 配置 Token

```bash
# 复制示例文件
copy .env.example .env

# 编辑 .env 文件，填入您的 OPENCLAW_TOKEN
notepad .env
```

#### 步骤 3: 启动服务

```bash
# 运行服务器
python server.py
```

#### 步骤 4: 测试连接

```bash
# 新开一个终端
python test_mcp_full.py
```

---

## 基础使用

### 启动方式

#### 方式 1: 直接运行

```bash
python server.py
```

#### 方式 2: 使用批处理脚本

```bash
run.bat
```

#### 方式 3: 调试模式

```bash
# 显示详细日志
python -u server.py
```

### 验证运行状态

成功启动后，您应该看到类似输出：

```
2026-03-14 10:00:00 - openclaw_mcp - INFO - 🚀 OpenClaw MCP Server 启动...
2026-03-14 10:00:01 - openclaw_client - INFO - ✅ OpenClaw WebSocket 已连接
```

---

## 进阶用法

### MCP 客户端配置

#### Claude Desktop 配置

1. 找到配置文件位置：
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

2. 添加以下配置：

```json
{
  "mcpServers": {
    "openclaw": {
      "command": "python",
      "args": ["C:/Users/user/Desktop/openclaw-mcp-server/server.py"],
      "env": {
        "OPENCLAW_TOKEN": "your_token_here"
      }
    }
  }
}
```

3. 重启 Claude Desktop

#### 其他 MCP 兼容客户端

```json
{
  "mcpServers": {
    "openclaw": {
      "command": "python",
      "args": ["/absolute/path/to/server.py"],
      "env": {
        "OPENCLAW_TOKEN": "your_token",
        "PYTHONPATH": "/path/to/venv/Lib/site-packages"
      }
    }
  }
}
```

### 使用 stdio 传输

OpenClaw MCP Server 使用 stdio 传输模式，通过标准输入/输出与客户端通信：

```
┌──────────────┐    stdin/stdout    ┌──────────────┐
│ MCP 客户端   │◀──────────────────▶│ MCP 服务器   │
│ (Claude 等)  │                    │ (本服务)     │
└──────────────┘                    └──────────────┘
```

---

## 工具使用示例

### 1. process_intent - 处理用户意图

**用途**: 发送用户意图并异步处理，立即返回任务 ID。

**使用场景**:
- 需要长时间处理的任务
- 不希望阻塞客户端
- 需要后续查询结果的场景

**示例请求**:
```json
{
  "name": "process_intent",
  "arguments": {
    "intent": "帮我分析这份销售数据，找出增长趋势",
    "context": {
      "data_type": "sales",
      "time_range": "2024-Q4",
      "format": "summary"
    }
  }
}
```

**示例响应**:
```json
{
  "status": "processing",
  "task_id": "task_1",
  "message": "意图已接收，正在处理中...",
  "intent_preview": "帮我分析这份销售数据，找出增长趋势"
}
```

**查询结果**:
```json
{
  "name": "get_task_result",
  "arguments": {
    "task_id": "task_1"
  }
}
```

### 2. get_task_result - 获取任务结果

**用途**: 查询异步任务的执行结果。

**使用场景**:
- 配合 process_intent 使用
- 轮询任务状态
- 获取最终处理结果

**示例请求**:
```json
{
  "name": "get_task_result",
  "arguments": {
    "task_id": "task_1"
  }
}
```

**响应（处理中）**:
```json
{
  "status": "processing",
  "message": "任务仍在处理中，请稍后查询"
}
```

**响应（已完成）**:
```json
{
  "status": "completed",
  "result": {
    "analysis": "销售数据显示 Q4 同比增长 23%...",
    "charts": [...],
    "recommendations": [...]
  }
}
```

### 3. ask_jarvis - 向贾维斯提问

**用途**: 直接向贾维斯 AI 提问获取智能回答。

**使用场景**:
- 问答类任务
- 需要即时回复的场景
- 知识查询

**示例请求**:
```json
{
  "name": "ask_jarvis",
  "arguments": {
    "question": "什么是 MCP 协议？",
    "context": {
      "detail_level": "beginner",
      "include_examples": true
    }
  }
}
```

**示例响应**:
```json
{
  "content": [
    {
      "type": "text",
      "text": "MCP（Model Context Protocol）是一种用于..."
    }
  ],
  "isError": false
}
```

### 4. execute_task - 执行任务

**用途**: 让贾维斯执行特定任务。

**使用场景**:
- 需要执行具体操作
- 多步骤任务
- 需要参数配置的任务

**示例请求**:
```json
{
  "name": "execute_task",
  "arguments": {
    "task_description": "生成一份月度销售报告",
    "parameters": {
      "month": "2024-12",
      "include_charts": true,
      "format": "markdown",
      "sections": ["summary", "trends", "recommendations"]
    }
  }
}
```

**示例响应**:
```json
{
  "content": [
    {
      "type": "text",
      "text": "{\n  \"success\": true,\n  \"status\": \"completed\",\n  \"report_url\": \"...\"\n}"
    }
  ],
  "isError": false
}
```

### 5. get_status - 获取状态

**用途**: 获取贾维斯当前状态信息。

**使用场景**:
- 健康检查
- 确认服务可用性
- 获取能力列表

**示例请求**:
```json
{
  "name": "get_status"
}
```

**示例响应**:
```json
{
  "content": [
    {
      "type": "text",
      "text": "{\n  \"name\": \"贾维斯\",\n  \"status\": \"online\",\n  \"version\": \"1.0.0\",\n  \"capabilities\": [\n    \"自然语言理解\",\n    \"任务执行\",\n    \"信息查询\",\n    \"工具调用\"\n  ]\n}"
    }
  ],
  "isError": false
}
```

---

## 集成到应用

### Python 集成示例

```python
import asyncio
import json
import subprocess

class OpenClawMCPClient:
    def __init__(self, server_path, token):
        self.server_path = server_path
        self.token = token
        self.process = None
        
    async def start_server(self):
        """启动 MCP 服务器"""
        self.process = subprocess.Popen(
            ["python", self.server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            env={"OPENCLAW_TOKEN": self.token},
            text=True
        )
        
    async def send_request(self, tool_name, arguments):
        """发送工具调用请求"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        # 发送请求
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        
        # 读取响应
        response = await asyncio.get_event_loop().run_in_executor(
            None, self.process.stdout.readline
        )
        return json.loads(response)
    
    async def process_intent(self, intent, context=None):
        """便捷方法：发送意图"""
        return await self.send_request("process_intent", {
            "intent": intent,
            "context": context or {}
        })

# 使用示例
async def main():
    client = OpenClawMCPClient(
        server_path="C:/Users/user/Desktop/openclaw-mcp-server/server.py",
        token="your_token"
    )
    
    await client.start_server()
    
    # 发送意图
    result = await client.process_intent(
        intent="帮我写一封邮件",
        context={"tone": "formal"}
    )
    print(f"任务 ID: {result.get('task_id')}")

asyncio.run(main())
```

### Node.js 集成示例

```javascript
const { spawn } = require('child_process');
const readline = require('readline');

class OpenClawMCPClient {
  constructor(serverPath, token) {
    this.serverPath = serverPath;
    this.token = token;
    this.process = null;
    this.messageId = 0;
  }

  async startServer() {
    this.process = spawn('python', [this.serverPath], {
      env: { ...process.env, OPENCLAW_TOKEN: this.token },
      stdio: ['pipe', 'pipe', 'inherit']
    });

    this.rl = readline.createInterface({
      input: this.process.stdout,
      output: this.process.stdin
    });
  }

  async sendRequest(toolName, arguments) {
    return new Promise((resolve, reject) => {
      const id = ++this.messageId;
      const request = {
        jsonrpc: '2.0',
        id,
        method: 'tools/call',
        params: {
          name: toolName,
          arguments
        }
      };

      this.process.stdin.write(JSON.stringify(request) + '\n');

      this.rl.once('line', (line) => {
        try {
          const response = JSON.parse(line);
          resolve(response);
        } catch (e) {
          reject(e);
        }
      });
    });
  }

  async processIntent(intent, context = {}) {
    return this.sendRequest('process_intent', { intent, context });
  }
}

// 使用示例
async function main() {
  const client = new OpenClawMCPClient(
    'C:/Users/user/Desktop/openclaw-mcp-server/server.py',
    'your_token'
  );

  await client.startServer();

  const result = await client.processIntent(
    '帮我分析数据',
    { data_type: 'sales' }
  );
  console.log('任务 ID:', result.task_id);
}

main().catch(console.error);
```

---

## 最佳实践

### 1. 异步任务处理

对于可能耗时较长的任务，使用 `process_intent` + `get_task_result` 模式：

```python
# ✅ 推荐：异步处理
async def handle_long_task(intent):
    # 立即返回任务 ID
    response = await client.process_intent(intent)
    task_id = response['task_id']
    
    # 轮询获取结果
    while True:
        result = await client.get_task_result(task_id)
        if result['status'] == 'completed':
            return result['result']
        await asyncio.sleep(1)

# ❌ 不推荐：同步等待
```

### 2. 错误处理

```python
async def safe_call(tool_name, arguments):
    try:
        result = await client.send_request(tool_name, arguments)
        if result.get('isError'):
            logger.error(f"工具调用失败：{result}")
            return None
        return result
    except Exception as e:
        logger.error(f"调用异常：{e}")
        return None
```

### 3. 连接管理

```python
class ManagedClient:
    def __init__(self):
        self.client = None
        
    async def __aenter__(self):
        self.client = OpenClawMCPClient(...)
        await self.client.start_server()
        return self.client
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client and self.client.process:
            self.client.process.terminate()
```

### 4. 日志记录

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('openclaw_client')

# 在关键操作处记录日志
logger.info(f"发送意图：{intent}")
logger.debug(f"响应：{response}")
```

### 5. 重试机制

```python
import asyncio
from functools import wraps

def retry(max_attempts=3, delay=1):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    await asyncio.sleep(delay * (attempt + 1))
        return wrapper
    return decorator

@retry(max_attempts=3, delay=1)
async def call_with_retry(tool_name, arguments):
    return await client.send_request(tool_name, arguments)
```

---

## 常见问题解答

### Q: 如何知道任务是否完成？

A: 使用 `get_task_result` 轮询任务状态：
- `status: "processing"` - 任务仍在处理
- `status: "completed"` - 任务已完成
- `status: "error"` - 任务出错

### Q: 任务超时怎么处理？

A: 建议在客户端实现超时逻辑：
```python
async def call_with_timeout(tool_name, arguments, timeout=30):
    try:
        return await asyncio.wait_for(
            client.send_request(tool_name, arguments),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        return {"error": "请求超时"}
```

### Q: 可以并发处理多个任务吗？

A: 可以，每个任务有独立的 task_id：
```python
tasks = [
    client.process_intent("任务 1"),
    client.process_intent("任务 2"),
    client.process_intent("任务 3")
]
results = await asyncio.gather(*tasks)
```

### Q: 如何调试 MCP 通信？

A: 启用详细日志：
```bash
python -u server.py 2>&1 | tee mcp.log
```

---

**最后更新**: 2026 年 3 月 14 日