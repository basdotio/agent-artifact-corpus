---
name: auto-commit
description: 当用户要求提交代码、保存到 GitHub、推送改动、创建 PR 或同步代码时使用
allowed-tools: Bash(git:*), Bash(gh:*), Read, Grep
---

# 自动 Git 工作流

## 触发场景

- 用户说"提交代码"、"commit"
- 用户说"推送到 GitHub"、"push"
- 用户说"保存改动"、"同步代码"
- 用户说"创建 PR"

## 执行流程

### 1. 检查状态
```bash
git status
git diff --stat
```

### 2. 生成 Commit 消息
- 使用中文
- 格式：`<类型>: <简短描述>`
- 类型：
  - `feat`: 新功能
  - `fix`: 修复 bug
  - `refactor`: 重构
  - `docs`: 文档
  - `style`: 格式调整
  - `chore`: 杂项

### 3. 执行提交
```bash
git add <相关文件>
git commit -m "<消息>"
```

### 4. 推送（如果用户要求）
```bash
git push origin <当前分支>
```

### 5. 创建 PR（如果用户要求）
```bash
gh pr create --title "<标题>" --body "<描述>"
```

## 安全规则

- 不要自动 force push
- 不要自动 push 到 main/master
- 敏感文件（.env, credentials）要警告用户
