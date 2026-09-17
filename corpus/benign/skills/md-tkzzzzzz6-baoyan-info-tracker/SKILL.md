---
name: 保研信息自动化跟踪-保包
description: |
  监控GitHub仓库CS-BAOYAN/CSLabInfo2025的更新，跟踪计算机、生物医学工程、电子信息专业的保研招生和实习信息，通过时间过滤避免重复推送。
  【重要原则】：没有新的更新或不满足条件时，绝对不能发送任何消息推送，必须完全静默。
---

## 核心任务

监控目标仓库 `CS-BAOYAN/CSLabInfo2025` 的实时更新，筛选符合条件的保研情报并推送。

## 最高原则

**【绝对禁止】没有新的更新或不满足时间窗口条件时，必须完全静默，不能发送任何消息！**

## 环境配置

**必需工具**：`git`、`gh`、`jq`

**环境变量**：
- `REPO_DIR`：仓库本地路径（默认：`$HOME/CSLabInfo2025`）
- `TRACKER_DIR`：数据存储目录（默认：`$HOME/baoyan-tracker/data`）
- `WATERMARK_FILE`：水位线文件（默认：`$TRACKER_DIR/watermark`）
- `LOG_FILE`：审计日志文件（默认：`$TRACKER_DIR/llog`）

## 执行流程

### 1. 初始化环境
```bash
# 创建数据目录
mkdir -p "$TRACKER_DIR"

# 初始化水位线（如果不存在）
if [ ! -f "$WATERMARK_FILE" ]; then
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "$WATERMARK_FILE"
fi

# 克隆或更新仓库
if [ ! -d "$REPO_DIR/.git" ]; then
    git clone https://github.com/CS-BAOYAN/CSLabInfo2025.git "$REPO_DIR"
else
    cd "$REPO_DIR" && git pull origin main
fi
```

### 2. 检查最新Commit（早退机制）
```bash
cd "$REPO_DIR"

# 获取最新commit时间
LATEST_COMMIT=$(git log -1 --format="%ct" main)
CURRENT_TIME=$(date +%s)
WATERMARK=$(cat "$WATERMARK_FILE" | xargs date -u +"%s" 2>/dev/null || echo 0)

# 检查是否在1小时窗口内
COMMIT_AGE=$((CURRENT_TIME - LATEST_COMMIT))
if [ $COMMIT_AGE -le 3600 ] && [ $LATEST_COMMIT -gt $WATERMARK ]; then
    # 早退：推送commit摘要
    COMMIT_HASH=$(git log -1 --format="%h" main)
    COMMIT_MSG=$(git log -1 --format="%s" main)
    COMMIT_AUTHOR=$(git log -1 --format="%an" main)
    CHANGED_FILES=$(git diff --name-only HEAD~1 HEAD)

    echo "Found new commit on main branch."
    echo "Commit: $COMMIT_HASH"
    echo "Author: $COMMIT_AUTHOR"
    echo "Message: $COMMIT_MSG"
    echo "Changed files:"
    echo "$CHANGED_FILES" | sed 's/^/  /'

    # 更新水位线
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "$WATERMARK_FILE"

    # 记录审计日志
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] Status: CommitEarlyExit (New commit detected within 1h window)" >> "$LOG_FILE"
    exit 0
fi
```

### 3. 获取并筛选PR
```bash
cd "$REPO_DIR"
WATERMARK=$(cat "$WATERMARK_FILE")
CURRENT_TIME=$(date +%s)

# 获取最近更新的PR（最多50个）
gh pr list --repo CS-BAOYAN/CSLabInfo2025 --limit 50 --state open --json number,title,updatedAt > /tmp/prs.json

# 筛选PR
CANDIDATES=()
while IFS= read -r pr; do
    PR_UPDATED=$(echo "$pr" | jq -r '.updatedAt' | xargs date -u +"%s" 2>/dev/null || echo 0)
    WATERMARK_TS=$(date -u -d "$WATERMARK" +"%s" 2>/dev/null || echo 0)

    # PR静默窗口：1小时内不推送
    PR_AGE=$((CURRENT_TIME - PR_UPDATED))
    if [ $PR_AGE -ge 3600 ] && [ $PR_UPDATED -gt $WATERMARK_TS ]; then
        CANDIDATES+=("$pr")
    fi
done < <(jq -c '.[]' /tmp/prs.json)
```

### 4. 处理候选PR
```bash
HIT_COUNT=0

for pr in "${CANDIDATES[@]}"; do
    PR_NUMBER=$(echo "$pr" | jq -r '.number')
    PR_TITLE=$(echo "$pr" | jq -r '.title')

    # 输出结果
    echo "Result: PR#${PR_NUMBER} | Title: ${PR_TITLE}"
    HIT_COUNT=$((HIT_COUNT + 1))
done
```

### 5. 记录审计日志
```bash
SCANNED=$(jq '. | length' /tmp/prs.json 2>/dev/null || echo 0)
CANDIDATE_COUNT=${#CANDIDATES[@]}
FILTERED=$((SCANNED - CANDIDATE_COUNT))

if [ $HIT_COUNT -gt 0 ]; then
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] 扫描PR数: ${SCANNED} | 候选PR数: ${CANDIDATE_COUNT} | 命中: ${HIT_COUNT} | 过滤干扰项: ${FILTERED}" >> "$LOG_FILE"
    # 更新水位线
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "$WATERMARK_FILE"
else
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] Status: Idle (No relevant updates)." >> "$LOG_FILE"
fi
```

## 时间窗口规则

- **Commit早退窗口**：1小时（3600秒）- 最新commit在1小时内且新于水位线才推送
- **PR静默窗口**：1小时（3600秒）- PR更新后1小时内不推送
- **水位线机制**：记录上次扫描时间，实现增量扫描

## 输出格式

### Commit早退路径
```
Found new commit on main branch.
Commit: <hash>
Author: <author>
Message: <message>
Changed files:
  <file1>
  <file2>
```

### PR处理路径
```
Result: PR#<编号> | Title: <PR标题>
```

### 审计日志
```
[YYYY-MM-DD HH:MM:SS] 扫描PR数: N | 候选PR数: C | 命中: H | 过滤干扰项: Z
[YYYY-MM-DD HH:MM:SS] Status: Idle (No relevant updates).
[YYYY-MM-DD HH:MM:SS] Status: CommitEarlyExit (New commit detected within 1h window)
```
