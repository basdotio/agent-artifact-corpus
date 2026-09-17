---
name: RunPowerShell
description: 設定 PowerShell 的 UTF-8 編碼以避免中文亂碼，適用於 Copilot 啟動時的初始設定。
license: Complete terms in LICENSE.txt
---

# Copilot 啟動 PowerShell 初始設定

**等級**：基礎
**預估時間**：2-5 分鐘
**最後更新**：2026-01-06

## 學習目標

- 理解為何需要設定 PowerShell 的 UTF-8 編碼
- 學會執行初始設定指令
- 確保 Copilot 啟動 PowerShell 時中文顯示正常

## 快速開始

在 PowerShell 執行以下指令以設定 UTF-8 編碼：

```ps1
chcp 65001 > $null
$OutputEncoding = [Console]::OutputEncoding = [Console]::InputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['*:Encoding'] = 'utf8'
```

說明：切換代碼頁並設定輸入/輸出與 Cmdlet 預設編碼為 UTF-8。

## 驗證

```ps1
Write-Output "測試中文輸出：你好，世界！"
[Console]::OutputEncoding.EncodingName
```

## FAQ

**Q：為什麼需要執行這些指令？**
A：預設情況下，PowerShell 的編碼可能不是 UTF-8，導致中文顯示亂碼。這些指令確保輸入與輸出皆使用 UTF-8 編碼。

**Q：是否需要每次啟動都執行？**
A：若將這些指令加入 PowerShell Profile，則每次啟動時會自動執行，無需手動輸入。

## 參考資料

- https://learn.microsoft.com/zh-tw/powershell/
- https://learn.microsoft.com/zh-tw/powershell/module/microsoft.powershell.core/about/about_character_encoding

## 檢查清單

- [ ] 我已執行初始設定指令
- [ ] 我已驗證中文顯示正常
- [ ] （選用）我已將設定加入 PowerShell Profile