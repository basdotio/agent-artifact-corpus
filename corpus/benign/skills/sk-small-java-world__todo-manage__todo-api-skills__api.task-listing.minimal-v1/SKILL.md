---
name: タスク一覧の軽量取得（段階取得の前段）
description: >
  FastAPI TODO API で一覧取得時に hid/title/status/updated_at のみに絞り、
  詳細は expand/別APIで段階取得するための Skill。LLM のコンテキストを圧迫しない運用を徹底する。
---

# 使い方
- 一覧は `fields=hid,title,status,updated_at` を必ず付与する
- 詳細が必要になった場合のみ `/tasks/{hid}?expand=comments,links` を後段で呼ぶ

## 手順
1. `GET {base_url}/tasks?type={type}&status={status}&limit={limit}&fields=hid,title,status,updated_at`
2. さらに情報が必要なら `GET /tasks/{hid}?expand=comments,links`

## 例
- `examples/list.http` を参照
