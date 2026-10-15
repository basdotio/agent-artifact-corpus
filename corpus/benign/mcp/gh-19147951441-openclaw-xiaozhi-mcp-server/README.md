# OpenClaw--xiaozhi MCP Server

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-2024--11--05-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **OpenClaw-xiaozhi MCP Server** 是一个基于 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 协议的智能桥接服务器，用于将用户意图通过 MCP 转发给 OpenClaw（贾维斯）AI 助手处理。支持异步任务处理、WebSocket 实时通信和任务完成回调通知。

## 📖 目录

- [功能特点](#-功能特点)
- [系统架构](#-系统架构)
- [环境要求](#-环境要求)
- [安装指南](#-安装指南)
- [配置说明](#-配置说明)
- [使用方法](#-使用方法)
- [API 参考](#-api-参考)
- [部署选项](#-部署选项)
- [故障排除](#-故障排除)
- [许可证](#-许可证)

## ✨ 功能特点

- **🚀 异步处理** - 立即返回"处理中"状态，不阻塞客户端
- **🔄 WebSocket 实时通信** - 与小智 MCP 服务器保持长连接
- **📬 回调通知** - 任务完成后自动通知用户
- **🛠️ 多工具支持** - 提供多种工具接口（ask_jarvis, execute_task, process_intent 等）
- **🔌 自动重连** - 连接断开后自动重连，支持指数退避
- **📊 完整 MCP 协议** - 支持 JSON-RPC 2.0 和 MCP 2024-11-05 协议
- **💼 生产就绪** - 支持 Windows 服务、任务计划程序等多种部署方式

## 🏗️ 系统架构

```
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│  MCP 客户端     │────▶│  OpenClaw MCP       │────▶│  小智 MCP       │
│  (Claude 等)    │◀────│  Server (本服务)    │◀────│  WebSocket      │
└─────────────────┘     └─────────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │  OpenClaw       │
                        │  (贾维斯 AI)    │
                        └─────────────────┘
```

### 工作流程

```
1. MCP 客户端发送意图
         │
         ▼
2. MCP Server 立即返回 task_id（状态：processing）
         │
         ▼
3. 异步发送给 OpenClaw 处理
         │
         ▼
4. OpenClaw 处理完成后通过 WebSocket 回调
         │
         ▼
5. 客户端可通过 get_task_result 查询结果
```

## 📋 环境要求

### 必需软件

| 软件 | 版本 | 说明 |
|------|------|------|
| Python | 3.9+ | 推荐 Python 3.11+ |
| pip | 21.0+ | Python 包管理器 |

### 可选软件（用于生产部署）

| 软件 | 用途 |
|------|------|
| Windows 10/11 | 运行环境 |
| PowerShell 5.1+ | 运行安装脚本 |

### Python 依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| mcp | >=1.0.0 | MCP 协议实现 |
| websockets | >=12.0 | WebSocket 通信 |
| python-dotenv | >=1.0.0 | 环境变量管理 |

## 📦 安装指南

### 方法一：源码安装（推荐）

```bash
# 1. 克隆或下载项目
cd C:\Users\user\Desktop\openclaw-mcp-server

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境（Windows）
venv\Scripts\activate

# 4. 安装依赖
pip install -r requirements.txt
```

### 方法二：使用 install-startup.bat

```bash
# 双击运行或命令行执行
install-startup.bat
```

## ⚙️ 配置说明

### 1. 环境变量配置

复制 `.env.example` 为 `.env`：

```bash
copy .env.example .env
```

编辑 `.env` 文件，设置您的 Token：

```env
# OpenClaw MCP Token
# 从 wss://api.xiaozhi.me/mcp/?token=xxx 中获取
OPENCLAW_TOKEN=your_token_here
```

### 2. 获取 Token

1. 访问小智 MCP 平台
2. 创建您的 Agent
3. 复制包含 token 的 WebSocket URL
4. 提取 `token=` 后面的值填入 `.env`

### 3. MCP 客户端配置

#### Claude Desktop 配置

编辑 Claude Desktop 配置文件（通常位于 `%APPDATA%\Claude\claude_desktop_config.json`）：

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

#### 其他 MCP 客户端

```json
{
  "mcpServers": {
    "openclaw": {
      "command": "path/to/your/python",
      "args": ["path/to/openclaw-mcp-server/server.py"],
      "env": {
        "OPENCLAW_TOKEN": "your_token"
      }
    }
  }
}
```

## 🚀 使用方法

### 启动服务器

```bash
# 激活虚拟环境
venv\Scripts\activate

# 运行服务器
python server.py
```

### 使用 run.bat 脚本

```bash
# 直接运行
run.bat
```

### 测试连接

```bash
# 运行测试脚本
python test_mcp_full.py
```

## 📡 API 参考

### 工具列表

#### 1. process_intent

发送用户意图并立即返回任务 ID（异步处理）。

**参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| intent | string | ✅ | 用户意图或请求内容 |
| context | object | ❌ | 可选的上下文信息 |

**请求示例：**
```json
{
  "intent": "帮我写一封邮件",
  "context": {
    "tone": "formal",
    "recipient": "client"
  }
}
```

**响应示例：**
```json
{
  "status": "processing",
  "task_id": "task_1",
  "message": "意图已接收，正在处理中...",
  "intent_preview": "帮我写一封邮件"
}
```

#### 2. get_task_result

查询任务处理结果。

**参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| task_id | string | ✅ | 任务 ID（由 process_intent 返回） |

**请求示例：**
```json
{"task_id": "task_1"}
```

**响应示例（完成）：**
```json
{
  "status": "completed",
  "result": {
    "content": "尊敬的客户，..."
  }
}
```

**响应示例（处理中）：**
```json
{
  "status": "processing",
  "message": "任务仍在处理中，请稍后查询"
}
```

#### 3. ask_jarvis

向贾维斯提问获取智能回答。

**参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| question | string | ✅ | 要问的问题 |
| context | object | ❌ | 可选的上下文信息 |

#### 4. execute_task

让贾维斯执行特定任务。

**参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| task_description | string | ✅ | 任务描述 |
| parameters | object | ❌ | 任务参数 |

#### 5. get_status

获取贾维斯当前状态。

**响应示例：**
```json
{
  "name": "贾维斯",
  "status": "online",
  "version": "1.0.0",
  "capabilities": [
    "自然语言理解",
    "任务执行",
    "信息查询",
    "工具调用"
  ]
}
```

## 🖥️ 部署选项

### 方案一：Windows 服务（推荐用于生产环境）

**特点：**
- ✅ 最稳定，系统级服务
- ✅ 开机自动启动
- ✅ 进程崩溃自动重启
- ✅ 完善的日志管理
- ⚠️ 需要管理员权限

**安装步骤：**

1. 右键点击 `install-service.ps1`
2. 选择 **"以管理员身份运行"**
3. 按提示完成安装

**管理命令：**
```powershell
# 启动服务
net start JarvisMCPBridge

# 停止服务
net stop JarvisMCPBridge

# 查看状态
sc query JarvisMCPBridge

# 查看日志
Get-Content service.log -Tail 50

# 卸载服务（管理员）
.\uninstall-service.ps1
```

### 方案二：任务计划程序（适合个人使用）

**特点：**
- ✅ 无需管理员权限
- ✅ 用户登录时自动启动
- ✅ 进程崩溃自动重启

**安装步骤：**

1. 双击运行 `install-task.ps1`
2. 按提示完成安装

**管理命令：**
```powershell
# 启动任务
Start-ScheduledTask -TaskName JarvisMCPBridge_AutoStart

# 停止任务
Stop-ScheduledTask -TaskName JarvisMCPBridge_AutoStart

# 查看状态
Get-ScheduledTask -TaskName JarvisMCPBridge_AutoStart
```

### 方案三：开机启动文件夹（简单测试）

**步骤：**

1. 按 `Win + R`
2. 输入 `shell:startup`
3. 创建 `start-service.bat` 的快捷方式

### 部署方案对比

| 特性 | Windows 服务 | 任务计划 | 启动文件夹 |
|------|-------------|---------|-----------|
| 管理员权限 | 需要 | 不需要 | 不需要 |
| 开机启动 | ✅ | ✅ (登录时) | ✅ (登录时) |
| 自动重启 | ✅ | ✅ | ❌ |
| 日志管理 | ✅ | ⚠️ | ❌ |
| 稳定性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 推荐场景 | 生产环境 | 个人使用 | 临时测试 |

## 🐛 故障排除

### 常见问题

#### 1. OPENCLAW_TOKEN 未设置

**错误信息：**
```
ValueError: 请设置 OPENCLAW_TOKEN 环境变量
```

**解决方案：**
- 确保 `.env` 文件存在于项目根目录
- 检查 `.env` 文件中 `OPENCLAW_TOKEN` 是否正确设置

#### 2. WebSocket 连接失败

**错误信息：**
```
连接失败：...
```

**解决方案：**
- 检查网络连接
- 验证 Token 是否有效
- 检查防火墙设置

#### 3. 依赖安装失败

**解决方案：**
```bash
# 升级 pip
python -m pip install --upgrade pip

# 重新安装依赖
pip install -r requirements.txt --force-reinstall
```

#### 4. 服务无法启动

**诊断步骤：**
```powershell
# 查看详细错误
sc qc JarvisMCPBridge

# 手动测试运行
cd C:\Users\user\Desktop\openclaw-mcp-server
venv\Scripts\activate
python bridge.py
```

### 日志查看

```powershell
# 查看服务日志
Get-Content service.log -Tail 100

# 持续跟踪日志
Get-Content service.log -Wait -Tail 20
```

### 检查 Python 环境

```powershell
# 确认 Python 路径
where python

# 确认虚拟环境激活
echo %VIRTUAL_ENV%

# 检查已安装的包
pip list | Select-String "websockets|mcp|dotenv"
```

## 📁 项目结构

```
openclaw-mcp-server/
├── server.py                 # MCP 服务器主程序
├── bridge.py                 # 小智桥接器（完整 MCP 协议）
├── openclaw_client.py        # OpenClaw WebSocket 客户端
├── tools.py                  # MCP 工具定义
├── config.py                 # 配置管理
├── requirements.txt          # Python 依赖
├── .env                      # 环境变量（需自行创建）
├── .env.example              # 环境变量示例
├── manifest.json             # 项目清单
├── mcp-client-config.json    # MCP 客户端配置示例
│
├── run.bat                   # 快速运行脚本
├── start-service.bat         # 服务启动脚本
├── install-service.ps1       # 安装 Windows 服务
├── uninstall-service.ps1     # 卸载服务
├── install-task.ps1          # 安装任务计划
├── install-startup.bat       # 快速安装脚本
│
├── test_client.py            # 客户端测试
├── test_mcp_full.py          # 完整 MCP 测试
│
├── README.md                 # 本文档
├── SERVICE_GUIDE.md          # 服务部署指南
├── SETUP_COMPLETE.md         # 安装完成说明
└── TEST_REPORT.md            # 测试报告
```

## 🔧 开发指南

### 添加新工具

在 `tools.py` 中添加新的工具定义：

```python
@mcp.tool()
def your_new_tool(param1: str, param2: int = 0) -> dict:
    """
    工具描述
    
    Args:
        param1: 参数 1 说明
        param2: 参数 2 说明
    
    Returns:
        返回结果
    """
    # 实现逻辑
    return {"result": "success"}
```

### 调试模式

```bash
# 启用详细日志
python -u server.py 2>&1 | tee debug.log
```

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 支持

如有问题，请提交 Issue 或联系维护者。

---

**🤖 Powered by OpenClaw (贾维斯)**