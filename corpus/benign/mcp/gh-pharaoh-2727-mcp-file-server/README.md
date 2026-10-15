# 文件系统 MCP Server

一个基于 [FastMCP](https://github.com/jlowin/fastmcp) 的本地文件系统 MCP Server。

**让 AI 能够安全地读、写、检索你指定的目录** —— 所有操作都被限制在一个白名单根目录内，越界请求会被拒绝。

---

## 为什么做这个

大语言模型本身读不了你磁盘上的文件。要让 Agent 操作本地文件，必须给它工具。

但**给 AI 一个能读写文件的工具，本身就是个危险动作**：

- `read_file("../../Windows/System32/drivers/etc/hosts")` —— 读系统文件
- `write_file("../../important.txt", "")` —— 覆盖任意文件
- `search_content(".", "password")` —— 扫出你的密钥

所以这个项目的重点不是"能读写文件"，而是**"在能读写文件的同时，保证它跑不出去"**。

## 提供的能力

| 工具 | 参数 | 作用 |
|---|---|---|
| `read_file` | `path` | 读取文件内容 |
| `list_dir` | `path` | 列出目录内容（区分目录/文件，目录在前） |
| `write_file` | `path`, `content` | 写入新文件（已存在则拒绝，不覆盖） |
| `search_content` | `path`, `keyword` | 递归搜索文件内容，返回 `文件:行号: 内容` |

`path` 一律**相对沙箱根目录**，用 `/` 分隔。

### 一次完整调用长什么样

对 Host（Claude Desktop / 其他 MCP 客户端）说：

> 看看 sandbox 里有什么，把 notes.txt 的内容读出来，然后新建一个 backup.txt 把内容抄进去。

Agent 会依次调用：

```
list_dir(".")                     → 目录: sub
                                    文件: notes.txt
                                    文件: second.txt
read_file("notes.txt")            → 这是一份测试文件。...
write_file("backup.txt", "这是一份测试文件。...")  → 成功：已写入文件 backup.txt。
```

---

## 🔒 安全设计（核心部分）

### 白名单根目录

`BASE_DIR` 是这个 Server 的**权限边界**。所有路径操作都必须落在这个目录内。

```python
BASE_DIR = Path(__file__).resolve().parent / "sandbox"
```

**用 `__file__` 锚定，而不是相对路径** —— 否则同一个脚本在 PyCharm 里跑和命令行跑，`cwd` 不同，`BASE_DIR` 就指向不同地方。

**`sandbox` 放在脚本同级目录**，这样整个项目可以整体搬走，不用改任何路径。

### 四步校验

```python
def _safe(path: str) -> Path:
    target = (BASE_DIR / path).resolve()      # ① 拼接 + ② 展开
    if not target.is_relative_to(BASE_DIR):   # ③ 判断
        raise ValueError(f"Path escapes sandbox: {path}")
    return target                              # ④ 交付
```

| 步骤 | 做什么 |
|---|---|
| ① `BASE_DIR / path` | 把用户输入接到根目录下 |
| ② `.resolve()` | 把 `..`、`.`、符号链接展开成**真实路径** |
| ③ `.is_relative_to()` | 判断真实路径是否仍在根目录内 |
| ④ `return` / `raise` | 在里面就交付，不在就拒绝 |

### ⚠️ 顺序不能反 —— 有实测证据

**`is_relative_to()` 只比较路径段，不帮你展开 `..`。**

```
攻击路径            : ...\sandbox\..\..\secret.txt
不 resolve 直接判断 : True      ← 放行了，防护完全失效
resolve 后判断      : False     ← 拦住了
```

原因：`sandbox\..\..\secret.txt` 在字面上"以 sandbox 开头"，所以 `is_relative_to()` 认为是子路径。

**所以必须先算清真实落点，再判断范围。**

### ⚠️ 也不能自己写字符串前缀判断

```python
if ".." in path: ...                          # ❌ 符号链接 / Windows 短名可绕过
if str(target).startswith(str(BASE_DIR)): ...  # ❌ 见下
```

实测：

```
Path('C:/ab').is_relative_to(Path('C:/a'))    →  False   ✅ 正确
'C:/ab'.startswith('C:/a')                     →  True    ❌ 误判
```

`C:/ab` 是一个叫 `ab` 的目录，**不是 `a` 下的 `b`**。字符串前缀会把它们混淆。

### 为什么抽成独立函数

四个工具都需要同一套校验。抽出来之后，**新增工具时忘了调用会非常显眼**（因为每个函数开头都长一样）。抄在每个函数里，迟早漏一个。

---

## 错误处理设计

这个 Server 的"用户"是模型，所以错误信息不是给人看的日志，而是**给模型的指令**。

### 分界线

| 错误类型 | 处理方式 | 原因 |
|---|---|---|
| **安全类**（越界） | `raise ValueError` | 语义上是"程序拒绝执行"，也便于留告警痕迹 |
| **业务类**（不存在 / 是目录 / 编码错） | `return` 错误字符串 | 属于"正常失败"，模型应该读懂并换路径重试 |

**异常消息用 ASCII（英文）** —— 中文错误信息在 Windows 终端会乱码，模型可能也收到乱码，那就谈不上自愈了。

### 错误信息必须带"下一步动作"

```
错误：文件不存在（nope.txt）。可以先调用 list_dir 看看有什么。
错误：notes.txt 是文件不是目录，请用 read_file。
错误：路径为空。请传入相对于 sandbox 根目录的路径（例如 notes.txt）。
```

每条都告诉模型**接下来该怎么做**，而不只是"失败了"。

对比反例：

```
错误：无法写入文件 deep/a.txt。      ← 模型不知道是权限、磁盘还是路径问题
```

---

## 快速开始

### 环境

- Python ≥ 3.10（开发环境为 3.13）
- `fastmcp >= 4.0`

```bash
# 方式一：只装运行时依赖
pip install fastmcp

# 方式二：按 pyproject.toml 的声明安装（依赖 + 本项目）
pip install -e .
```

**方式二的好处**：依赖清单写在 `pyproject.toml` 里，换台机器一条命令就能装齐，
而且以后加依赖只改那一处。

### 运行

```bash
# 直接运行（stdio，供 Host 调用）
python agent_mcp.py

# 用 CLI 查看它暴露了哪些工具
fastmcp list agent_mcp.py

# 命令行直接调一个工具
fastmcp call agent_mcp.py read_file path=notes.txt
```

### 验证

```bash
# 正常读取
fastmcp call agent_mcp.py read_file path=notes.txt

# 越界 —— 应该被拒绝
fastmcp call agent_mcp.py read_file path=../secret.txt
fastmcp call agent_mcp.py read_file path=C:/Windows/win.ini

# 业务错误 —— 应该返回可读的提示
fastmcp call agent_mcp.py read_file path=nope.txt
fastmcp call agent_mcp.py read_file path=.

# 空路径
fastmcp call agent_mcp.py read_file path=

# 搜索（递归 + 行号）
fastmcp call agent_mcp.py search_content path=. keyword=hello
```

**判据**：正常路径返回内容；两条越界返回 `Path escapes sandbox`；其余返回中文友好提示。

### 接进 Host

在 Host 的 MCP 配置里加上：

```json
{
  "mcpServers": {
    "file-server": {
      "command": "python",
      "args": ["/绝对路径/agent_mcp.py"]
    }
  }
}
```

> ⚠️ `command` 必须是**装了 fastmcp 的那个 Python** 的绝对路径，不能只写 `python`。多环境机器上写错会出现 `ModuleNotFoundError: No module named 'fastmcp'`。

---

## 目录结构

```
mcp-file-server/
├── agent_mcp.py       # Server 本体（四个工具 + _safe）
├── README.md
├── TEST-CASES.md      # 测试样本清单 + 分场景测试命令 + 问题记录
├── pyproject.toml
├── .gitignore
├── LICENSE
└── sandbox/           # 沙箱根目录 = BASE_DIR，模型只能在这里操作
    ├── notes.txt / second.txt      # 普通文本
    ├── empty.txt / blank.txt       # 0 字节 / 纯空白
    ├── gbk.txt / bom.txt           # GBK 编码 / UTF-8 BOM
    ├── crlf.txt                    # CRLF 换行
    ├── bin.dat                     # 假二进制 → 验证"读不了就跳过"
    ├── long.txt                    # needle 命中 60 行 → 验证结果上限
    ├── hello_big.txt               # 190 KB → 验证大文件截断
    ├── huge_line.txt               # 单行 50 KB → 验证单条截断
    ├── edge_20000.txt / edge_20001.txt   # 长度上限的边界值
    ├── no_extension / my notes.txt / 中文文件.txt
    ├── empty_dir/                  # 空目录 → 验证「（空目录）」
    ├── docs/ logs/                 # 子目录，验证递归
    ├── data/2026/09/report/         # 5 层深
    └── sub/deep/c.txt              # 关键词在第 2、4 行 → 验证递归 + 行号
```

> ⚠️ **`empty_dir/` 是空目录，而 Git 不跟踪空目录** —— clone 下来它不存在。
> 要跑 `list_dir path=empty_dir` 这条测试，先手动创建：`mkdir sandbox\empty_dir`。

**每个样本具体测哪个分支，见 [`TEST-CASES.md`](TEST-CASES.md) 的「一、样本清单」。**

**`sandbox` 与脚本同级** —— `BASE_DIR = Path(__file__).resolve().parent / "sandbox"`。
整个目录可以随意搬动/改名，不需要改代码。

---

## 已知限制

| 限制 | 说明 |
|---|---|
| **不支持覆盖写入** | 文件已存在时 `write_file` 直接拒绝。要改内容得先手动删掉 |
| **不自动创建父目录** | 写到不存在的目录会报错，不支持 `mkdir -p` 行为 |
| **只支持 UTF-8 文本** | 读写都按 UTF-8 处理，二进制文件读不了（搜索时会跳过） |
| **搜索有结果上限** | 默认 50 条（`MAX_RESULTS`），超出会提示缩小范围 |
| **读取有长度上限** | 超过 20000 字符（`MAX_CHARS`）只返回前 8000 字符（`HEAD_CHARS`），并在开头注明总长度 |
| **列目录只做一层** | 不递归 —— 递归遇到软链接可能刷出几十万行 |

### 后续计划

- [ ] `write_file` 增加 `overwrite` 参数，支持显式覆盖
- [ ] 搜索结果支持大小写不敏感选项
- [ ] 部署为远程 MCP Server（HTTP/SSE）
- [ ] 补充自动化测试

---

## 开发笔记

### 踩过的坑（部分）

| 坑 | 现象 |
|---|---|
| `Path("/sandbox")` 不是相对路径 | Windows 上解析成 `C:\sandbox`，直接废掉整个工具 |
| `read_text()` 对目录 | 抛 `PermissionError`（Windows），不是 `IsADirectoryError` |
| `.is_dir()` 返回 `False` ≠ 是文件 | 不存在的路径 `is_dir()` 也是 `False`，所以两道检查顺序不能反 |
| `Path("")` 等于 `Path(".")` | 空路径会定位到根目录本身，被误判为"是目录" |
| `"" in "任意字符串"` 恒为 `True` | 空关键词会匹配所有行，必须挡空 |
| `rglob("*")` 会带出目录 | 必须 `is_file()` 过滤，否则拿目录去 `read_text()` |
| `break` 只跳出一层循环 | 结果上限的内外两层都要管 |

### 测试方法

**验证一个工具不是"跑一次看能不能用"，而是"把每一种失败都跑一遍"。**

以 `read_file` 为例，测试矩阵：

| 输入 | 期望 |
|---|---|
| 正常文件名 | 返回内容 |
| `../secret.txt` | 越界拦截 |
| `C:/Windows/win.ini` | 越界拦截（绝对路径） |
| 不存在的文件 | 友好提示 |
| `.`（目录） | 友好提示 + 建议用 list_dir |
| `""`（空字符串） | 友好提示 |
| `"   "`（全空格） | 友好提示 |
| 大文件（超过 20000 字符） | 截断到前 8000 字符 + 注明总长度 |
| **正好卡在上限的文件** | **不截断**（边界值） |

其中**空字符串、全空格、绝对路径**这三条都是跑测试才发现的，写代码时想不到。

**另外三条经验**：

1. **成功路径必须第一个测。** 失败路径再多也证明不了核心功能是好的 —— 曾有一版四个失败路径全过，唯一失败的是"应该成功"那条，因为 bug 藏在唯一没被拦的路径上。
2. **测试样本本身要先验证。** 要测"二进制文件被跳过"，得先确认那个文件真的会抛 `UnicodeDecodeError`；否则测试"通过"了，实际什么都没测到。
3. **边界值要成对测，造完立刻断言。** `>` 和 `>=` 差一个字行为就不同，只测"远大于上限"的输入两种写法都通过 —— 必须拿**正好卡在两侧**的输入才验得出来。而造这类样本时（如"20001 字符"），**先 `assert len(s) == 20001` 再拿去测**：曾用 `'0' * (n // 10)` 造样本，整除丢余数导致两个文件一样大，边界根本没测到。

---

## License

MIT
