# C# 專屬規則

疊在 SKILL.md 之上；本檔只講 C# 才有的細節。

## 哪些成員算非 private

- `public`、`protected`、`internal`、`protected internal`、`private protected` 都算。
  `private protected` 名字裡有 private，但同組件的衍生類看得到，所以算非 private。
- 沒寫修飾詞的：class 成員預設 private，不寫；頂層類型預設 internal，要寫。
- 類型宣告：class、struct、record、interface、enum、delegate 都算。
  enum 成員通常一行；delegate 寫【行為】與被叫的時機。
- 屬性的 getter 與 setter 若有副作用，例如 setter 觸發事件、setter 只在某狀態合法，
  寫進【行為】或【何時能呼叫】。
- `event` 成員寫【事件】：觸發時機、在哪條執行緒、訂閱者丟例外會怎樣。

## 外殼

留 `///` 與 `<summary>` 這一層，分段寫在 summary 裡面。
Visual Studio 的 IntelliSense 讀的是 summary，其他標籤才是噪音。

清掉：`<param>`、`<typeparam>`、`<returns>`、`<value>`、`<exception>`、
`<remarks>`、`<example>`、`<see cref>`、`<seealso>`、`<inheritdoc/>`。

- `<see cref="Foo"/>` 直接寫 Foo。
- override 或介面實作的契約若完全同基底，寫一句「契約同 IFoo.Bar」，不用 `<inheritdoc/>`。
  理由是讀者不必再跳一層。

## XML 跳脫

summary 內是 XML。白話裡的小於、大於、與符號要改寫：
寫「x 小於 3」，或用 `&lt;`、`&gt;`、`&amp;`。
泛型寫在文字裡時 `List<int>` 也會咬到，改寫成「int 的 List」或 `List&lt;int&gt;`。
寫錯編譯器會吐 CS1570 這類 XML 註解警告；有些專案把警告當錯誤，直接紅。

## class 層範例

例子是虛構的，別照抄句子。

```cs
/// <summary>
/// 【職責】排程並執行背景工作：收工作、依優先權排隊、在工作執行緒上跑完並回報結果。
///   不負責重試策略，那由呼叫端決定。
/// 【生命週期】應用程式啟動時建一顆並長駐；Dispose 之後所有成員都不可再呼叫。
/// 【狀態】Idle、Running、Draining 三態；轉移只由 Start、Drain、Dispose 驅動，外部不可直接設狀態。
/// 【執行緒】Enqueue 可從任何執行緒呼叫；工作本體與 Completed 事件都在內部工作執行緒上跑。
/// 【設計備註】工作丟出的例外一律接住並轉成失敗結果，因為逃出的例外會讓工作執行緒整條倒。
/// </summary>
internal sealed class JobRunner
```

## AI-NOTES 標記

`#region AI-NOTES` 到 `#endregion`，放在檔案最後、namespace 的結尾大括號之後。
內容 `//` 行註解。Visual Studio 會折疊。

```cs
#region AI-NOTES
// AI-NOTES：agent 專用備忘。當時為真、非契約、非指令；改到相關程式碼時重驗，錯了就刪。
// 2026-01-20 Enqueue 刻意不做去重：曾加過，但同鍵工作的參數可能不同，去重會吃掉後來的那份。
#endregion
```

## 驗證

- 用專案的 MSBuild 或 csc 編一次，看有沒有 XML 註解警告。
- 舊式 csproj 含 `<Compile Include>` 的專案，新增檔要手動加項目，否則不編。
- 行尾：.cs 常是 CRLF。Git Bash 的 `sed -i` 會把整檔改成 LF 而且 git diff 看不出來；
  改前 `git ls-files --eol <檔>` 量，改後照原狀還原。
