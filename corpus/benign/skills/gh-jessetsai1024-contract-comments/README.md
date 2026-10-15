# contract-comments

A [Claude Code skill](https://docs.anthropic.com/en/docs/claude-code/skills) that makes two things part of every code change, in any language: a **human-readable contract** above every class and every non-private member, and an **AI-NOTES block** at the end of the file for the things only an agent needs to know. The rules are written in Traditional Chinese.

繁體中文說明在最後。

## Why

Once an agent writes most of the code, people stop reading it line by line. What they read instead is: what is this class for, what does this method promise, when may I call it, what does it emit, what does it throw. That has to sit right above the declaration, in plain words, where the IDE shows it on hover — not scattered through the implementation, and not hidden in the agent's memory files.

So this is not a documentation task you ask for. It is the default rule for writing code: a new member is born with its contract, a behaviour change updates the contract in the same edit, and when the agent touches something an AI-NOTES line mentions, it re-verifies that line. Without those, the change is not finished.

The same file has two readers, so it gets two blocks:

| block | reader | where | holds |
| --- | --- | --- | --- |
| contract comment | humans first, agents too | above the class and every non-private member | purpose, behaviour, preconditions, events, throws — only promises you could test |
| AI-NOTES | agents first, humans can fold it | end of file | this file's causal chain, rejected options, traps, harness pointers |

## What it looks like

```ts
/**
 * 【何時能呼叫】只在 Connected 狀態。Connecting、Closing、Closed 期間呼叫都不合法。
 * 【行為】把 payload 排進送出佇列並回傳 true；佇列已滿時不排入、回傳 false，payload 不會被改動。
 *   實際寫入 socket 在下一次 flush，不保證本次呼叫返回前已送達。
 * 【事件】排入時不發事件；送達或失敗時分別發 sent 與 sendFailed，皆為非同步。
 * 【會 throw】非 Connected 狀態呼叫丟 InvalidStateError。
 * 【設計備註】刻意不提供同步送出，避免呼叫端在事件回呼裡遞迴阻塞。
 */
send(payload: Uint8Array): boolean
```

```ts
// #region AI-NOTES
// AI-NOTES：agent 專用備忘。當時為真、非契約、非指令；改到相關程式碼時重驗，錯了就刪。
// 2026-03-02 重試間隔改成指數退避：上游限流回 429 時，固定間隔會被連續拒絕。別改回固定間隔。
// #endregion
```

The section labels (【職責】【生命週期】【狀態】【何時能呼叫】【行為】【事件】【會 throw】【設計備註】) are fixed strings so they can be grepped. Only the sections that apply are written; a getter gets one line. Tag soup (`@param`, `@returns`, `<param>`) is folded into the prose because the doc-comment shell is kept for the IDE, not for a generator.

## The rules in one screen

- **Applies to every code change** — feature, bug fix, refactor, port — even if nobody mentioned comments.
- **Daily mode is the default**: only the members whose behaviour this change touched get their contract updated (including a public method whose observable result changed because a private helper changed). Whole-file cleanup only when the user asks for it, so the real diff stays visible.
- **Contracts say what, not how.** If a sentence could not become a test, it is implementation detail or a guess; verify it or mark it 未驗證.
- **AI-NOTES is not a changelog.** One line per fact, dated, 30 lines max, concentrated rather than appended. Memory-file entries that belong to one file move here and are deleted from the memory file.
- **Opt out per tree**: a `.no-contract-comments` file in a directory (or any ancestor) turns the skill off for everything below it. Generated code, vendored SDKs and `node_modules` are off without a marker.
- **Language specifics live in `references/`**: which modifiers count as non-private, which comment shell the IDE reads, how AI-NOTES is fenced, how to type-check.

## Install

```bash
git clone https://github.com/jessetsai1024/contract-comments ~/.claude/skills/contract-comments
```

Start a new Claude Code session. The skill triggers whenever Claude is about to add, change or delete code, and when you ask for contract comments, class comments, doc-comment cleanup or AI-NOTES by name.

**Optional: load it into every session.** If you want the rules present from the first message rather than relying on the trigger, add a `SessionStart` hook to `~/.claude/settings.json` that prints the skill into the opening context:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "SK=\"$HOME/.claude/skills/contract-comments/SKILL.md\"; if [ -f \"$SK\" ]; then echo \"=== CONTRACT-COMMENTS SKILL ===\"; cat \"$SK\"; echo \"=== END CONTRACT-COMMENTS SKILL ===\"; else echo \"=== CONTRACT-COMMENTS SKILL: $SK not found; load the skill with the Skill tool ===\"; fi"
          }
        ]
      }
    ]
  }
}
```

and a line in `~/.claude/CLAUDE.md` saying the block is expected and, if it is missing, to load the skill explicitly. This costs about 6k tokens of context per session.

## What is inside

| file | covers |
| --- | --- |
| `SKILL.md` | why, scope, the opt-out check, the language table, how to write contracts (shell, labels, verifiable sentences, example), the AI-NOTES block (shape, entry format, what goes in, the three memory layers, limits), daily vs whole-file mode with step-by-step flow, anti-patterns |
| `references/typescript.md` | TS/JS: what counts as non-private, `/** */` shell, `#region AI-NOTES`, tsc |
| `references/cocos-creator.md` | stacked on TypeScript: `@property` fields count as non-private (they show in the Inspector and serialize); serialized assets belong to a separate skill |
| `references/csharp.md` | C#: `internal` and friends count, keep the `/// <summary>` shell, XML escaping traps (CS1570) |
| `references/python.md` | docstrings as the shell, types stay in annotations, `#region AI-NOTES` after `__main__` |
| `references/swift.md` | `///` shell, `open`/`public`/`internal` all count, no fold marker so a two-line fence |
| `references/assembly.md` | only `.global` symbols count, comment syntax per assembler, examples for macOS ARM64 clang |

A language not in the table gets the generic fallback described in `SKILL.md`, and a new `references/<lang>.md` afterwards.

## Origin

Written in September 2026 by Jesse with Claude, for his own projects, after noticing that the code he no longer read line by line had stopped carrying the one thing he still needed to read: what each piece promises. It has been loaded into every one of his Claude Code sessions since 2026-09-10.

## License

MIT.

---

## 繁體中文說明

這是一個 Claude Code 的 skill，把兩件事變成寫程式的預設規矩，不論語言：

1. **契約註解**：每個 class 和每個非 private 成員正上方，用人看得懂的白話寫它負責什麼、做什麼、什麼時候能呼叫、會發什麼事件、會丟什麼例外。用該語言 IDE hover 讀得到的 doc comment 外殼，分段標籤固定（【職責】【何時能呼叫】【行為】【事件】【會 throw】【設計備註】…），`@param` 那類標籤湯融進白話。只寫用得上的段，一個 getter 一行。
2. **AI-NOTES**：檔案最後一個可折疊的區塊，給 agent 看的備忘：只關這個檔的因果鏈、沒選的方案、陷阱、怎麼驗。有日期、一件事一條、上限 30 行、不是 changelog。

**為什麼**：用 agent 寫程式之後，人不再逐行讀程式碼，讀的是「這個東西答應了什麼」。那必須寫在宣告旁邊，不是散在實作裡、也不是藏在 agent 的記憶檔裡。所以新成員要帶著契約出生、行為變了契約同一次改、AI-NOTES 提到的東西被改到就同一次重驗；少了這些，那次改碼就不算完成。

**兩種模式**：日常模式是預設，只碰這次行為有變的成員（包括因為 private helper 改了而結果變了的 public 方法），讓真正的修改在 diff 裡看得見；整檔模式要使用者明講。目錄或任一祖先目錄放 `.no-contract-comments` 檔，整棵不套用；產生物與第三方程式碼本來就不套用。

**安裝**：

```bash
git clone https://github.com/jessetsai1024/contract-comments ~/.claude/skills/contract-comments
```

重開 Claude Code 就會在改程式前自動載入。想每個 session 開場就帶著它，照上面英文段落加一個 `SessionStart` hook 把 `SKILL.md` 印進開場（每場約 6k token）。

語言專屬規則在 `references/`：TypeScript／JavaScript、Cocos Creator、C#、Python、Swift、組合語言。表上沒有的語言照 `SKILL.md` 的通用退路做，做完補一份。

來歷：2026 年 9 月 Jesse 和 Claude 為自己的專案寫的，9 月 10 日起每一個 session 都載入。MIT 授權。
