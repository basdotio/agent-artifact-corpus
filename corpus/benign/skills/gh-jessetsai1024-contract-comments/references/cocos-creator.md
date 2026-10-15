# Cocos Creator 專屬規則

疊在 `typescript.md` 之上；本檔只講 Cocos Creator 專案才有的細節。
若環境裡有處理 Cocos 序列化檔的 skill，例如 `cocos-creator-files`，
動到 .prefab、.scene、.meta 之前先載入它，那是另一套規矩。

## @property 欄位算非 private

掛 `@property` 的欄位會出現在編輯器 Inspector、也會序列化進 prefab 與 scene，
等於對外契約，不管它有沒有底線開頭。

契約寫：誰在編輯器接線、可不可以為 null、什麼時候會被讀、改值要不要重新整理畫面。

底線開頭的 `@property` 欄位 Inspector 預設隱藏但仍序列化；
契約要說明它是隱藏的，避免下一個人以為沒接線。

## 【生命週期】段要寫 Cocos 的鉤子

元件的 onLoad、start、onEnable、onDisable、onDestroy 各在什麼時候跑，
哪些成員 onLoad 之前不能叫、哪些快取在 onLoad 才建。

父節點在 onLoad 內把子節點設成 `active = false`，子元件的 onLoad 不會跑。
這種陷阱的「呼叫端該怎麼做」寫在【何時能呼叫】，因果與踩過的實例寫 AI-NOTES。

## 【事件】段要寫時機

Cocos 的回呼常常不是同步的：
`scheduleOnce` delay 為 0 是下一幀；tween 的第一次 step 不推進；
計時器回呼裡開的 tween 本幀不 tick。
契約要寫清楚「同步」「下一幀」「動畫結束時」，別只寫「會發事件」。

## JSON 資產放不了註解

.prefab、.scene、.meta、.anim 是 JSON，沒有註解。
關於它們的備忘寫進對應元件 .ts 的 AI-NOTES，並註明是哪個 prefab 或 scene；
沒有對應 .ts 的資產，備忘留在記憶檔。

手刻的 test scene .ts 也是程式碼，同規矩。

## 驗證

- 用 Cocos 編輯器自帶的 tsc，在 Creator 安裝目錄的 typescript/lib 下。
- 專案 tsconfig 的 `ignoreDeprecations` 值若 tsc 不接受，會一檔未檢就退出；
  用 CLI 參數覆蓋成 `--ignoreDeprecations 5.0`。
- 引擎 cc.d.ts 與 jsb.d.ts 吐出來的殘留錯誤是雜訊，只看自己的檔。
