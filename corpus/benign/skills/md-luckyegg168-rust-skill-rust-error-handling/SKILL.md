---
name: rust-error-handling
description: >
  Rust 錯誤處理模式技能。涵蓋 Result<T,E> 與 Option<T> 模式、? 運算子錯誤傳播、
  thiserror 2.0 自訂錯誤類型、anyhow 應用層錯誤、自訂 Error trait 實作、
  From trait 轉換、error chain、panic 與 unwrap 使用時機、錯誤處理最佳實踐。
  觸發關鍵詞：Rust error handling, Result, Option, thiserror, anyhow,
  ? operator, unwrap, expect, Error trait, From conversion, error propagation,
  custom error type, error chain, panic
---

# Rust 錯誤處理 (rust-error-handling)

## 適用場景
- 設計函式的錯誤回傳類型
- 選擇 thiserror（library）vs anyhow（application）
- 實作自訂 Error enum
- 使用 ? 運算子串接錯誤傳播
- 將 panic/unwrap 替換為正確的錯誤處理

## 核心知識

### 錯誤處理策略選擇
| 場景 | 推薦方案 |
|------|---------|
| Library crate | `thiserror` 定義具體 Error enum |
| Application crate | `anyhow::Result` 快速開發 |
| 原型開發 | `.unwrap()` / `.expect("msg")` |
| 不可能失敗 | `.unwrap()` 加註解說明為何安全 |
| 需要 backtrace | `anyhow` 或 `color-eyre` |

### Result 與 Option 差異
- `Result<T, E>`：操作可能失敗，帶有錯誤資訊
- `Option<T>`：值可能不存在，無錯誤資訊
- `Option` 可透過 `.ok_or()` / `.ok_or_else()` 轉為 `Result`

### ? 運算子流程
```rust
fn foo() -> Result<T, MyError> {
    let val = some_operation()?; // 失敗時自動 return Err(e.into())
    Ok(val)
}
```
`?` 會自動呼叫 `From::from()` 轉換錯誤類型。

### thiserror vs anyhow 選擇原則
- **thiserror**：為呼叫端提供可 match 的具體錯誤 variant，適合 library
- **anyhow**：不需呼叫端區分錯誤種類，適合 application 頂層邏輯
- 同一專案可同時使用：library 模組用 thiserror，main/bin 用 anyhow

### 自訂 Error 的標準結構（thiserror 2.0）
```rust
use thiserror::Error;

#[derive(Debug, Error)]
pub enum AppError {
    #[error("描述訊息: {0}")]          // 位置參數
    VariantA(String),

    #[error("欄位: {field}")]          // 具名欄位
    VariantB { field: String },

    #[error("來源錯誤")]
    VariantC(#[from] std::io::Error),  // 自動 From 轉換

    #[error(transparent)]              // 透傳內部錯誤的 Display
    Other(#[from] anyhow::Error),
}
```

### 手動實作 Error trait（無 thiserror）
```rust
use std::fmt;

#[derive(Debug)]
pub enum MyError {
    NotFound(String),
    Internal(Box<dyn std::error::Error + Send + Sync>),
}

impl fmt::Display for MyError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NotFound(id) => write!(f, "找不到: {id}"),
            Self::Internal(e) => write!(f, "內部錯誤: {e}"),
        }
    }
}

impl std::error::Error for MyError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Internal(e) => Some(e.as_ref()),
            _ => None,
        }
    }
}
```

### Option 常用轉換方法
```rust
let opt: Option<i32> = Some(42);

// Option -> Result
let res = opt.ok_or("值不存在");            // Result<i32, &str>
let res = opt.ok_or_else(|| make_error()); // 延遲建構錯誤

// Option 安全存取
let val = opt.unwrap_or(0);                // 預設值
let val = opt.unwrap_or_default();         // Default trait
let val = opt.unwrap_or_else(|| compute());

// Option 組合
let mapped = opt.map(|v| v * 2);           // Some(84)
let flat  = opt.and_then(|v| checked_div(v, 2));
let alt   = opt.or(Some(99));              // 備選值
```

### panic 與 unwrap 的正確使用時機
1. **測試程式碼**：`unwrap()` 可接受，失敗即測試失敗
2. **邏輯上不可能失敗**：加 `// SAFETY:` 或 `expect("原因")` 說明
3. **原型開發**：先用 unwrap，後續重構為 Result
4. **程式初始化**：設定檔載入失敗可 panic（無法繼續運行）
5. **永遠不要**：在 library 的公開 API 中使用 unwrap

### anyhow 常用功能
```rust
use anyhow::{Context, Result, bail, ensure};

// context(): 附加上下文訊息
let val = operation().context("操作描述")?;

// with_context(): 延遲建構上下文（效能更好）
let val = operation()
    .with_context(|| format!("處理 {} 時失敗", id))?;

// bail!: 直接回傳錯誤
bail!("無法處理: {reason}");

// ensure!: 條件斷言
ensure!(count > 0, "數量必須大於零，當前為 {count}");

// 錯誤鏈遍歷
if let Err(e) = run() {
    for cause in e.chain() {
        eprintln!("原因: {cause}");
    }
}
```

## 程式碼範例

### Basic: Result 與 Option 基礎
```rust
use std::num::ParseIntError;

/// 解析字串為正整數（回傳 Result）
fn parse_positive(s: &str) -> Result<u32, String> {
    let n: i64 = s.parse().map_err(|e: ParseIntError| e.to_string())?;
    if n > 0 {
        Ok(n as u32)
    } else {
        Err(format!("預期正整數，但得到 {n}"))
    }
}

/// 從 Option 轉換為 Result
fn first_element(data: &[i32]) -> Result<i32, &'static str> {
    data.first().copied().ok_or("陣列為空")
}

fn main() {
    // Result 的 match 處理
    match parse_positive("42") {
        Ok(n) => println!("解析成功: {n}"),
        Err(e) => eprintln!("解析失敗: {e}"),
    }

    // 方法鏈: map, and_then, unwrap_or
    let result = parse_positive("10")
        .map(|n| n * 2)
        .unwrap_or(0);
    println!("結果: {result}");

    // Option 方法鏈
    let names = vec!["Alice", "Bob"];
    let upper = names.first()
        .map(|s| s.to_uppercase())
        .unwrap_or_default();
    println!("第一個名字: {upper}");
}
```

### Intermediate: thiserror 自訂錯誤（Library 用）
```rust
use thiserror::Error;

#[derive(Debug, Error)]
pub enum DatabaseError {
    #[error("連線失敗: {0}")]
    ConnectionFailed(String),

    #[error("查詢逾時（{timeout_secs} 秒）")]
    QueryTimeout { timeout_secs: u64 },

    #[error("記錄未找到: id={id}")]
    NotFound { id: u64 },

    #[error("IO 錯誤")]
    Io(#[from] std::io::Error),
}

#[derive(Debug, Error)]
pub enum UserServiceError {
    #[error("資料庫錯誤: {0}")]
    Database(#[from] DatabaseError),

    #[error("驗證失敗: {0}")]
    Validation(String),
}

fn find_user(id: u64) -> Result<String, DatabaseError> {
    if id == 0 {
        Err(DatabaseError::NotFound { id })
    } else {
        Ok(format!("User-{id}"))
    }
}

fn get_user_display(id: u64) -> Result<String, UserServiceError> {
    let name = find_user(id)?; // 自動轉換 DatabaseError -> UserServiceError
    if name.is_empty() {
        return Err(UserServiceError::Validation("名稱不可為空".into()));
    }
    Ok(format!("顯示名稱: {name}"))
}
```

### Advanced: anyhow 應用層 + context
```rust
use anyhow::{Context, Result, bail, ensure};

fn load_config() -> Result<(u16, String)> {
    let port: u16 = std::env::var("APP_PORT")
        .context("APP_PORT 未設定")?
        .parse()
        .context("APP_PORT 必須是有效埠號")?;

    ensure!(port >= 1024, "埠號 {port} 不可小於 1024");

    let db_url = std::env::var("DATABASE_URL")
        .context("DATABASE_URL 未設定")?;

    if db_url.is_empty() {
        bail!("DATABASE_URL 不可為空");
    }

    Ok((port, db_url))
}

fn init_app() -> Result<()> {
    let (port, db_url) = load_config()
        .context("載入設定失敗")?;
    println!("啟動於 :{port}，資料庫: {db_url}");
    Ok(())
}
```

## 常見錯誤對照表

| 錯誤訊息 | 原因 | 修復方式 |
|----------|------|---------|
| `the ? operator can only be used in a function that returns Result or Option` | 在 main 或非 Result 函式中使用 ? | 將回傳改為 `Result<(), E>` 或用 `match` |
| `the trait From<A> is not implemented for B` | ? 嘗試轉換不相容的錯誤類型 | 實作 `From<A> for B` 或用 `map_err()` |
| `cannot use the ? operator in a function that returns ()` | main() 沒有回傳 Result | 改為 `fn main() -> anyhow::Result<()>` |
| `this function should return Result or Option to accept ?` | 閉包中使用 ? | 在閉包內用 match 或改用 `.map()` 鏈 |
| `use of moved value` after unwrap in match arm | match arm 中 unwrap 消耗了值 | 改用 `ref` 或 `as_ref()` |
| `expected Result, found Option` | 混用 Result 與 Option | 用 `.ok_or()` 將 Option 轉為 Result |
| `error[E0277]: the size ... cannot be known at compilation time` | 回傳 `dyn Error` 未裝箱 | 改為 `Box<dyn Error>` 或用具體類型 |

## Cargo.toml 依賴模板
```toml
[dependencies]
thiserror = "2.0"       # Library: 自訂 Error derive
anyhow = "1.0"          # Application: 彈性錯誤處理
color-eyre = "0.6"      # Application: 美化錯誤輸出（替代 anyhow）

[dev-dependencies]
assert_matches = "1.5"  # 測試錯誤 variant
```

## 參考來源
- [The Rust Book Ch.9 - Error Handling](https://doc.rust-lang.org/book/ch09-00-error-handling.html)
- [thiserror 2.0 docs](https://docs.rs/thiserror/2/thiserror/)
- [anyhow docs](https://docs.rs/anyhow/latest/anyhow/)
- [Rust by Example - Error Handling](https://doc.rust-lang.org/rust-by-example/error.html)
- [Designing error types in Rust](https://mmapped.blog/posts/12-rust-error-handling.html)
