# Stolas Thread：沿一條脈絡的系統化教學 skill

Stolas Thread 是一個 Claude skill，適用於使用者手上只有一個詞的情況。它把一個專有名詞、縮寫或外文術語，或一篇國文課文、古典詩詞、文言文，沿「上游、本體、下游」的縱向脈絡展開成完整的學習單元。它先診斷學習者對該領域的基本認識，再用脈絡地圖同時安排「它怎麼運作」與「它從哪來、往哪去」，同層級的比較以表格附在節點中。所有討論持續整併成一份教材，結案後交由 stolas-print 產出附一頁重點的 PDF 學習筆記，教材附 Obsidian 可讀取的學科標籤。

## Stolas 系列

| 技能 | 起點 | 展開方式 |
|---|---|---|
| stolas-thread | 手上只有一個詞 | 一條線：AI 先排好脈絡地圖，縱向展開 |
| stolas-web | 手上可能有一張詞彙表 | 一張網：依使用者點名，攤成心智圖 |
| stolas-exam | 已有 thread 教材或 web 主檔 | 出題、批改、補測，結果寫回原檔 |
| stolas-print | 已結案的 thread 教材或 web 主檔 | 產出 PDF |

## 使用方式

訊息以 `/stolas-thread` (或全形 `／stolas-thread`) 開頭才會啟動，例如：

- `/stolas-thread Semaglutide`
- `/stolas-thread 杜甫〈登高〉`
- `/stolas-thread 我感覺台灣飲料店小品牌很多，為什麼沒有寡占`
- `/stolas-thread` 附上一張圖片，詢問「這是什麼」

單元開始後可以直接追問，或使用以下指令：

| 指令 | 作用 |
|---|---|
| 繼續教學 | 講解下一個節點 |
| 沒聽懂 | 換一種方式重講 (先畫圖，再拆步驟定位卡住的地方) |
| 生成全教材 | 把剩餘節點一次寫進教材後停下等待 |
| 結案 | 整理一頁重點，接著交給 stolas-print 產出 PDF |
| `/stolas-exam` | 期中或最終驗收 (由 stolas-exam 進行) |

## 檔案結構

```
stolas-thread/
├── SKILL.md                     主流程與教學規則
├── README.md                    本說明
├── LICENSE                      授權條款
└── references/
    ├── intake.md                多義詞、詞彙表轉介、婉拒、觀察查核、圖片辨識
    ├── context-map.md           脈絡地圖：深淺判定、欄位、權重
    ├── classical-text.md        經典文本單元
    ├── doc-template.md          教材模板、學科分類、一頁重點文字版
    ├── visual-toolkit.md        圖解的表徵選擇與繪圖規格
    └── mcq-design.md            診斷用選擇題的選項寫法
```

## 環境需求

- 需要開啟程式執行 (Code Execution) 功能，教材檔才能產生。PDF 的環境需求見 stolas-print。
- 有網路搜尋工具時，涉及數據、法規、時效資訊的內容會先查證再寫入。

## 致謝

Stolas 系列自第三版起的部分設計概念，參考自 Matt Pocock 的 [mattpocock/skills](https://github.com/mattpocock/skills) 倉庫 (MIT License)，主要是 `skills/productivity/` 中的 teach、wait-what、to-questionnaire 與 writing-for-agents。參考的範圍包括：以術語表作為已定義清單並統一用語、以作答證據判定掌握、誤解只收錄被更正過的錯誤、課程與參考資料分離、沒聽懂時換方式重講，以及撰寫 skill 時的正向描述、漸進揭露與單一規則來源等原則。

以上皆為概念參考，Stolas 系列的所有文字與程式均為重新撰寫，未複製原倉庫的內容。感謝原作者公開分享。

## 授權

本專案以 MIT License 釋出，詳見 [LICENSE](LICENSE)。
