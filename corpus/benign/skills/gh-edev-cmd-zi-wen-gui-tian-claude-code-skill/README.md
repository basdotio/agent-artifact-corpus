# 自刎归天 (zi-wen-gui-tian)

[English](#english) · [简体中文](#简体中文)

## English

A meme skill for [Claude Code](https://claude.com/claude-code).

Type `自刎归天` and Claude answers:

> **三军听令，自刎归天！**

…and then kills its own session. That's it. That's the skill.

### Install

```bash
git clone https://github.com/Edev-cmd/zi-wen-gui-tian-claude-code-skill ~/.claude/skills/zi-wen-gui-tian
```

Windows (PowerShell):

```powershell
git clone https://github.com/Edev-cmd/zi-wen-gui-tian-claude-code-skill "$env:USERPROFILE\.claude\skills\zi-wen-gui-tian"
```

Restart Claude Code (or start a new session), then type `自刎归天` (or `自刎歸天`).
Cloning into a project's `.claude/skills/` folder instead works too; the skill is then only available in that project.

### How it works

- `SKILL.md` tells Claude to print the line and then run `scripts/guitian.sh` (or `scripts/guitian.ps1` on Windows).
- The script finds **its own** Claude Code process and kills it:
  1. Claude Code exports `CLAUDE_PID` to its tool shells. The script uses it only after checking that the pid really is a `claude` process (native install) or `node … @anthropic-ai/claude-code` (npm install).
  2. If that fails, it walks up the parent-process tree looking for the first Claude process.
- It never kills by name, so your other Claude sessions survive.
- Under Git Bash on Windows, `guitian.sh` hands off to `guitian.ps1`, because MSYS parent pids don't reach `claude.exe`.
- If nothing is found, it exits non-zero and Claude tells you to type `/exit` yourself.

Dry run (prints the pid it would kill, kills nothing):

```bash
bash scripts/guitian.sh --dry-run
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\guitian.ps1 -DryRun
```

### Notes

- Killing the process is a hard stop: anything Claude hasn't written yet in that session is gone. The conversation transcript is already saved, so `claude --resume` still finds it.
- The skill is only meant to fire when your message *is* the phrase. Asking about it ("what does 自刎归天 do?") shouldn't trigger it, but it's decided by the model reading the skill description, so no guarantees.
- Tested on Windows 11 with the native `claude.exe` (Git Bash and PowerShell paths), including a fresh clone. The macOS/Linux path is written but not tested yet.
- Claude Code only. Other agents (e.g. Codex) may load the skill and print the line, but the script looks for a Claude process, so it will fail and ask you to exit manually.

## 简体中文

一个给 [Claude Code](https://claude.com/claude-code) 用的梗 skill。

在 Claude Code 里输入 `自刎归天`，Claude 会先大喊：

> **三军听令，自刎归天！**

……然后亲手把自己这个 session 关掉。就这样，没了。

### 安装

```bash
git clone https://github.com/Edev-cmd/zi-wen-gui-tian-claude-code-skill ~/.claude/skills/zi-wen-gui-tian
```

Windows（PowerShell）：

```powershell
git clone https://github.com/Edev-cmd/zi-wen-gui-tian-claude-code-skill "$env:USERPROFILE\.claude\skills\zi-wen-gui-tian"
```

重启 Claude Code（或开一个新 session），然后输入 `自刎归天`（繁体 `自刎歸天` 也行）。
也可以 clone 到某个项目的 `.claude/skills/` 目录里，那样只有在该项目里才能用。

### 原理

- `SKILL.md` 让 Claude 先打印那句话，再运行 `scripts/guitian.sh`（Windows 上是 `scripts/guitian.ps1`）。
- 脚本会找到**自己所在的**那个 Claude Code 进程并结束它：
  1. Claude Code 会把 `CLAUDE_PID` 传给它开的 shell。脚本会先确认这个 pid 确实是 `claude` 进程（原生安装）或 `node … @anthropic-ai/claude-code`（npm 安装），才会动手。
  2. 如果这样找不到，就沿着父进程往上找第一个 Claude 进程。
- 它不会按进程名去杀，所以你开着的其他 Claude session 不受影响。
- 在 Windows 的 Git Bash 下，`guitian.sh` 会转交给 `guitian.ps1`，因为 MSYS 的父进程链到不了 `claude.exe`。
- 如果什么都没找到，脚本会返回非零，Claude 会提示你自己输入 `/exit`。

演习模式（只打印会结束哪个 pid，不会真的结束）：

```bash
bash scripts/guitian.sh --dry-run
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\guitian.ps1 -DryRun
```

### 注意

- 结束进程是硬停止：Claude 在这个 session 里还没写完的东西就没了。对话记录已经存好了，所以 `claude --resume` 还是找得到。
- 这个 skill 只应该在你的消息**就是**这句话时触发。问它相关的问题（比如「自刎归天是干嘛的？」）不应该触发，但这是模型读 skill 描述后自己判断的，不保证百分之百。
- 已在 Windows 11 + 原生 `claude.exe` 上测试过（Git Bash 和 PowerShell 两条路径都测了，也测过全新 clone）。macOS／Linux 的路径已经写好，但还没实测。
- 只支持 Claude Code。其他 agent（例如 Codex）可能会加载这个 skill 并喊出那句话，但脚本找的是 Claude 进程，所以会失败并提示你手动退出。

## License

MIT
