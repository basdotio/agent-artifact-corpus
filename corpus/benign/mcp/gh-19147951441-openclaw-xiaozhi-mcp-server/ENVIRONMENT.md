# 环境配置与依赖说明

本文档详细描述了 OpenClaw-xiaozhi MCP Server 的环境要求、依赖项和配置方法。

## 📋 目录

- [系统要求](#系统要求)
- [Python 环境配置](#python-环境配置)
- [依赖安装](#依赖安装)
- [环境变量配置](#环境变量配置)
- [网络要求](#网络要求)
- [故障排除](#故障排除)

---

## 系统要求

### 操作系统

| 操作系统 | 版本要求 | 支持状态 |
|---------|---------|---------|
| Windows 10 | 1903+ | ✅ 完全支持 |
| Windows 11 | 所有版本 | ✅ 完全支持 |
| Windows Server 2019 | 所有版本 | ✅ 支持 |
| Windows Server 2022 | 所有版本 | ✅ 支持 |
| macOS | 10.15+ | ⚠️ 部分支持（需调整路径） |
| Linux | Ubuntu 20.04+ | ⚠️ 部分支持（需调整部署脚本） |

### 硬件要求

| 组件 | 最低要求 | 推荐配置 |
|------|---------|---------|
| CPU | 双核 1.5GHz | 四核 2.0GHz+ |
| 内存 | 512 MB | 1 GB+ |
| 磁盘空间 | 100 MB | 500 MB+ |
| 网络 | 宽带连接 | 稳定的互联网连接 |

---

## Python 环境配置

### Python 版本要求

- **最低版本**: Python 3.9
- **推荐版本**: Python 3.11 或 Python 3.12
- **不支持**: Python 3.8 及以下版本

### 安装 Python

#### Windows 安装步骤

1. 访问 [Python 官网](https://www.python.org/downloads/)
2. 下载最新稳定版（推荐 Python 3.11+）
3. 运行安装程序
4. **重要**: 勾选 "Add Python to PATH"
5. 点击 "Install Now"

#### 验证安装

```bash
# 检查 Python 版本
python --version

# 或
python3 --version

# 检查 pip
pip --version
```

### 虚拟环境配置

**强烈建议**使用虚拟环境来隔离项目依赖。

#### 创建虚拟环境

```bash
# 在项目根目录执行
cd C:\Users\user\Desktop\openclaw-mcp-server

# 创建虚拟环境
python -m venv venv
```

#### 激活虚拟环境

**Windows:**
```bash
# CMD
venv\Scripts\activate

# PowerShell
venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

#### 验证虚拟环境

激活后，命令行前缀应显示 `(venv)`：
```bash
(venv) C:\Users\user\Desktop\openclaw-mcp-server>
```

---

## 依赖安装

### 核心依赖

项目依赖定义在 `requirements.txt` 中：

```
mcp>=1.0.0
websockets>=12.0
python-dotenv>=1.0.0
```

### 依赖说明

| 包名 | 最低版本 | 用途 | 文档 |
|------|---------|------|------|
| `mcp` | 1.0.0 | Model Context Protocol 实现 | [MCP 文档](https://modelcontextprotocol.io/) |
| `websockets` | 12.0 | WebSocket 客户端/服务器 | [websockets 文档](https://websockets.readthedocs.io/) |
| `python-dotenv` | 1.0.0 | 从 .env 文件加载环境变量 | [python-dotenv 文档](https://pypi.org/project/python-dotenv/) |

### 安装命令

```bash
# 确保已激活虚拟环境
pip install -r requirements.txt

# 或手动安装
pip install mcp>=1.0.0 websockets>=12.0 python-dotenv>=1.0.0
```

### 验证依赖安装

```bash
# 列出已安装的包
pip list

# 检查特定包
pip show mcp
pip show websockets
pip show python-dotenv
```

### 依赖树

```
openclaw-mcp-server
├── mcp (>=1.0.0)
│   └── (MCP 协议核心库)
├── websockets (>=12.0)
│   └── (WebSocket 通信库)
└── python-dotenv (>=1.0.0)
    └── (环境变量管理)
```

---

## 环境变量配置

### .env 文件结构

在项目根目录创建 `.env` 文件：

```env
# OpenClaw MCP Token
# 从 wss://api.xiaozhi.me/mcp/?token=xxx 中获取
OPENCLAW_TOKEN=your_token_here
```

### 获取 Token

1. **访问小智 MCP 平台**
   - 登录到小智 MCP 管理控制台

2. **创建 Agent**
   - 创建新的 Agent 或选择现有 Agent

3. **获取 WebSocket URL**
   - 复制类似以下的 URL：
     ```
     wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1NiIs...
     ```

4. **提取 Token**
   - 提取 `token=` 后面的完整字符串
   - 填入 `.env` 文件的 `OPENCLAW_TOKEN` 变量

### 环境变量优先级

环境变量加载优先级（从高到低）：

1. 系统环境变量
2. `.env` 文件中的变量
3. 默认值（如果代码中定义）

### 验证环境变量

```bash
# Windows CMD
echo %OPENCLAW_TOKEN%

# PowerShell
echo $env:OPENCLAW_TOKEN

# Linux/macOS
echo $OPENCLAW_TOKEN
```

### Python 中访问

```python
import os
from dotenv import load_dotenv

load_dotenv()  # 加载 .env 文件

token = os.getenv("OPENCLAW_TOKEN")
if not token:
    raise ValueError("请设置 OPENCLAW_TOKEN 环境变量")
```

---

## 网络要求

### 出站连接

服务器需要能够访问以下外部端点：

| 端点 | 协议 | 端口 | 用途 |
|------|------|------|------|
| `api.xiaozhi.me` | WSS (WebSocket Secure) | 443 | 连接小智 MCP 服务器 |
| `pypi.org` | HTTPS | 443 | 下载 Python 包（仅安装时） |

### 防火墙配置

**Windows 防火墙:**

1. 打开 "Windows Defender 防火墙"
2. 点击 "高级设置"
3. 创建出站规则：
   - 程序：`python.exe`（虚拟环境中的）
   - 协议：TCP
   - 远程端口：443
   - 操作：允许

### 代理配置

如果使用代理服务器：

```bash
# 设置代理环境变量
set HTTP_PROXY=http://proxy.server:port
set HTTPS_PROXY=http://proxy.server:port

# 或在 .env 中添加
HTTP_PROXY=http://proxy.server:port
HTTPS_PROXY=http://proxy.server:port
```

---

## 故障排除

### 问题 1: Python 版本过低

**错误信息:**
```
SyntaxError: invalid syntax
```

**解决方案:**
```bash
# 检查版本
python --version

# 如果低于 3.9，请升级 Python
# 访问 https://www.python.org/downloads/
```

### 问题 2: pip 未找到

**错误信息:**
```
'pip' is not recognized as an internal or external command
```

**解决方案:**
```bash
# 使用 python -m pip
python -m pip install -r requirements.txt

# 或添加 Python 到 PATH
# 重新运行 Python 安装程序，勾选 "Add to PATH"
```

### 问题 3: 依赖安装失败

**错误信息:**
```
ERROR: Could not find a version that satisfies the requirement...
```

**解决方案:**
```bash
# 升级 pip
python -m pip install --upgrade pip

# 清除缓存重试
pip cache purge
pip install -r requirements.txt --no-cache-dir

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题 4: WebSocket 连接超时

**错误信息:**
```
websockets.exceptions.InvalidStatusCode: server rejected WebSocket connection
```

**解决方案:**
1. 检查 Token 是否有效
2. 检查网络连接
3. 检查防火墙设置
4. 验证代理配置（如使用）

### 问题 5: .env 文件未加载

**错误信息:**
```
ValueError: 请设置 OPENCLAW_TOKEN 环境变量
```

**解决方案:**
```bash
# 确认 .env 文件存在
dir .env

# 确认文件格式（应为纯文本，无 .txt 扩展名）
# 在记事本中打开 .env 检查

# 尝试手动设置环境变量
set OPENCLAW_TOKEN=your_token
```

### 问题 6: 虚拟环境问题

**错误信息:**
```
The venv module is not available
```

**解决方案:**
```bash
# 某些 Python 发行版需要单独安装 venv
# Ubuntu/Debian:
sudo apt-get install python3-venv

# 或使用 conda
conda create -n openclaw python=3.11
conda activate openclaw
```

---

## 快速检查脚本

创建 `check_env.py` 来验证环境配置：

```python
#!/usr/bin/env python3
"""环境检查脚本"""

import sys
import os
from dotenv import load_dotenv

print("=" * 50)
print("OpenClaw-xiaozhi MCP Server 环境检查")
print("=" * 50)

# Python 版本
print(f"\n✅ Python 版本：{sys.version}")
if sys.version_info < (3, 9):
    print("⚠️  警告：Python 3.9+ 是必需的")

# 依赖检查
try:
    import mcp
    print(f"✅ mcp: v{mcp.__version__ if hasattr(mcp, '__version__') else 'unknown'}")
except ImportError:
    print("❌ mcp: 未安装")

try:
    import websockets
    print(f"✅ websockets: v{websockets.__version__}")
except ImportError:
    print("❌ websockets: 未安装")

try:
    import dotenv
    print(f"✅ python-dotenv: v{dotenv.__version__}")
except ImportError:
    print("❌ python-dotenv: 未安装")

# 环境变量检查
load_dotenv()
token = os.getenv("OPENCLAW_TOKEN")
if token:
    print(f"✅ OPENCLAW_TOKEN: 已设置 ({len(token)} 字符)")
else:
    print("❌ OPENCLAW_TOKEN: 未设置")

print("\n" + "=" * 50)
```

运行检查：
```bash
python check_env.py
```

---

## 参考资源

- [Python 官方文档](https://docs.python.org/3/)
- [MCP 协议文档](https://modelcontextprotocol.io/)
- [websockets 文档](https://websockets.readthedocs.io/)
- [python-dotenv 文档](https://pypi.org/project/python-dotenv/)

---

**最后更新**: 2026 年 3 月 14 日