---
name: postgresql
description: PostgreSQL 作為遷移目標時的專屬指引。包含 MSSQL → PostgreSQL 類型映射、連線格式、大小寫敏感處理、Sequence 同步、COPY 協議、已知問題。當處理 PostgreSQL 相關的遷移、連線、Schema 或資料問題時使用。
---

# PostgreSQL 遷移目標指引

## 連線字串格式

```
postgres://user:pass@host:port/dbname?sslmode=disable
```

## 關鍵程式碼

| 功能 | 檔案 |
|------|------|
| PostgreSQL 連線 | `internal/connection/postgres.go` |

## 類型映射速查（MSSQL → PostgreSQL）

| MSSQL | PostgreSQL |
|-------|------------|
| int | INTEGER |
| bigint | BIGINT |
| bit | BOOLEAN |
| datetime | TIMESTAMP(3) |
| datetime2(n) | TIMESTAMP(n) (max 6) |
| varchar(n) | VARCHAR(n) |
| varchar(max) | TEXT |
| nvarchar(n) | VARCHAR(n) |
| uniqueidentifier | UUID |
| money | NUMERIC(19,4) |
| varbinary | BYTEA |
| int identity | SERIAL |

## 資料插入：COPY 協議

PostgreSQL 使用 COPY 協議進行高效批次插入：

```go
CopyFrom() // pgx 的 COPY 協議方法
```

## 注意事項

### 大小寫敏感

PostgreSQL 識別符預設轉小寫，含大寫的表名需用雙引號包裹：

```go
pgx.Identifier{tableName}.Sanitize() // 自動加雙引號
```

### Sequence 同步

遷移含 identity 欄位的表格後，需同步 sequence：

```go
qualifiedTable := fmt.Sprintf("%s.%s",
    pgx.Identifier{schema}.Sanitize(),
    pgx.Identifier{tableName}.Sanitize())
```

錯誤範例：`Failed to sync sequence for dbo.XXX: relation "dbo.xxx" does not exist`
原因：未用雙引號包裹表名，已修復於 `postgres.go` → `SyncSequence()`

### 主鍵重複

```
duplicate key value violates unique constraint
```

目標表已有資料時，需先清空或使用 `dropTargetIfExists` 選項。
