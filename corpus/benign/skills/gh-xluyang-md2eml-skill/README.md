# Local Markdown to Email Skill

[![Validate](https://github.com/OWNER/REPOSITORY/actions/workflows/validate.yml/badge.svg)](https://github.com/OWNER/REPOSITORY/actions/workflows/validate.yml)

一个零网络依赖的本地 Markdown 转邮件工具与 Agent Skill。

把本地 Markdown 笔记转换成适合邮件客户端的 HTML、带本地图片 CID 附件的 `.eml` 草稿，或系统富文本剪贴板内容。

这个 Skill 完全在本机处理笔记和图片。模型只需要传递文件路径、输出类型和主题；图片二进制由 `scripts/local_markdown_to_email.py` 读取、编码并封装，不会进入模型上下文，也不会上传到第三方服务。

## 目录结构

```text
local-markdown-to-email/
├── SKILL.md
├── tool_spec.json
├── README.md
└── scripts/
    └── local_markdown_to_email.py
```

> 发布到 GitHub 后，请将上方徽章中的 `OWNER/REPOSITORY` 替换为实际仓库路径。

运行时只需要 Python 3.10 或更高版本。生成 `.eml` 使用 Python 标准库，不需要安装第三方包。剪贴板模式优先使用 `pyperclip`，也可以使用系统自带的 `pbcopy`、`xclip` 或 `xsel`。

## 支持的功能

- WikiLink 图片：`![[image.png]]`、`![[image.png|400]]`
- Markdown 图片：`![说明](./assets/image.png)`
- 从笔记目录、根目录 根目录和 根目录 子目录查找附件
- `NOTE`、`TIP`、`WARNING`、`CAUTION`、`IMPORTANT` Callout
- 标题、粗体、斜体、行内代码、代码块、列表和 Markdown 表格
- 非图片双链转换为粗体文本，避免邮件出现无效内部链接
- 缺图占位：`[图片缺失: filename.png]`
- 三种输出：`eml`、`clipboard`、`both`
- 三种主题：`default`、`modern`、`minimal`

## 快速验证

在仓库根目录执行：

```bash
python3 -m py_compile scripts/local_markdown_to_email.py
python3 scripts/local_markdown_to_email.py --help
```

使用一个真实笔记生成 `.eml`：

```bash
python3 scripts/local_markdown_to_email.py \
  --note-path "Projects/2026架构规划.md" \
  --root-path "/绝对路径/到/本地笔记根目录" \
  --output-type eml \
  --theme default
```

默认输出到笔记同目录，例如 `2026架构规划.eml`。也可以指定输出文件：

```bash
python3 scripts/local_markdown_to_email.py \
  --note-path "/绝对路径/到/本地笔记根目录/Projects/design.md" \
  --output-type eml \
  --output-path "/绝对路径/到/Downloads/design.eml"
```

脚本始终在标准输出打印 JSON：

```json
{
  "status": "success",
  "message": "转换完成",
  "data": {
    "output_type": "eml",
    "embedded_images_count": 3,
    "missing_images": [],
    "eml_file_path": "/path/to/design.eml"
  }
}
```

错误时进程返回码为 `1`，并打印 `status: error` 的 JSON。缺失图片不是致命错误：转换继续，图片位置显示占位文本，并在 `missing_images` 中列出。

## Claude Code 部署

Claude Code 使用带 `SKILL.md` 的 Skill 目录。推荐先做用户级安装，所有项目都能使用；只希望某个项目使用时，则放入项目目录。

### 用户级安装

Linux/macOS：

```bash
mkdir -p "$HOME/.claude/skills/local-markdown-to-email/scripts"
cp SKILL.md README.md tool_spec.json "$HOME/.claude/skills/local-markdown-to-email/"
cp scripts/local_markdown_to_email.py "$HOME/.claude/skills/local-markdown-to-email/scripts/"
chmod +x "$HOME/.claude/skills/local-markdown-to-email/scripts/local_markdown_to_email.py"
```

Windows PowerShell：

```powershell
$dest = "$HOME\.claude\skills\local-markdown-to-email"
New-Item -ItemType Directory -Force "$dest\scripts" | Out-Null
Copy-Item SKILL.md,README.md,tool_spec.json $dest
Copy-Item scripts\local_markdown_to_email.py "$dest\scripts\"
```

重新打开 Claude Code 会话后，用自然语言调用：

```text
把 /Users/me/本地笔记/Projects/design.md 转成邮件草稿，根目录 是 /Users/me/本地笔记，输出为 eml，主题用 modern。
```

也可以要求直接粘贴到邮件编辑器：

```text
把这篇 本地笔记 笔记转成 HTML 富文本并复制到系统剪贴板：
/Users/me/本地笔记/Projects/design.md
```

如果 Claude Code 没有自动发现 Skill，直接执行脚本即可：

```bash
python3 "$HOME/.claude/skills/local-markdown-to-email/scripts/local_markdown_to_email.py" \
  --note-path "/Users/me/本地笔记/Projects/design.md" \
  --root-path "/Users/me/本地笔记" \
  --output-type eml
```

### 项目级安装

在要使用该能力的项目根目录执行：

```bash
mkdir -p .claude/skills/local-markdown-to-email/scripts
cp /path/to/local-markdown-to-email/{SKILL.md,README.md,tool_spec.json} .claude/skills/local-markdown-to-email/
cp /path/to/local-markdown-to-email/scripts/local_markdown_to_email.py .claude/skills/local-markdown-to-email/scripts/
```

项目级 Skill 适合团队仓库或需要版本控制的自动化流程。

## Codex 部署

Codex 使用 `$CODEX_HOME/skills`；未设置 `CODEX_HOME` 时通常是 `~/.codex/skills`。Skill 目录名建议与 frontmatter 的 `name` 一致。

### 用户级安装

```bash
CODEX_SKILLS_DIR="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$CODEX_SKILLS_DIR/local-markdown-to-email/scripts"
cp SKILL.md README.md tool_spec.json "$CODEX_SKILLS_DIR/local-markdown-to-email/"
cp scripts/local_markdown_to_email.py "$CODEX_SKILLS_DIR/local-markdown-to-email/scripts/"
chmod +x "$CODEX_SKILLS_DIR/local-markdown-to-email/scripts/local_markdown_to_email.py"
```

重新开始一个 Codex 会话，然后输入：

```text
使用 local-markdown-to-email，把 Projects/design.md 转成 .eml。
根目录 路径是 /home/me/本地笔记，使用 modern 主题，输出到 /home/me/Downloads/design.eml。
```

若使用的是当前仓库中的 Skill，也可以直接要求 Codex 从当前目录运行：

```text
使用当前目录的 local-markdown-to-email Skill，执行 scripts/local_markdown_to_email.py，
把 /home/me/本地笔记/Projects/design.md 输出为 clipboard。
```

### Codex 中的路径和权限

- `note_path` 可以是绝对路径，也可以是相对于 `vault_path` 的路径。
- 为避免歧义，自动化调用推荐始终传绝对的 `vault_path`。
- 生成 `.eml` 是本地文件写入；请确保 Codex 会话对目标目录有写权限。
- 剪贴板模式需要图形会话和可用剪贴板后端。服务器或 SSH 无桌面环境时，优先使用 `eml`。

## Pi 部署

Pi 的 Skill 目录位置可能由具体发行版或启动脚本配置。最稳妥的方式是把 Skill 放入 Pi 配置的 skills 目录；如果当前环境没有自动 Skill 目录，则保留仓库目录并让 Pi 调用 CLI。

### 发现 Pi 的 Skill 目录

先查看 Pi 的帮助和配置：

```bash
pi --help
pi config list 2>/dev/null || true
```

如果你的 Pi 配置指定了 skills 目录，设为变量后复制：

```bash
PI_SKILLS_DIR="/path/to/pi/skills"
mkdir -p "$PI_SKILLS_DIR/local-markdown-to-email/scripts"
cp SKILL.md README.md tool_spec.json "$PI_SKILLS_DIR/local-markdown-to-email/"
cp scripts/local_markdown_to_email.py "$PI_SKILLS_DIR/local-markdown-to-email/scripts/"
chmod +x "$PI_SKILLS_DIR/local-markdown-to-email/scripts/local_markdown_to_email.py"
```

如果 Pi 以项目目录加载 Skill，可以使用：

```bash
mkdir -p .pi/skills/local-markdown-to-email/scripts
cp SKILL.md README.md tool_spec.json .pi/skills/local-markdown-to-email/
cp scripts/local_markdown_to_email.py .pi/skills/local-markdown-to-email/scripts/
```

然后在 Pi 中发送：

```text
调用 local-markdown-to-email，将 /data/本地笔记/Inbox/report.md 转为邮件 .eml，
根目录 为 /data/本地笔记，使用 minimal 主题。
```

### Pi 的直接 CLI 兜底

当 Pi 版本没有 Skill 自动发现机制时，直接把下面的命令注册为 shell tool、脚本工具或工作流步骤：

```bash
python3 /path/to/local-markdown-to-email/scripts/local_markdown_to_email.py \
  --note-path "/data/本地笔记/Inbox/report.md" \
  --root-path "/data/本地笔记" \
  --output-type both
```

Pi 只需要读取 JSON 结果中的 `eml_file_path`、`embedded_images_count` 和 `missing_images`，不需要读取图片内容。

## 剪贴板依赖

推荐安装 `pyperclip`：

```bash
python3 -m pip install --user pyperclip
```

不安装 Python 包时：

- macOS：使用系统 `pbcopy`
- Linux X11：安装 `xclip` 或 `xsel`
- Windows：建议安装 `pyperclip`；PowerShell、远程会话或无桌面环境可能无法提供 HTML 剪贴板

`clipboard` 模式成功时 `clipboard_error` 为 `null`。没有可用后端时，转换仍返回 JSON，但 `clipboard_error` 会说明原因；这不会影响 `eml` 模式。

## 参数参考

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `--note-path` | 是 | Markdown 笔记的绝对路径，或相对于 根目录 的路径 |
| `--root-path` | 否 | 本地笔记 根目录 绝对路径；使用相对笔记路径时建议提供 |
| `--output-type` | 否 | `eml`、`clipboard` 或 `both`，默认 `eml` |
| `--theme` | 否 | `default`、`modern` 或 `minimal`，默认 `default` |
| `--output-path` | 否 | `.eml` 的目标路径；未提供时写到笔记同目录 |

等价的 JSON 工具契约见 [tool_spec.json](tool_spec.json)。

## 常见问题

### 找不到笔记

相对路径必须相对于 `--root-path`。检查：

```bash
test -f "/path/to/vault/Projects/design.md" && echo ok
```

也可以直接传绝对路径，此时 `--root-path` 可省略。

### 图片显示为缺失

脚本会依次按笔记目录、根目录 根目录和 根目录 中同名文件查找。确认文件名大小写与扩展名完全一致。WikiLink 的宽度写法应为 `![[image.png|400]]`。

### `.eml` 能打开但图片不显示

请使用 Outlook、Apple Mail、Thunderbird 或其他支持 `multipart/related` 的客户端打开，不要把 `.eml` 当普通文本导入。脚本会把图片作为 CID 相关附件写入 HTML 邮件部分。

### 服务器上无法使用 clipboard

这是预期限制：剪贴板需要当前用户的桌面会话。服务器环境使用 `--output-type eml`，再下载 `.eml` 到本机邮件客户端。

### 如何更新 Skill

重新复制 `SKILL.md` 和 `scripts/local_markdown_to_email.py` 覆盖安装目录，然后重启 Claude Code、Codex 或 Pi 会话。Skill 是纯文件包，不需要数据库迁移。

## 安全与数据边界

- 输入文件、图片和生成的 `.eml` 始终在本地处理。
- Skill 不调用网络、不使用图床、不上传附件。
- Agent 应传递路径参数，不要把图片 Base64 或文件二进制放入上下文。
- 使用 `both` 时会分别生成 CID `.eml` 和 Base64 剪贴板 HTML，图片可能被本地读取两次；大图较多时可按需选择一种输出。
