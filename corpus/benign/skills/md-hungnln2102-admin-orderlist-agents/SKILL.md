---
name: admin_store Project Knowledge
description: >
  Kiến thức nền tảng về project admin_store: quy ước code, cấu trúc DB, 
  các service Adobe automation, scheduler tasks và conventions chung.
  Đọc file này trước khi làm bất kỳ task nào trong project này.
---

# admin_store — Project Knowledge Base

## 📁 Cấu Trúc Backend

```
admin_orderlist/backend/src/
  config/
    dbSchema.js       ← ĐỌC TRƯỚC: toàn bộ table/column constants của mọi schema DB
  utils/
    statuses.js       ← ORDER_STATUS constants — LUÔN DÙNG STATUS.* thay vì string literal
    logger.js         ← Winston logger dùng chung
  db/
    index.js          ← Knex instance (db) — dùng cho mọi query
  services/
    adobe-http/       ← HTTP/Browser functions: autoDeleteUsers, addUsersWithProduct (v1)
    adobe-renew-v2/   ← Playwright browser flows (V2): addUsersWithProductV2, autoAssignFlow
    userAccountMappingService.js  ← CRUD bảng user_account_mapping
  scheduler/
    index.js          ← Đăng ký tất cả cron jobs
    tasks/            ← Mỗi task là 1 file, export createXxxTask() factory function
  routes/
    schedulerRoutes.js ← Manual trigger endpoints
  controllers/
    RenewAdobeController.js ← runCheckForAccountId() — crawl snapshot 1 account
```

---

## 🗄️ Database Conventions

### Schema: `system_automation`
- **`accounts_admin`** — Tài khoản admin Adobe org
- **`product_system`** — Mapping variant_id → system_code (renew_adobe, fix_adobe_edu...)
- **`user_account_mapping`** — Mapping user_email ↔ id_order ↔ adobe_account_id

### Schema: `orders`
- **`order_list`** — Toàn bộ đơn hàng

### ⚠️ QUAN TRỌNG: Cách dùng DB Schema
```js
// LUÔN dùng constants từ dbSchema.js — KHÔNG hardcode tên table/cột
const {
  SCHEMA_RENEW_ADOBE,
  RENEW_ADOBE_SCHEMA,
  SCHEMA_ORDERS,
  ORDERS_SCHEMA,
  tableName,
} = require("../config/dbSchema");

const TABLE = tableName(RENEW_ADOBE_SCHEMA.USER_ACCOUNT_MAPPING.TABLE, SCHEMA_RENEW_ADOBE);
const COLS  = RENEW_ADOBE_SCHEMA.USER_ACCOUNT_MAPPING.COLS;
```

---

## 📊 Bảng `user_account_mapping` — Schema đầy đủ (sau migration 2026-03-19)

| Column | Type | Nullable | Default | Ý nghĩa |
|---|---|---|---|---|
| `id` | integer | NO | auto-increment | PK |
| `user_email` | text | NO | — | Email khách hàng |
| `id_order` | text | NO | — | Mã đơn từ order_list.id_order |
| `adobe_account_id` | integer | YES | null | FK → accounts_admin.id |
| `assigned_at` | timestamptz | NO | now() | Lần đầu ghi mapping |
| `updated_at` | timestamptz | NO | now() | Lần cập nhật gần nhất |
| `product` | boolean | NO | false | User đã được assign product trong org chưa |
| `url_active` | text | YES | null | URL auto-assign nếu product=false |

**COLS constants:**
```js
COLS.PRODUCT    = "product"
COLS.URL_ACTIVE = "url_active"
```

---

## 🔖 Order Status Constants — LUÔN DÙNG STATUS.* 

```js
const { STATUS } = require("../utils/statuses");
// hoặc: require("../../utils/statuses")

STATUS.UNPAID          // "Chưa Thanh Toán"
STATUS.PROCESSING      // "Đang Xử Lý"       ← active
STATUS.PAID            // "Đã Thanh Toán"     ← active
STATUS.CANCELED        // "Hủy"
STATUS.REFUNDED        // "Đã Hoàn"
STATUS.PENDING_REFUND  // "Chờ Hoàn"
STATUS.EXPIRED         // "Hết Hạn"
STATUS.RENEWAL         // "Cần Gia Hạn"       ← active
```

**Active statuses** (đơn còn hiệu lực):
```js
const ACTIVE_STATUSES = [STATUS.PROCESSING, STATUS.PAID, STATUS.RENEWAL];
```

**KHÔNG BAO GIỜ** hardcode string status trong code logic (comment/JSDoc thì OK).

---

## 🤖 Adobe Automation — Luồng & Services

### Jobs hiện tại (scheduler/index.js)
| Cron | Job | Mô tả |
|---|---|---|
| `00:01` | `updateDatabaseTask` | Cập nhật trạng thái đơn hàng theo ngày |
| `23:30` | `cleanupExpiredAdobeUsersTask` | Xóa user hết hạn khỏi org |
| `05:00` + `12:00` | `renewAdobeCheckAndNotifyTask` | Check org, xóa user expired, reassign, notify |
| `07:00` | `notifyFourDaysRemainingTask` | Thông báo còn 4 ngày |
| `18:00` | `notifyZeroDaysRemainingTask` | Thông báo hết hạn hôm nay |

### Services Adobe
| Service | Method | Dùng cho |
|---|---|---|
| `adobe-http` | `autoDeleteUsers(email, pwd, [emails], opts)` | Xóa user khỏi org (browser V1) |
| `adobe-http` | `addUsersWithProduct(email, pwd, [emails], opts)` | Add user + product (V1 - cũ) |
| `adobe-renew-v2` | `addUsersWithProductV2(email, pwd, [emails], opts)` | Add user + product (V2 Playwright - ưu tiên dùng) |
| `adobe-renew-v2` | `getOrCreateAutoAssignUrlWithPage(page, orgId, email, pwd, opts)` | Lấy/tạo URL auto-assign |
| `RenewAdobeController` | `runCheckForAccountId(accountId)` | Crawl lại snapshot 1 account |

### userAccountMappingService — API
```js
syncOrdersToMapping()                          // Đồng bộ đơn hàng → mapping (insert + xóa hết hạn)
lookupAndRecordIfNeeded(emails, adobeAccId)    // Add mapping sau khi assign user
recordUsersAssigned(emails, idOrder, accId)    // Ghi nhận user đã assign
removeMappingsForAccount(adobeAccountId)       // Xóa mapping khi account hết hạn
removeMappingsByOrders(idOrders)               // Xóa mapping theo đơn hàng
getMappingsForAccount(adobeAccountId)          // Lấy danh sách mapping theo account
getAccountForUser(userEmail)                   // Lấy accountId của 1 user
```

---

## 🏗️ Quy Ước Code — Scheduler Task

```js
// Pattern chuẩn cho mỗi task — factory function + closure
function createMyTask() {
  return async function myTask(trigger = "cron") {
    logger.info("[CRON] Bắt đầu job...", { trigger });
    try {
      // logic
    } catch (err) {
      logger.error("[CRON] Job thất bại", { error: err.message, stack: err.stack });
    }
  };
}
module.exports = { createMyTask };
```

---

## ⚠️ Quy Tắc Bắt Buộc Khi Sửa Code

1. **Không hardcode** string status → dùng `STATUS.*`
2. **Không hardcode** tên table/cột → dùng `COLS.*` + `tableName()`
3. Mỗi scheduler task xuất `createXxxTask()` factory
4. Delay `await new Promise(r => setTimeout(r, 3000))` giữa các account để tránh rate limit Adobe
5. Luôn `try/catch` riêng từng account trong vòng lặp — lỗi 1 account không dừng cả job
6. `addUsersWithProductV2` (V2) ưu tiên hơn `addUsersWithProduct` (V1)
7. Sau khi add user → gọi `runCheckForAccountId(accId)` để crawl lại snapshot mới nhất

---

## 🔄 RPM Protocol — Adobe Auto Fix (Đang Implement)

**Mục tiêu**: Task tổng hợp `adobeAutoFixTask` tự động fix user Adobe bị lỗi.

**Trạng thái hiện tại:**
- ✅ B1: Check tài khoản org — `runCheckForAccountId` 
- ✅ B2: Xóa user hết hạn — `cleanupExpiredAdobeUsersTask`
- ✅ B3: Cột `product` + `url_active` — **migration đã chạy 2026-03-19**
- ✅ B4: Xóa mapping đơn hết hạn — `syncOrdersToMapping` 
- ⏳ B5: Re-add user (product=false) → `addUsersWithProductV2`
- ⏳ B6: Crawl snapshot sau add → `runCheckForAccountId`
- ⏳ B7: Update `product` status + lưu `url_active`
- ⏳ B8: Task tổng hợp `adobeAutoFixTask.js`
