# my-mcp-ssh
[![EN doc](https://img.shields.io/badge/document-English-blue.svg)](README.md)
[![CN doc](https://img.shields.io/badge/文档-中文版-blue.svg)](README_zh_CN.md)

这是一个基于 Model Context Protocol (MCP) 的 SSH 连接工具，允许大语言模型通过 MCP 协议安全地与远程服务器进行 SSH 连接和文件操作。

## 功能特性

- SSH 连接管理：连接到远程 SSH 服务器
- 命令执行：在远程服务器上执行命令
- 文件传输：上传和下载文件
- 会话管理：维护和关闭 SSH 会话

## 安装
### 依赖
- Python >= 3.12
- uv包管理器

```bash
# 下载项目代码
git clone https://github.com/ffpy/my-mcp-ssh.git

# 进入项目目录
cd my-mcp-ssh

# 安装依赖
uv sync
```

## 用法
### 在客户端中配置
```json
{
  "mcpServers": {
    "my-mcp-ssh": {
      "command": "uv",
      "args": [
        "--directory",
        "<your_path>/my-mcp-ssh",
        "run",
        "src/main.py"
      ],
      "env": {}
    }
  }
}
```

### 环境变量

#### SSH 连接默认值（可选功能）

环境变量为 SSH 连接提供默认值，适用于频繁连接同一服务器或自动化环境：

- `SSH_HOST`: SSH 服务器主机名或 IP 地址
- `SSH_PORT`: SSH 服务器端口
- `SSH_USERNAME`: SSH 用户名
- `SSH_PASSWORD`: SSH 密码（如果使用密码认证）
- `SSH_KEY_PATH`: SSH 私钥文件路径（如果使用密钥认证）
- `SSH_KEY_PASSPHRASE`: SSH 私钥密码（如果需要）

**何时使用 SSH 环境变量：**
- **重复连接**：多次连接同一服务器时
- **CI/CD 流水线**：自动化部署脚本中
- **开发环境**：为常用服务器设置默认值
- **容器部署**：无需修改代码即可配置默认值

**注意**：传递给 `connect` 工具的参数始终会覆盖环境变量。

#### 服务器配置

其他服务器行为配置：

- `SESSION_TIMEOUT`: 会话超时时间（分钟），默认 30 分钟
- `MAX_OUTPUT_LENGTH`: 命令输出最大长度（字符数），默认 5000 字符

### SSH 凭据文件

为了更好的安全性，你可以将 SSH 凭据存储在本地配置文件中，而不是以参数形式传递密码。

1. 复制示例文件：
```bash
cp ssh-credentials.json.example ssh-credentials.json
```

2. 编辑 `ssh-credentials.json` 填入你的实际凭据：
```json
{
  "root@192.168.1.100": "your_password",
  "admin@web-[0-9].example.com": "web_password",
  "deploy@server-{dev,test,staging}.company.com": "deploy_password",
  "admin@*.internal.network": "internal_password"
}
```

**支持的通配符模式：**
- `*` - 匹配任意字符
- `?` - 匹配单个字符
- `[0-9]` - 匹配任意数字
- `{dev,test,staging}` - 匹配列出的任意选项

**认证优先级顺序：**
1. 传递给 connect 工具的参数（`password`, `key_path`）
2. 凭据文件中的精确匹配（`username@host`）
3. 凭据文件中的模式匹配（通配符）
4. 环境变量密码（`SSH_PASSWORD`）
5. 环境变量密钥（`SSH_KEY_PATH`）
6. 默认SSH密钥（`~/.ssh/id_rsa` 如果存在）

**安全特性：**
- 文件权限自动设置为 600（仅所有者可读写）
- 文件已添加到 .gitignore 防止意外提交

**注意：**
- 凭据文件修改后立即生效，无需重启服务器
- 每次连接时都会重新读取文件

## 工具列表

### connect

连接到SSH服务器

**参数：**
- `host`: SSH服务器主机名或IP地址（可选）
- `port`: SSH服务器端口（可选，默认22）
- `username`: SSH用户名（可选）
- `password`: SSH密码认证（可选）
- `key_path`: SSH私钥文件路径认证（可选）
- `key_passphrase`: SSH私钥密码（如需要，可选）

### disconnect

断开SSH连接

**参数：**
- `session_id`: 要断开连接的会话ID

### list_sessions

列出所有活动SSH会话

**参数：**
- 无

### execute

在SSH服务器上执行命令

**参数：**
- `session_id`: 会话ID
- `command`: 要执行的命令
- `stdin`: 提供给命令的输入字符串，默认为空
- `timeout`: 命令超时时间（秒），默认为60秒

### upload

上传文件到SSH服务器

**参数：**
- `session_id`: 会话ID
- `local_path`: 本地文件路径
- `remote_path`: 远程文件路径

### download

从SSH服务器下载文件

**参数：**
- `session_id`: 会话ID
- `remote_path`: 远程文件路径
- `local_path`: 本地文件路径

## 调试
执行 `./inspector.sh` 进行在线调试

## License
my-mcp-ssh is licensed under the Apache License, Version 2.0