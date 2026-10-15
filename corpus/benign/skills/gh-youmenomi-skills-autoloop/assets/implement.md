這是自動開發 loop 的一個實作輪。你是這一輪唯一的 writer，沒有人在看，不要問問題，不要等待核准；做不到的事就寫進 NEEDS-USER 然後結束。

依目前資料夾的 AGENTS.md（或 CLAUDE.md）的 loop 協定執行**一輪**：
1. 先跑協定規定的開場檢查（STOP 檔、loop:start 或等價腳本、lock）。它說本輪不該開工就立即結束，不寫任何檔、不 commit。
2. 讀 STATUS、PLAN、NEEDS-USER。有 RESOLVED 的 NEEDS-USER 項目先套用並改 APPLIED。
3. 只做 PLAN 最上面一個 TODO，做完就停，不接續下一項，不順手修別的。
4. 跑該項目適用的 gates；通過才 commit、寫切片記錄、更新進度檔；失敗或遇到任何停止條件就依協定寫停止記錄後結束，不硬做。
5. 結束前確認：沒有留下任何你啟動的背景程序（dev server、watcher、長駐 gate），lock 檔已移除。
6. 不 push，不開 PR，不改全域設定，不建立排程任務。

回覆最後一行**固定**是這個格式，前面不要加其他符號：
`LOOP-STATUS: CONTINUE|ASK_USER|STOPPED|ERROR — <一句話摘要>`
- CONTINUE：切片完成並已 commit。
- ASK_USER：有 AUTH 類項目在 NEEDS-USER 等使用者決定。
- STOPPED：因 STOP 檔或另一輪進行中而未開工。
- ERROR：gate 失敗或其他停止條件，已寫停止記錄。
