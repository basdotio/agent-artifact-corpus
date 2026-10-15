---
name: autoloop
description: 自動開發 loop，一個 skill 兩個子指令。`/autoloop init`：把 repo 準備好（新 repo 從零建 harness；已有 harness 的瘦身指令檔），寫允許規則、ignore 與版本標記。`/autoloop run`：本 session 當主迴圈，每輪直接呼叫本 skill 的 run-round.sh 開一個獨立的 claude -p 工作者（NEEDS-USER 有 OPEN 就開 Fable 決策輪，否則開 Opus 實作輪），清理、留一行摘要、再開下一輪；要人決定或上下文超標時推手機通知並停下。repo 裡不放任何腳本。
---

# 用法

- `/autoloop init`：每個 repo 做一次；本 skill 升版後再做一次（任何版本都要）。
- `/autoloop run`：在已 init 的 repo 啟動或接續 loop。
- 沒給子指令：看 repo 有沒有 `.claude/autoloop.json`，沒有就當 `init`，有就當 `run`，並說一句你選了哪個。

本 skill 的所有執行檔都在安裝目錄的 `assets/`：`run-round.sh`（輪次啟動器）、`decide.md`（Fable 決策輪 prompt）、`implement.md`（Opus 實作輪 prompt）、`ctx-usage.sh`、`VERSION`（semver）。skill 可以裝在 repo 層或使用者層，所以路徑要用找的，而且要以**文字形式**記住，因為允許規則是字串比對：
- repo 層：`.claude/skills/autoloop/assets`（相對 repo 根目錄）
- 使用者層：`~/.claude/skills/autoloop/assets`（**寫 `~`，不要展開成 `/Users/...`**）
下文寫作 `$A`。`init` 把找到的那個字串寫進 `.claude/autoloop.json`，`run` 之後一律照那個字串呼叫，例如 `bash ~/.claude/skills/autoloop/assets/run-round.sh opus`。

原則：狀態在 repo 不在對話；一輪一個切片，做完就結束；驗收狀態只有一個來源；需要人決定的事寫進檔案等人，不硬做。**決策政策（TECH／AUTH 分類、例外、supervisor 寫入流程）只存在 `$A/decide.md`，指令檔不抄全文**，只放 repo 專屬的補充。

---

# init

## 開始前

1. `git status --porcelain` 必須乾淨；不乾淨先問使用者，不 reset、stash、覆寫。
2. 環境檢查：`uname` 是 Darwin 或 Linux（原生 Windows 不支援，請用 WSL）；`jq`、`lsof`、`perl` 都在 PATH（缺的給安裝指令）。獨立 CLI 已安裝（預設 `~/.local/bin/claude`，可用 `CLAUDE_BIN` 指定；沒有就給 `curl -fsSL https://claude.ai/install.sh | bash`）且已登入：`claude auth status` 的 `loggedIn` 為 true。否則請使用者在終端機執行 `claude` 登入；憑證由使用者親自處理。
3. 找 `$A`：`ls .claude/skills/autoloop/assets/VERSION` 有就用 repo 層，否則 `ls ~/.claude/skills/autoloop/assets/VERSION`；都沒有就請使用者先安裝 skill，結束。
4. 可調參數都放 repo 的 `.claude/settings.json` 的 `env`，不碰全域設定：`LOOP_MODEL_DECIDE`／`LOOP_MODEL_IMPLEMENT`（預設 claude-fable-5-1／claude-opus-5-5）、`LOOP_EFFORT_DECIDE`／`LOOP_EFFORT_IMPLEMENT`（預設 high）、`LOOP_TIMEOUT`（秒，預設 5400）、`LOOP_BUDGET`（美元，預設 20）、`LOOP_SWEEP_PATTERN`、`LOOP_CTX_WINDOW`（主 session 視窗 token 數，預設 Claude 5 系列 1M）、`LOOP_NOTIFY_CMD`（非桌面 app 環境的通知指令）。使用者沒有 Fable 或 Opus 的存取權時在這裡換模型。
5. 判斷模式：
   - **新 repo**：沒有指令檔的 loop 協定、沒有 `docs/progress/PLAN.md` → 走「建立 harness」再「寫設定」。
   - **已有 harness**：有協定與進度檔 → 走「瘦身指令檔」再「寫設定」。
   - **已 init 過**：有 `.claude/autoloop.json` → 版本或 assets 路徑和現在不同就更新它與允許規則；指令檔有舊段落就瘦身；其餘不動。
   - **從舊版升級**（1.x 的 loop-init／loop-run，或帶 stub 的版本）：除了「寫設定」，逐一清掉過時內容，列給使用者看後一次 `chore:`／`docs:` commit：`scripts/harness/run-round.sh`（完整腳本或 stub）→ `git rm`；允許規則 `Bash(scripts/harness/run-round.sh *)` → 移除；指令檔、STATUS、NEEDS-USER 裡的 `/loop-run`、`/loop-init`、`~/.claude/loop/decide.md`、`scripts/harness/run-round.sh` 字樣 → 改成 `/autoloop run`、`/autoloop init`、「autoloop 的 `decide.md`」、「autoloop 的 `run-round.sh`」；repo 根目錄殘留的 `.loop-main.json` → 刪；`logs/loop/` 的舊 log 留著不管。用 `grep -rn 'loop-run\|loop-init\|\.claude/loop\|harness/run-round' --include='*.md' --include='*.json' .` 掃一遍確認沒漏。
6. 新 repo 時先盤點：建置／測試／lint 指令、既有指令檔（CLAUDE.md 或 AGENTS.md，兩者只能留一個，有 CLAUDE.md 時 AGENTS.md 不會被讀）、測試工具、既有進度文件與大小、gates 會不會啟動長駐子程序。然後一次問使用者三件事：指令檔用哪個檔名；哪些檢查每切片必跑、哪些 milestone 才跑、哪些定期跑；允不允許 push，以及這個 repo **額外**要問人的動作（`decide.md` 已涵蓋刪已追蹤檔、遠端操作、放寬 gate、改驗收或方向、改 PLAN 順序、改寫 history、付費、核准 ADR）。

## 建立 harness（新 repo）

指令檔 200 行內，用一般 Markdown 連結指向其他文件，不用 @ 匯入。章節固定：

1. **邊界與工程規範**：從既有文件濃縮，不複製整份規格。
2. **Gates 分級**：每切片／milestone／定期三級，各列實際指令。不得為綠燈刪測試、放寬 tolerance、重跑到綠。pre-commit 只檢查變動檔；完整掃描留在完整 CI。
3. **Loop 協定**：開場先跑開場腳本（`npm run loop:start` 或等價，結束碼 0＝有工作且已建 lock、3＝停止條件、4＝STOP 檔或另一輪進行中），讀 STATUS、PLAN、NEEDS-USER，必要時讀 CODEMAP；有 RESOLVED 的 NEEDS-USER 項目先套用再開工。中間只做 PLAN 最上面一個 TODO；每個長步驟前 `touch .loop.lock`；中途發現 STOP 只回報不改檔。結尾跑適用 gates、請 reviewer 子代理看實際 diff、commit、寫切片記錄 `docs/progress/log/<切片ID>.md`、更新 STATUS 與驗收狀態、RESOLVED 改 APPLIED、`rm -f .loop.lock`。
4. **定期完整檢查**：距上次完整 CI 超過 24 小時或已完成 5 個實作切片時，該輪只跑完整 CI；失敗寫 NEEDS-USER 並停止。
5. **停止條件與停止記錄**：STOP 檔；同一切片連續兩輪 gates 不過；需要人決定；工作樹的未提交檔與停止項清單不一致；STATUS 起點核對不符；PLAN 無 TODO。停止時只提交 NEEDS-USER 與 STATUS 的停止記錄，`git status --porcelain` 原樣寫進該項。例外（可帶著 BLOCKED 提交）的三個條件同時成立才適用，且不得把驗收項改 PASS。
6. **單一 writer**：同一時間只有一個代理寫 working tree；子代理只做調查與審查；supervisor（決策輪）寫入前建 STOP、寫完移除。
7. **PLAN 規則**：順序由使用者決定；代理可拆分項目、標 DONE、把新項目插在最後一項之前；每項含 ID、目標、驗收條件與驗證指令、狀態；200 行內。
8. **NEEDS-USER 格式與本 repo 的補充**：每項 `### ID 標題 — OPEN|RESOLVED|APPLIED — TECH|AUTH`，含背景、選項、建議、擋住的 PLAN 項目、使用者決定、套用方式。寫一句：「決策政策（哪些可由 supervisor 決定、例外、寫入流程）見 autoloop 的 `decide.md`；本 repo 額外必須問使用者的動作：…」。writer 在輪中遇到 TECH 問題可交 `decider` 子代理，ESCALATE 才寫 NEEDS-USER。
9. **ADR 規則**：架構決定以 PROPOSED 提交並寫 NEEDS-USER，核准前不做依賴它的切片。
10. **腳本規則**：`scripts/harness/*.sh` 一律 `set -eu`；有逾時的 gate 逾時要終止整個程序群組並清暫存；每輪結尾不得留下背景程序。
11. **Git 規則**：小而完整的 commit，Conventional Commits；不 push、不開 PR、不改全域設定。
12. **環境備註**：機器、工具版本、已知的環境坑。
13. **執行方式**：「用 `/autoloop run` 驅動，每輪由 autoloop 的 `run-round.sh` 啟動獨立工作者；逾時與費用上限可在 `.claude/settings.json` 的 `env` 設 `LOOP_TIMEOUT`、`LOOP_BUDGET`；log 在 `logs/loop/`；版本標記在 `.claude/autoloop.json`。」

其他檔案：`docs/progress/PLAN.md`、`STATUS.md`（含起點核對值一行）、`NEEDS-USER.md`、`log/`；機器可讀的驗收清單（`docs/progress/ACCEPTANCE.json`，每項有通過條件、負向案例、狀態 PASS／FAIL／BLOCKED／NOT_RUN／NA、證據路徑）；`docs/CODEMAP.md`（200 行內）；`docs/adr/` 與模板；`.claude/agents/`：explorer（sonnet、medium、唯讀）、doc-writer（sonnet、medium，只寫 docs）、reviewer（opus、xhigh、唯讀，看實際 diff）、decider（fable、high、唯讀，輪中 TECH 決策）；唯讀子代理用白名單腳本把 Bash 限制成唯讀。既有巨大的進度文件原文搬到 `docs/progress/archive/`。PLAN 第一項放「驗收稽核」；gates 會啟動長駐子程序時，第一個產品切片之前加「逾時終止與殘留清理」項目。

## 瘦身指令檔（已有 harness）

指令檔是使用者的規則，**先列出要改的段落與替換文字，使用者同意才動**，一次 `docs:` commit：
- NEEDS-USER 協定裡的 TECH／AUTH 分類細則、decider 核准流程、Supervisor 規則整節 → 換成第 8 章節那一句指向 `decide.md` 的話，加上本 repo 額外要問人的動作（從原文裡挑出 `decide.md` 沒有的）。整節刪掉會讓其他章節的 § 引用錯位時，保留標題只留一行指向。
- 排程相關章節 → 換成第 13 章節「執行方式」。
- 結尾補「不得留下背景程序」（若缺）。
- 指令檔若規定「起點核對值之後只能有 docs commit」，init 的 `chore:` commit 會違反它：在同一個 docs commit 裡把起點核對值移到那個 commit，不要放寬規則。
- 其餘章節不動。改完跑 repo 的文件檢查（若有）。

## 寫設定

1. `.claude/autoloop.json`：`{"version":"<cat $A/VERSION>","assets":"<$A 的文字路徑>"}`。這是 repo 的版本標記；`run` 開場拿它和 skill 比，不同就要求重跑 init。
2. `.claude/settings.json`：`permissions.allow` 加 `"Bash(<$A 的文字路徑>/run-round.sh *)"`（例如 `Bash(~/.claude/skills/autoloop/assets/run-round.sh *)`；這是窄規則，auto 模式下仍有效、在分類器之前判定，主 session 啟動工作者才不會被臨場擋下）；新 repo 另加 `"effortLevel": "high"`、deny `git push`、只預先允許明確列出的安全指令。已有內容就合併，不動其他鍵。
3. `.gitignore` 確保有 `STOP`、`.loop.lock`、`.loop-round.pid`、`.loop-main.json`、`logs/`（沿用檔內既有的寫法，例如前導 `/`）。
4. 看 gates 用到的長駐程序是否在 `run-round.sh` 的 `SWEEP_PATTERN`（vite、node、npm、blender、cargo、playwright、chrom*、python、tail…）裡；不在就建議在 `env` 設 `LOOP_SWEEP_PATTERN`。用最近幾個切片記錄的實際耗時估 `LOOP_TIMEOUT`（最長一輪的兩倍）與 `LOOP_BUDGET`。
5. 試跑 `bash <$A 的文字路徑>/run-round.sh sweep`，應印出 `sweep: killed=[]`。
6. commit（`chore: autoloop <版本>` 或與 harness 一起），只 add 明確路徑。不 push。

## 收尾

回報：改了哪些檔、commit hash、指令檔行數、gates 分級、`SWEEP_PATTERN` 與逾時／預算、本 repo 額外的 AUTH 動作。下一步固定是：「開一個 Sonnet 5.5 / medium 的 session，執行 `/autoloop run`」。若這個 repo 還有舊的 app 排程任務，提醒使用者停用或刪除。

不做的事：不建立排程任務、不 push、不改 `~/.claude/` 下的任何檔、不跑實作輪、不在未經使用者同意下改指令檔內容。

---

# run

## 角色

你是主迴圈，不是 writer，也不是決策者。你**不改程式碼、不跑 gates、不做切片、不替使用者做 AUTH 決定**。你做的事只有：檢查狀態、挑這一輪的角色、啟動工作者、讀結果、清理、留一行摘要、通知使用者。狀態全在 repo 檔案裡，你的對話記憶不是真相來源。

工作者是 `$A/run-round.sh` 啟動的獨立 `claude -p` 程序（有自己的程序群組、逾時、清理；它以 git 根目錄當 repo root，所以要在 repo 根目錄呼叫）。它們看不到這個對話，你也不能傳訊息給它們；溝通只靠 repo 檔案與它們留下的 `logs/loop/<ts>-<role>.summary`。

參數（寫死，使用者要改再改）：上下文門檻 **30%**；決策輪 `fable`（Fable 5.1 high）；實作輪 `opus`（Opus 5.5 high）；主 session 建議用 **Sonnet 5.5 / medium**。

## 開場（每次呼叫都做一次）

0. 版本核對：讀 `.claude/autoloop.json` 的 `version` 與 `assets`（沒有這個檔 → 請先跑 `/autoloop init`，結束）。`RR="<assets>/run-round.sh"`（照檔裡的字串，不展開 `~`，之後所有呼叫都用這個字串，允許規則才會匹配）。`S=$(cat <assets 展開後>/VERSION)`。`version` 和 `S` **不完全相同**（patch 不同也算）→ **不啟動**，只告訴使用者「repo 是 version，skill 是 S，請先跑 `/autoloop init`」並結束。不要自己改標記檔、不要降級處理。
1. 確認在 repo 根目錄：有 `AGENTS.md` 或 `CLAUDE.md`。沒有 → 告訴使用者先跑 `/autoloop init`，結束。
2. 讀 `.loop-main.json`（可能不存在）。若 `sessionId` 不是自己（用 `get_session self` 取得）而且 `updatedAt` 在 **15 分鐘內** → 另一個主 session 可能還在跑。用 AskUserQuestion 問使用者要不要接手；要接手就 `touch STOP`、等 `.loop-round.pid` 消失（最多 40 分鐘，每 30 秒看一次）、`rm -f STOP`，再繼續；不接手就結束。
3. `get_session self` 看模型與強度。不是 Sonnet 5.5 / medium 就記住：之後**每輪摘要**加一句「主 session 目前 <模型>/<強度>，建議 Sonnet 5.5 / medium，請在模型選單切換」。只提醒，不阻擋（session 不能改自己的模型）。
4. `bash $RR sweep` 清掉殘留程序與死掉的 lock。回 BUSY 代表有輪次在跑：等它結束（看 `.loop-round.pid` 消失）再繼續。
5. 回使用者一行：repo、目前 PLAN 最上面的 TODO、NEEDS-USER 有幾個 OPEN、主 session 模型。然後進入迴圈。

## 每一輪

1. 寫 `.loop-main.json`：`{"sessionId":"<self>","updatedAt":"<ISO>","round":<n>}`。
2. 挑角色（純字串比對，不做判斷）。各 repo 的項目標題格式不同（`### NU-001 … — OPEN — AUTH`、`## NU-003 … — OPEN · AUTH · blocks: …` 都有），所以只認「標題行裡有 OPEN」：
   `grep -cE '^#{2,4} +NU-[0-9]+.*\bOPEN\b' docs/progress/NEEDS-USER.md`（路徑依 repo 的指令檔）
   結果 > 0 → `fable`；= 0 → `opus`。開場第一次先用 `grep -n 'OPEN'` 看一眼格式，確認上面的樣式有抓到該 repo 的項目行。
3. 先把標題改成 `▶ loop <repo> · 第n輪 <role> 進行中`（見「側欄狀態」），再用 Bash **背景執行**：`bash $RR <role>`。然後結束這個 turn，只說一句「第 n 輪（<role>）進行中」。工作者結束時你會自動被叫醒；在那之前不要輪詢、不要 sleep。
4. 被叫醒後，讀**最新一個** `logs/loop/*.summary`（一行）。需要細節時最多再讀該輪 `.json` 的 `.result` 前 20 行，**不要**把整個 JSON 讀進上下文。
5. 以檔案為準再查一次狀態：再 grep 一次 OPEN；`git status --porcelain`；`ls STOP .loop.lock .loop-round.pid 2>/dev/null`。摘要說 CONTINUE 但 grep 到 OPEN，照 OPEN 處理。
6. 跑 `bash <assets>/ctx-usage.sh 30` 取得自己的上下文百分比（它讀自己的 transcript 最後一筆 usage，近似值即可）。
7. 依下表決定：

| 狀況 | 動作 |
|---|---|
| CONTINUE，沒有 OPEN，上下文未超標 | 留一行摘要，回到 1 |
| 有 OPEN（決策輪留下的 AUTH）或 ASK_USER | **通知並停**：列出每個 OPEN 項目的 ID、標題、supervisor 建議；不開下一輪 |
| 上下文 ≥ 30% | **通知並停**：說明「主 session 上下文約 xx%，建議開新 session 執行 `/autoloop run` 接續」。若同時有 AUTH 待決，**併成一則通知**。使用者說繼續 → 回到迴圈，之後每輪摘要加一句「上下文約 xx%，已超過 30%」，不再重複通知 |
| ERROR 或 TIMEOUT 或 exit≠0 | 第一次：留摘要，回到 1（下一輪的開場檢查會因停止記錄或髒工作樹而停下並寫 NEEDS-USER，之後自然走決策輪）。**連續第二次**：通知並停 |
| STOPPED（STOP 檔） | STOP 是使用者放的 → 走「收掉」。不是（決策輪殘留）→ 等 60 秒再開一輪；再 STOPPED 就通知並停 |
| INTERRUPTED | 是你自己 TaskStop 的 → 照使用者指令處理；否則通知並停 |
| `denials > 0` | 摘要只列數量，不停。JSON 的 `permission_denials` 分不出是 auto 模式分類器擋的，還是 repo 自己的 hook（例如子代理的唯讀 Bash 白名單）擋的；唯讀指令（grep、git diff、node -e）被擋幾乎都是後者，屬 repo 的 TECH 問題。連續三輪都有時，把被擋的指令抄幾條給使用者看，**不要建議改任何 settings** |

8. **摘要固定一行**，例如：
   `#7 opus 48s $0.11 CONTINUE — T-04 完成（dc5e64b）| OPEN=0 ctx=12%`
   每輪只留這一行，不要複述工作者的回報。欄位依序：輪次、角色（opus＝實作輪、fable＝決策輪）、工作者耗時、該輪 API 費用、工作者回報的 LOOP-STATUS、一句話、檔案核對結果（OPEN 數）、主 session 上下文百分比。

## 側欄狀態（讓使用者一眼看出在跑還是停了）

用 `set_session_title`（session_id "self"，不需核准）在每次狀態改變時改標題，格式固定：
- 開工或下一輪開始：`▶ loop <repo> · 第n輪 <opus|fable> 進行中`
- 停下等使用者：`⏸ loop <repo> · 等你：<一句，例如 NU-011 AUTH / 上下文 31%>`
- 連續錯誤、逾時停下：`⚠ loop <repo> · <原因>`
- 收掉：`■ loop <repo> · 已結束（n 輪）`
停下等使用者時，另外呼叫 `set_unread`（session_id "self"，unread true）讓側欄出現藍點；使用者回話後呼叫 `set_unread` false 清掉。這兩個工具是延後載入的，第一次用前先 `ToolSearch` 查 `select:mcp__ccd_session_mgmt__set_session_title,mcp__ccd_sidebar__set_unread`。

## 通知

用 `PushNotification` 工具（status proactive）。它是**延後載入**的工具，第一次用之前先 `ToolSearch` 查 `select:PushNotification` 載入，再呼叫。訊息一行、200 字內、先講要做的事：
`[<repo>] loop 停：NU-002 AUTH 待決（建議 b 保留）· 上下文 34%，建議換 session`
只在「停下等使用者」時發，一次停只發一則，**每次停下都一定要呼叫**，不要自行判斷使用者在不在：使用者就在對話裡時工具會自己略過並回報「not sent」，那是正常結果。在對話裡也要把同樣的內容寫出來。

## 沒有桌面 app 工具時（純 CLI、其他環境）

開場用 `ToolSearch` 查 `select:mcp__ccd_session_mgmt__get_session,mcp__ccd_session_mgmt__set_session_title,mcp__ccd_sidebar__set_unread,PushNotification`，查不到的就代表不在桌面 app：
- 標題與藍點：跳過。
- 自己的模型與強度：用 `ctx-usage.sh` 輸出的 `model=` 欄位代替 `get_session`。
- 通知：改用 `LOOP_NOTIFY_CMD` 環境變數（若有設，執行它並把訊息當第一個參數）；沒設就用系統通知：macOS `osascript -e 'display notification "<訊息>" with title "loop"'`，Linux `notify-send loop "<訊息>"`。都不可用就只在對話裡寫。
- 其餘流程完全相同。

## 使用者回答 AUTH 之後

使用者在這個對話裡回答。你把決定寫進 NEEDS-USER：該項改 `RESOLVED`，「使用者決定」欄填內容與日期；若決定改變切片範圍，先更新它擋住的 PLAN 項目。寫入遵守 repo 的 Supervisor 規則：先 `touch STOP`，確認 `.loop-round.pid` 與 `.loop.lock` 都不存在，只 `git add` 明確路徑，純文件 commit（`docs:` 前綴），`rm -f STOP`。然後回到迴圈（下一輪實作輪會把 RESOLVED 套用成 APPLIED）。不確定使用者意思就再問一次，不要猜。

## 使用者指令

- **「停」**：不開下一輪；有輪次在跑就讓它做完，結束後留摘要，停下。
- **「立刻停」**：對背景的 run-round 用 TaskStop（它會把工作者整組殺掉並清理），再跑 `bash $RR sweep`，留摘要，停下。
- **「收掉」／「結束」**：立刻停 + sweep + `rm -f .loop-main.json` + 最後摘要（本次共幾輪、commit 範圍、剩餘 OPEN）。之後不再排任何輪次。
- **「繼續」**：回到「每一輪」第 1 步。
- 使用者說要換 session：告訴他在新 session 執行 `/autoloop run`，新 session 會看到 `.loop-main.json` 並接手；本 session 做「收掉」。

## 鐵律

- 每輪只留一行摘要；不讀整個 JSON；不讀大型歷史文件。
- 不改程式碼、不跑 gates、不 push、不建立排程任務、不改任何 settings。
- 不替使用者做 AUTH 決定，也不因為「看起來很明顯」就跳過通知。
- 一個 repo 同時只有一個主 session、一個工作者；`.loop-round.pid` 回 BUSY 就等，不強殺。
- 門檻、模型、逾時都是 `run-round.sh` 與本檔的參數，不在對話裡臨時改。
