# FSDB MCP 服务器

一个用于读取和查询 FSDB (Fast Signal Database) 波形文件的 Model Context Protocol (MCP) 服务器。该服务器通过 MCP 协议提供对 FSDB 文件的编程访问，使 AI 助手和其他客户端能够查询波形数据、信号、scope 和值变化。

## 特性

- **打开和管理 FSDB 文件** - 打开、关闭和获取 FSDB 波形文件信息
- **浏览层次结构** - 导航 scope 层次结构并列出信号
- **搜索功能** - 按名称模式在层次结构中搜索信号和 scope
- **查询信号** - 获取详细的信号信息，包括范围、类型和属性
- **读取波形数据** - 提取特定时间的信号值或获取时间范围内的值变化
- **多种格式支持** - 以二进制、十进制、十六进制或实数格式查看值
- **智能限制** - 自动截断大型结果以防止内存问题（可配置）

## 前置要求

- **Python 3.10 或更高版本** (MCP SDK 所需)
- **Synopsys Verdi** 带 NPI (Native Programming Interface) 支持
- **VERDI_HOME** 环境变量设置为 Verdi 安装目录
- **pynpi** 库（Verdi 自带）
- **有效的 Verdi 许可证**

> **注意**: MCP SDK 需要 Python 3.10 或更高版本。

## 安装

详细安装说明请参见 [INSTALL.md](INSTALL.md)。

### 快速开始

1. **设置环境：**

```bash
export VERDI_HOME=/path/to/verdi
export LD_LIBRARY_PATH=$VERDI_HOME/share/NPI/lib/linux64:$VERDI_HOME/platform/linux64/bin:$LD_LIBRARY_PATH
```

2. **创建并激活虚拟环境（Python 3.10+）：**

```bash
python3.10 -m venv venv
source venv/bin/activate
```

3. **安装依赖：**

```bash
pip install --upgrade pip
pip install mcp
```

4. **测试安装：**

```bash
python test_fsdb.py
```

## 使用

### 运行服务器

启动 MCP 服务器：

```bash
python server.py
```

服务器通过 stdin/stdout 使用 MCP 协议进行通信。

### 可用工具

服务器提供以下工具：

#### 1. `fsdb_is_fsdb`
检查文件是否为有效的 FSDB 文件。

**参数：**
- `path` (string): 要检查的文件路径

#### 2. `fsdb_open`
打开 FSDB 波形文件。

**参数：**
- `path` (string): FSDB 文件路径

**返回：** 文件信息，包括时间范围、版本和属性

#### 3. `fsdb_close`
关闭已打开的 FSDB 文件。

**参数：**
- `path` (string): 要关闭的 FSDB 文件路径

#### 4. `fsdb_get_info`
获取已打开 FSDB 文件的详细信息。

**参数：**
- `path` (string): FSDB 文件路径

**返回：** 文件元数据，包括：
- 时间范围（min_time, max_time）
- 时间单位
- 版本和仿真日期
- 标志（has_glitch, has_assertion 等）

#### 5. `fsdb_list_scopes`
列出 FSDB 文件层次结构中的 scope。

**参数：**
- `path` (string): FSDB 文件路径
- `scope_path` (string, 可选): 要列出子 scope 的父 scope 路径

**返回：** scope 列表，包含 name、full_name、def_name 和 type

#### 6. `fsdb_list_signals`
列出 scope 中的信号。

**参数：**
- `path` (string): FSDB 文件路径
- `scope_path` (string, 可选): 要列出信号的 scope 路径

**返回：** 信号列表及其属性

#### 7. `fsdb_get_signal_info`
获取信号的详细信息。

**参数：**
- `path` (string): FSDB 文件路径
- `signal_path` (string): 完整信号路径（例如 "top.module1.signal_name"）

**返回：** 信号属性，包括：
- 名称和完整名称
- 类型信息（is_real, is_string 等）
- 范围信息（left_range, right_range, range_size）
- 方向和其他属性

#### 8. `fsdb_get_signal_value`
获取特定时间的信号值。

**参数：**
- `path` (string): FSDB 文件路径
- `signal_path` (string): 完整信号路径
- `time` (integer): 要查询的时间点
- `format` (string, 可选): 值格式 - "bin"、"dec"、"hex" 或 "real"（默认："hex"）

**返回：** 指定时间的信号值

#### 9. `fsdb_get_signal_changes`
获取时间范围内的信号值变化。

**参数：**
- `path` (string): FSDB 文件路径
- `signal_path` (string): 完整信号路径
- `start_time` (integer): 开始时间
- `end_time` (integer): 结束时间
- `format` (string, 可选): 值格式 - "bin"、"dec"、"hex" 或 "real"（默认："hex"）

**返回：** 值变化列表，包含时间和值

#### 10. `fsdb_search`
在 FSDB 文件中按名称模式搜索信号和 scope。

**参数：**
- `path` (string): FSDB 文件路径
- `pattern` (string): 搜索模式（不区分大小写的子串匹配）
- `search_type` (string, 可选): 要搜索的项目类型 - "signals"、"scopes" 或 "all"（默认："all"）
- `scope_path` (string, 可选): 限制搜索的 scope 路径（例如 "top.module1"）。如果未提供，则搜索整个层次结构。

**返回：** 包含匹配的信号和/或 scope 的搜索结果

**示例：**
```json
{
  "path": "/path/to/waveform.fsdb",
  "pattern": "clk",
  "search_type": "signals",
  "scope_path": "tb_top"
}
```

### 资源

服务器将已打开的 FSDB 文件作为资源暴露，URI 方案为 `fsdb://`。每个打开的文件都可以作为资源读取，以获取其信息和顶层 scope。

## 示例工作流程

1. **检查文件是否为 FSDB：**
```json
{
  "tool": "fsdb_is_fsdb",
  "arguments": {
    "path": "waveform.fsdb"
  }
}
```

2. **打开文件：**
```json
{
  "tool": "fsdb_open",
  "arguments": {
    "path": "waveform.fsdb"
  }
}
```

3. **列出顶层 scope：**
```json
{
  "tool": "fsdb_list_scopes",
  "arguments": {
    "path": "waveform.fsdb"
  }
}
```

4. **列出 scope 中的信号：**
```json
{
  "tool": "fsdb_list_signals",
  "arguments": {
    "path": "waveform.fsdb",
    "scope_path": "tb_top"
  }
}
```

5. **获取信号值变化：**
```json
{
  "tool": "fsdb_get_signal_changes",
  "arguments": {
    "path": "waveform.fsdb",
    "signal_path": "tb_top.clk",
    "start_time": 0,
    "end_time": 1000,
    "format": "bin"
  }
}
```

6. **关闭文件：**
```json
{
  "tool": "fsdb_close",
  "arguments": {
    "path": "waveform.fsdb"
  }
}
```

## 配置 MCP 客户端

### Claude Desktop

编辑配置文件：
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

添加以下内容：

```json
{
  "mcpServers": {
    "fsdb": {
      "command": "~/work/fsdb-mcp/venv/bin/python",
      "args": ["~/work/fsdb-mcp/server.py"],
      "env": {
        "VERDI_HOME": "/opt/verdi",
        "LD_LIBRARY_PATH": "/opt/verdi/share/NPI/lib/linux64:/opt/verdi/platform/linux64/bin"
      }
    }
  }
}
```

或使用自动配置脚本：

```bash
./update_mcp_config.sh
```

## 架构

服务器构建于：
- **MCP (Model Context Protocol)**: 用于与 AI 助手的标准化通信
- **pynpi**: Synopsys NPI Python 绑定，用于 FSDB 访问
- **waveform.py**: 用于波形操作的高级 Python API

## 故障排除

### 问题："pynpi not available"

**解决方案**：
- 确保 VERDI_HOME 设置正确
- 检查 pynpi 库路径是否可访问
- 验证 LD_LIBRARY_PATH 包含 Verdi 库

### 问题："Failed to open FSDB file"

**解决方案**：
- 验证文件存在且可读
- 使用 `fsdb_is_fsdb` 检查文件是否为有效的 FSDB 格式
- 确保 Verdi 许可证可用

### 问题："Signal not found"

**解决方案**：
- 使用 `fsdb_list_signals` 查看可用信号
- 检查信号路径语法（使用点表示法："scope.signal"）
- 使用 `fsdb_list_scopes` 验证 scope 层次结构

## 限制

- 需要安装 Synopsys Verdi 和 NPI 支持
- 仅支持 FSDB 格式（不支持 VCD、EVCD 等）
- 性能取决于 FSDB 文件大小和查询复杂度
- 必须正确配置 VERDI_HOME 和 LD_LIBRARY_PATH

## 许可证

本项目使用 Synopsys Verdi NPI 库，受 Synopsys 许可条款约束。

## 贡献

欢迎贡献！请确保：
- 代码遵循现有风格
- 新工具有文档说明
- 错误处理全面
- 使用真实 FSDB 文件测试更改

## 支持

相关问题：
- **MCP 协议**: 参见 [MCP 文档](https://modelcontextprotocol.io)
- **FSDB/Verdi**: 联系 Synopsys 支持
- **本服务器**: 在仓库中提交 issue
