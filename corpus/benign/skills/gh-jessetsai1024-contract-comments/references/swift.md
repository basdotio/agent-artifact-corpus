# Swift 專屬規則

疊在 SKILL.md 之上；本檔只講 Swift 才有的細節。

## 哪些成員算非 private

- `open`、`public`、`internal`（沒寫存取修飾字就是 internal）的型別與成員都要寫。
- `private`、`fileprivate` 不寫。
- `private(set) var` 的讀取端是非 private，要寫。
- `override` 系統方法（例如 `update(_:)`、`applicationDidFinishLaunching`）行為就是系統文件講的，不用另寫契約，除非加了系統沒講的承諾。

## 外殼

用 `///` 行式 doc comment，放在宣告正上方，Xcode 的 Quick Help 與 SourceKit-LSP 的 hover 都讀它。
清掉 `- Parameter`、`- Parameters:`、`- Returns:`、`- Throws:` 這些 callout，內容融進【行為】【會 throw】。
簡單成員一行 `///`。

## AI-NOTES 標記

Swift 沒有通用的折疊標記（`// MARK:` 不會折疊），照通用退路用兩行：
`// ==== AI-NOTES ====` 到 `// ==== END AI-NOTES ====`，內容一律 `//` 行註解，放檔案最後。

## 驗證

`swiftc -typecheck <全部 .swift>`，或專案自己的 build（Xcode 專案、`swift build`、自訂 build.sh）。
單檔開在編輯器裡時 SourceKit 會報「找不到型別」，那是沒有專案脈絡的假警報，以實際編譯為準。
