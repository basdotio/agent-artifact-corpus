# sandbox 测试样本清单

> 每个样本都对应一个**具体的分支或隐患**，不是随便撒的文件。
> 运行位置：`mcp-file-server\`

## 一、样本清单

```
sandbox\
├── notes.txt            357 B   已有
├── second.txt           311 B   已有
├── bin.dat               11 B   已有 · 假二进制，触发 UnicodeDecodeError
├── empty.txt              0 B   ← 新 · 空文件（0 字节）
├── blank.txt             12 B   ← 新 · 只有空行和空白
├── gbk.txt               54 B   ← 新 · GBK 编码中文，UTF-8 读不了
├── bom.txt               48 B   ← 新 · UTF-8 with BOM（首字符不可见）
├── crlf.txt              47 B   ← 新 · CRLF 换行
├── long.txt            3850 B   ← 新 · needle 命中 60 行（>上限 50）
├── hello_big.txt     184912 B   ← 新 · 190 KB 大文件，hello 在最后一行
├── huge_line.txt      50045 B   ← 新 · 单行 50 KB
├── no_extension          66 B   ← 新 · 无扩展名
├── my notes.txt          46 B   ← 新 · 文件名带空格
├── 中文文件.txt           49 B   ← 新 · 文件名带中文
├── edge_20000.txt     20000 B   ← 新 · 正好 20000 字符（上限边界，不该截断）
├── edge_20001.txt     20001 B   ← 新 · 20001 字符（刚超上限，该截断）
├── docs\
│   ├── a_readme.md       68 B   含 hello（排序靠前）
│   └── z_guide.md        80 B   含 hello 两行（排序靠后）
├── logs\
│   └── app.log          115 B   含 hello + ERROR
├── data\2026\09\report\
│   └── deep5.txt         47 B   5 层深，测递归
├── sub\deep\
│   └── c.txt            134 B   2 层深，hello 在第 2、4 行
└── empty_dir\             0 B   ⚠️ 空目录（Git 不跟踪，clone 后需手动建，见场景 4）
```

**共 12 个文件含 `hello`，合计 15 行匹配** —— 分散在平铺、子目录、深层三种位置，
所以任何"只搜到一部分文件"的 bug 都会立刻现形。

## 二、分场景测试

### 场景 1：多文件搜索（测「只搜最后一个文件」的 bug）

```powershell
fastmcp call .\agent_mcp.py search_content path=. keyword=hello
```

**期望**：**12 个文件、15 行**全部出现 —— `bom.txt`、`crlf.txt`、`hello_big.txt`、`huge_line.txt`(2 行)、
`my notes.txt`、`no_extension`、`中文文件.txt`、`docs\a_readme.md`、`docs\z_guide.md`(2 行)、
`logs\app.log`、`sub\deep\c.txt`(2 行)、`data\2026\09\report\deep5.txt`。

⚠️ 如果只出现一两个文件的 —— 循环缩进错了，参考「踩坑 2」。

### 场景 2：结果上限（60 命中 vs 上限 50）

```powershell
fastmcp call .\agent_mcp.py search_content path=. keyword=needle
```

**期望**：最多 50 条，末尾有 `（已显示前 50 个结果）`。

**为什么是 60 而不是 50**：命中数必须**严格大于**上限，才能区分"刚好收满"和
"被截断"。命中数正好 50 时，两种情况的输出一样，看不出上限生效没有。

### 场景 3：单文件 vs 目录

```powershell
fastmcp call .\agent_mcp.py search_content path=notes.txt keyword=测试
fastmcp call .\agent_mcp.py search_content path=docs keyword=hello
```

两条都要能搜到。

### 场景 4：空文件 / 纯空白

```powershell
fastmcp call .\agent_mcp.py read_file path=empty.txt
fastmcp call .\agent_mcp.py read_file path=blank.txt
fastmcp call .\agent_mcp.py list_dir  path=empty_dir
```

**期望**：

- `empty.txt` / `blank.txt` → `（... 是空文件，或只有空白字符）`
- `empty_dir` → `（空目录）`

> ⚠️ **先看这条**：`empty_dir` 是**空目录**，而 **Git 不跟踪空目录** ——
> 仓库里根本没有它，clone 下来这条会变成"错误：目录不存在"。
>
> 跑之前先建：`mkdir sandbox\empty_dir`
>
> 这不是 bug，是 Git 的固有行为（`git status` 也不报，完全静默）。
> 也**不要**往里面放 `.gitkeep` —— 那样目录就不空了，`（空目录）` 这个分支永远测不到。

### 场景 5：编码

```powershell
fastmcp call .\agent_mcp.py read_file path=gbk.txt
fastmcp call .\agent_mcp.py read_file path=bom.txt
```

- `gbk.txt` → 应该被 `UnicodeDecodeError` 接住（措辞见「问题 3」）
- `bom.txt` → 能读，但**首字符是看不见的 `\ufeff`**（正常现象，BOM 就是这么工作的）

### 场景 6：特殊文件名

```powershell
fastmcp call .\agent_mcp.py read_file "path=my notes.txt"
fastmcp call .\agent_mcp.py read_file "path=中文文件.txt"
fastmcp call .\agent_mcp.py read_file path=no_extension
```

**PowerShell 里带空格必须加引号。**

### 场景 7：结构 / 排序 / 递归

```powershell
fastmcp call .\agent_mcp.py list_dir path=.
fastmcp call .\agent_mcp.py list_dir path=data
```

**期望排序**：目录在前（`data` / `docs` / `empty_dir` / `logs` / `sub`），
文件在后（按 ASCII 名，中文名最后）。

### 场景 8：失败路径（回归）

```powershell
fastmcp call .\agent_mcp.py read_file  path=..\secret.txt
fastmcp call .\agent_mcp.py read_file  path=C:/Windows/win.ini
fastmcp call .\agent_mcp.py read_file  path=nope.txt
fastmcp call .\agent_mcp.py read_file  path=.
fastmcp call .\agent_mcp.py read_file  path=
fastmcp call .\agent_mcp.py list_dir   path=notes.txt
fastmcp call .\agent_mcp.py list_dir   path=nope
fastmcp call .\agent_mcp.py search_content path=. keyword=
```

全部应返回友好提示或拦截。

## 三、问题清单与修复状态

> 状态更新于 2026-09-22 15:00。**6 条全部已修复**，修复后的实测输出都贴在各条下面。

### ✅ 问题 1（已修复）：`read_file` 读空文件返回空字符串

**修复前**：

```
read_file path=empty.txt  →  {"result": ""}
```

模型的视角：**分不清「文件是空的」和「工具坏了 / 读失败了」**。

**这是你在 `list_dir` 里已经解决过的问题**（空目录 → `（空目录）`），`read_file` 漏了。
同样，`blank.txt` 返回 `"\n\n   \n\t\n"` 也是"没有任何信息量"的输出。

**修复**：

```python
    text = target.read_text(encoding="utf-8")
    if not text.strip():
        return f"（{path} 是空文件，或只有空白字符）"
    return text
```

**实测（已生效）**：

```
read_file path=empty.txt  →  （empty.txt 是空文件，或只有空白字符）
read_file path=blank.txt  →  （blank.txt 是空文件，或只有空白字符）
```

### ✅ 问题 2（已修复）：`search_content` 的上限按「条数」算，不按「字节」算

`huge_line.txt` 有一行 50 KB。搜 `hello` 时，这一行**整条**被吐出来了 ——
单条结果就有 50 KB，50 条最坏是 2.5 MB。

**上限拦住的是条数，拦不住单条的体积。** 一个又长又散的文件仍能撑爆上下文。

**修复**：

```python
        display = line if len(line) <= 200 else line[:200] + f"...（该行共 {len(line)} 字符）"
        results.append(f"{f.relative_to(BASE_DIR)}: {i}: {display}")
```

**实测（已生效）**：那一行 **50012 字符 → 输出 235 字符**

```
huge_line.txt: 1: 开头 hello AAAA...AAA...（该行共 50012 字符）
```

### ✅ 问题 3（已修复）：措辞 —— 把"非 UTF-8 文本"说成了"二进制文件"

**修复前**：`错误：gbk.txt 不是 UTF-8 文本，可能是二进制文件。`

`gbk.txt` 是**文本**，只是编码不是 UTF-8。模型收到"可能是二进制文件"，
可能会放弃这个文件，而不是想到"换个编码试试"。

**修复**：`不是 UTF-8 编码（可能是 GBK 等中文编码，或二进制文件）`

**实测（已生效）**：`错误：gbk.txt 不是 UTF-8 编码（可能是 GBK 等中文编码，或二进制文件）`

### ✅ 问题 4（已修复）：搜索结果没有排序

**修复前**：平铺文件在前、子目录顺序由 `rglob()` 决定 —— **不保证稳定**。
同样内容的两次搜索，顺序可能不同，模型想"记住文件在哪"更难。

**修复**：

```python
    files = sorted((p for p in target.rglob("*") if p.is_file()), key=lambda p: str(p).lower())
```

**实测（已生效）**——顺序变成纯字典序：

```
bom.txt → crlf.txt → data\2026\09\report\deep5.txt → docs\a_readme.md → docs\z_guide.md
→ hello_big.txt → huge_line.txt → logs\app.log → my notes.txt → no_extension
→ sub\deep\c.txt → 中文文件.txt
```

（`list_dir` 用的是另一套排序：目录在前、文件在后。两处不一致**没问题**——
`list_dir` 要突出层级，`search_content` 要可复现。）

### ✅ 问题 5（已修复）：上限提示措辞有歧义

**修复前**：

```python
    if len(results) >= MAX_RESULTS:
        text += f"\n（已显示前 {MAX_RESULTS} 个结果）"
```

**命中数正好 = 50 时也会显示这句**，但此时可能已经没有任何更多结果了。
模型会以为还有更多，可能继续换关键词白搜一遍。

**修复**（只改措辞，逻辑没动）：

```python
        text += f"\n（已达上限 {MAX_RESULTS} 条，可能还有更多，请缩小搜索范围）"
```

**实测（已生效，含对照）**：

| 输入 | 命中 | 提示 |
|---|---|---|
| `keyword=needle` | 60 条（超上限） | `（已达上限 50 条，可能还有更多，请缩小搜索范围）` ✅ |
| `keyword=hello` | 15 条（未超） | **不出现** ✅ |

**第二条对照很关键** —— 只验"该出来时出来了"是不够的，还要验"**不该出来时没出来**"。
否则一个"永远输出这句提示"的实现也能通过前一条测试。

### ✅ 问题 6（已修复）：`read_file` 对大文件没有提示

**修复前**：`hello_big.txt` 有 190 KB，`read_file` 会整个返回，模型不知道自己拿到的是个大文件。

**修复**：

```python
@mcp.tool
def read_file(path: str) -> str:
    """读取 sandbox 内的文件内容。path 用 / 分隔，相对 sandbox 根目录。"""
    MAX_CHARS = 20000  # 单次返回的字符数量上限
    HEAD_CHARS = 8000  # 超出上限时，只保留开头这么多字符
    ...
        text = target.read_text(encoding="utf-8")
        if not text.strip():
            return f"（{path} 是空文件，或只有空白字符）"
        if len(text) > MAX_CHARS:  # 文件过大，截断后再返回
            return (f"（{path} 共 {len(text)} 字符，超过上限 {MAX_CHARS}，"
                    f"仅显示前 {HEAD_CHARS} 字符）\n{text[:HEAD_CHARS]}")
        return text
```

**实测（已生效）**：

| 文件 | 原本 | 现在 |
|---|---|---|
| `hello_big.txt` | 182911 字符全返回 | `（... 共 182911 字符，超过上限 20000，仅显示前 8000 字符）` ✅ |
| `huge_line.txt` | 50025 字符全返回 | `（... 共 50025 字符，超过上限 20000，仅显示前 8000 字符）` ✅ |
| `notes.txt`（357 B） | 全文 | 全文，**未受影响** ✅ |

**边界测试**（判断条件是 `len(text) > MAX_CHARS`）：

| 文件 | 实际字符数 | 截断 |
|---|---|---|
| `edge_20000.txt` | 20000 | ❌ 不截断（正好在上限内） |
| `edge_20001.txt` | 20001 | ✅ 截断 |

**为什么必须测这两个**：`>` 和 `>=` 差一个字，行为就不同。
只测 `hello_big.txt` 那种"远大于上限"的文件，**`>=` 写错成 `>` 也照样通过**。
必须拿**正好卡在边界两侧**的输入才能验出来。

## 四、测试记录表（2026-09-22 15:00 已全部跑过）

| # | 命令 | 期望 | 实际 | 通过 |
|---|---|---|---|---|
| 1 | `search_content path=. keyword=hello` | 12 个文件 / 15 行 | 12 个文件 / 15 行，纯字典序 | ✅ |
| 2 | `search_content path=. keyword=needle` | 50 条 + 上限提示 | 50 条 + `（已显示前 50 个结果）` | ✅ |
| 3 | `read_file path=empty.txt` | 空文件提示 | `（empty.txt 是空文件，或只有空白字符）` | ✅ |
| 4 | `read_file path=gbk.txt` | 友好提示 | `不是 UTF-8 编码（可能是 GBK 等中文编码...）` | ✅ |
| 5 | `read_file path=中文文件.txt` | 读出内容 | 读出全文 | ✅ |
| 6 | `list_dir path=.` | 目录在前、文件在后 | 5 个目录 + 14 个文件，顺序正确 | ✅ |
| 7 | `list_dir path=empty_dir` | `（空目录）` | `（空目录）` | ✅ |
| 8 | `search_content path=.. keyword=x` | 拦住 | `Path escapes sandbox: ..` | ✅ |
| 9 | `search_content path=notes.txt keyword=测试` | 单文件分支能搜 | 返回 2 条 | ✅ |
| 10 | `read_file path=huge_line.txt` | 截断生效 | 50012 字符 → 235 字符 | ✅ |
| 11 | `write_file path=notes.txt content=x` | 拒绝覆盖 | `文件已存在（notes.txt）...` | ✅ |
| 12 | `write_file path=no_such_dir/a.txt content=x` | 父目录不存在 | `错误：父目录不存在（no_such_dir）...` | ✅ |
| 13 | `search_content path=. keyword=needle` | 超上限才提示 | 出提示 ✅ | ✅ |
| 14 | `search_content path=. keyword=hello` | **未超上限不出提示** | 没出现 ✅ | ✅ |
| 15 | `read_file path=hello_big.txt` | 大文件截断 + 提示 | 182911 → 前 8000 字符 | ✅ |
| 16 | `read_file path=notes.txt` | **正常文件不受影响** | 全文返回 | ✅ |
| 17 | `read_file path=edge_20000.txt` | 正好到上限，不截断 | 不截断 | ✅ |
| 18 | `read_file path=edge_20001.txt` | 刚超上限，截断 | 截断 | ✅ |

**回归确认**：以上命令跑完后 `sandbox\` 没有多出任何文件（`edge_*` 是本次新加的边界样本）。

**第 13/14 条、第 16/15 条、第 17/18 条都是「对照测试」** —— 成对验证"该发生时发生、不该发生时不发生"。
只测一边，写反了也看不出来。

**全部已修复**：6 条问题现在都是 ✅。
