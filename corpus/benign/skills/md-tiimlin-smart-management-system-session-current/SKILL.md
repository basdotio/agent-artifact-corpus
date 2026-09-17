---
name: session-current
description: >
  Get the current Claude Code session ID. Use at the end of a productive conversation
  to save the session ID for future resume. No search needed — returns newest session file.
  Use when user says "當前 session id"、"這個 session"、"目前對話 id"、"記錄這次對話"。
argument-hint: ""
user-invocable: true
layer: 5
type: tool
---

# Session Current

$$\text{SessionCurrent}() = \text{ProjectResolve} \to \text{LatestFile}(\text{dir}) \to \text{DisplayID}$$

## Step 1: ProjectResolve

$$\text{folder} = \$\text{PWD.replace}("/",\;"-") \quad \text{（完整替換，含首 "−"，e.g. /home/user/... → -home-user-...）}$$

$$\text{dir} = \texttt{\textasciitilde/.claude/projects/\{folder\}/}$$

## Step 2: LatestFile

$$\text{LatestFile}(\text{dir}) = \operatorname{argmax}_{\,\text{mtime}}(\text{dir/*.jsonl})$$

```bash
ls -t ~/.claude/projects/{folder}/*.jsonl | head -1
```

## Step 3: DisplayID

$$\text{session\_id} = \text{basename}(\text{LatestFile},\;".jsonl")$$

$$\text{output}: \text{session\_id} \;\Big|\; \texttt{claude --resume \{session\_id\}}$$
