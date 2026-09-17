---
name: write-diary
description: /docs/diary/に日記を書く。
---

# 日記を書く

セッション中の開発内容、反省点、学びを記録する。

## 手順

1. 現在の日付を取得する

```bash
node .claude/skills/write-diary/get-date.js
```

出力例: `2025-01-13 14:30 JST`

2. `docs/diary-cc-logs/` にファイルがあるか確認する
   - ある場合: autocompact が走った証拠。これらのファイルを全て読み、圧縮前の会話内容 + 現在の会話コンテキストの両方を使って日記を書く
   - ない場合: 現在の会話コンテキストのみで日記を書く

3. `/docs/diary/YYYYMMDD.md` を作成または追記する

4. `/docs/diary/CLAUDE.md` のガイドラインに従って記述する

5. 日記の作成が完了したら `docs/diary-cc-logs/` 内のファイルを削除する（次回のログと混在しないようにクリーンアップ）
