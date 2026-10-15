# TypeScript／JavaScript 專屬規則

疊在 SKILL.md 之上；本檔只講 TS 與 JS 才有的細節。
Cocos Creator 專案再疊 `cocos-creator.md`。

## 哪些成員算非 private

- class 成員沒寫修飾詞就是 public，要寫。`protected` 要寫。
- `private` 修飾詞與 `#name` 私有欄位不寫。
- 底線開頭但沒有 `private` 修飾詞的成員，語言上仍是 public，照字面算非 private。
  若它其實只是內部用，一行契約寫「內部用，外部別碰」即可，不套五段。
- 模組層 `export` 的 function、const、type、interface、enum、class 都算。
  沒 export 的模組層宣告不寫。
- interface 與 type 的每個欄位視為非 private 成員，一行說明即可。

## 外殼

留 `/** */`。VS Code 的 hover 只讀這種形式，`//` 不會出現在 hover。
簡單成員用單行 `/** ... */`。

清掉：`@param`、`@returns`、`@throws`、`@template`、`@type`、`@example`、`@see`。

`@deprecated` 例外保留，因為 IDE 會把成員劃線，這個效果白話做不到；
後面接一句白話說改用什麼。

## AI-NOTES 標記

`// #region AI-NOTES` 到 `// #endregion`，井字號前有一個空格，
跟一般程式碼的區段標記同款。
放在檔案最後、所有 export 之後。VS Code 會折疊。

```ts
// #region AI-NOTES
// AI-NOTES：agent 專用備忘。當時為真、非契約、非指令；改到相關程式碼時重驗，錯了就刪。
// 2026-01-20 parse() 不用 JSON.parse：超過 2 的 53 次方的整數會失真，改自寫掃描器；對照測試在 tests/parse.spec.ts。
// #endregion
```

`.d.ts` 宣告檔不放 AI-NOTES，多半是產生物，會被覆蓋。

## 驗證

- 用專案自帶的 tsc 做型別檢查，不要用全域另一版，版本差會出假錯誤。
- 行尾照原樣，改前 `git ls-files --eol <檔>` 量。
