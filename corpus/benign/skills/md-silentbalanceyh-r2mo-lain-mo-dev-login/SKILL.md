---
name: mo-dev-login
description: Develop comprehensive authentication module supporting 8+ enterprise-grade login methods including OAuth2/OIDC, with flexible selection based on requirements
version: 2.0.0
tags: [r2mo, dev, login, auth, authentication, jwt, ldap, oauth, oauth2, oidc, sms, email, wechat, wecom, captcha, qrcode]
repository: https://gitee.com/silentbalanceyh/r2mo-lain.git
---

# mo-dev-login

Develop the authentication module (`src/pages/login.rs`) as the application entry point. Support multiple enterprise-grade authentication methods, but implement only the methods specified in `requirement.page.md` - not all systems need all authentication types.

This skill consolidates proven patterns from real-world implementations including captcha integration, QR code workflows, error handling strategies, and callback processing.

## Role
Frontend Developer - Implement flexible, multi-method authentication system tailored to project requirements.

## Scope

### ✅ In Scope
- Multiple authentication methods (8+ login types)
- Standard OAuth2/OIDC protocol support
- Image captcha integration (CAPTCHA with auto-refresh)
- Form validation (client-side and server validation)
- Error handling with smart message extraction (`info` > `message` fallback)
- Authentication API integration (`/auth/**` and `/oauth2/**` endpoints)
- Token management (JWT + Access Token)
- AppContext integration (user state, mSecurity login method switches)
- Verification code workflows (SMS/Email countdown timers)
- QR code scanning flows (WeChat polling / WeCom redirect)
- Callback handling (OAuth2/third-party OAuth, URL parameter detection)
- Error modal component for user-friendly error display
- Responsive design across all devices

### ❌ Not in Scope
- Backend authentication implementation
- OAuth provider setup
- User registration/password reset
- Two-factor authentication (separate feature)
- SSO configuration
- LDAP server setup

## Supported Authentication Methods

### Available Methods (Choose Based on Requirements)
**NOT all systems need all methods** - implement only what `requirement.page.md` specifies.

### 1. Standard Username/Password (`/auth/login`)
- **When to use**: Almost all systems (essential baseline)
- Basic credential-based authentication with image captcha
- Fallback method for all configurations
- **Complexity**: Low | **Priority**: High

### 2. JWT Login (`/auth/jwt-login`)
- **When to use**: Modern apps, stateless API-first architectures
- Enhanced JWT-based authentication
- **Complexity**: Low | **Priority**: Medium

### 3. LDAP Enterprise Directory (`/auth/ldap-login`)
- **When to use**: Enterprise/government systems ONLY
- Integration with corporate LDAP directory
- **Complexity**: Medium | **Priority**: Low (enterprise only)

### 4. SMS Verification Code (`/auth/sms-login` + `/auth/sms-send`)
- **When to use**: Mobile-first apps, 2FA required, users prefer phone
- **Complexity**: High (countdown, validation) | **Priority**: Medium

### 5. Email Verification Code (`/auth/email-login` + `/auth/email-send`)
- **When to use**: Email-first apps, SaaS, cost-effective verification
- **Complexity**: Medium (countdown) | **Priority**: Medium

### 6. WeChat Public Account (`/auth/wechat-qrcode` + `/auth/wechat-status`)
- **When to use**: China-only applications
- Polling-based QR code flow (frontend polls status every 3s)
- **Complexity**: High (QR code, polling, status machine) | **Priority**: Low

### 7. Enterprise WeChat / WeCom (`/auth/wecom-init` + `/auth/wecom-qrcode`)
- **When to use**: Enterprise internal applications ONLY
- Redirect-based QR code flow (backend callback with token in URL)
- **Complexity**: High (OAuth2, redirect, error callback) | **Priority**: Low

### 8. OAuth2/OIDC Standard Protocol (`/oauth2/token`, `/oauth2/revoke`, `/userinfo`)
- **When to use**: SaaS platforms, multi-tenant systems
- **Complexity**: High (OAuth2 flow, token management) | **Priority**: Medium-High

## Authentication Method Selection Guide

### Minimal Configuration (Startups/Small Apps)
```
Required: Standard Username/Password
Optional: Email Verification
Not needed: LDAP, SMS, WeChat, WeCom, OAuth2
```

### Standard Configuration (Mid-Size Apps)
```
Required: Standard Username/Password, JWT
Optional: Email or SMS verification, OAuth2 (if multi-tenant)
Not needed: LDAP, WeChat, WeCom
```

### Enterprise Configuration (Enterprises/Government)
```
Required: LDAP Enterprise Directory, Standard Username/Password (fallback)
Optional: OAuth2/OIDC (for SSO), SMS verification
Not needed: WeChat, WeCom (unless internal use)
```

### China-Focused Local Apps
```
Required: Standard Username/Password, WeChat Login
Optional: WeCom (if B2B), SMS Verification
Not needed: LDAP, OAuth2 standard
```

## Input

### Critical Step: Identify Required Methods
```
Read: requirement.page.md
Identify:
  - Which authentication methods are specified?
  - Is it enterprise (LDAP needed)?
  - Is it China-focused (WeChat/WeCom)?
  - Is it SaaS/platform (OAuth2)?
  - What's the user base (mobile = SMS, email = Email)?

Rule: IMPLEMENT ONLY what requirement.page.md specifies
      DO NOT add methods not explicitly required
```

### Required Files
- `requirement.page.md` - Authentication requirements
- `.r2mo/api/metadata.yaml` - API definitions under `/auth/**` and `/oauth2/**`
- `.r2mo/api/marker.md` - Field attributes and validation rules
- `.r2mo/design/spec.md` - Design system (colors, fonts, responsive)
- `.r2mo/requirements/project.md` - Tech stack and credentials

## Output

### Files Modified/Created

| File | Purpose |
|------|---------|
| `src/models/auth.rs` | All auth DTOs (request/response structs) |
| `src/api/auth.rs` | All `/auth/**` API client functions |
| `src/api/mod.rs` | Re-export new API functions |
| `src/pages/login.rs` | Login page with all method panels |
| `src/components/error_modal.rs` | Reusable error modal component |
| `src/components/mod.rs` | Re-export error modal |
| `styles.css` | Captcha, QR code, and login styles |
| `Cargo.toml` | Dependencies (e.g. `urlencoding`) |

## Process - Step-by-Step Implementation

### Step 0: Determine Scope Based on Requirements (CRITICAL)

Before starting any implementation:

1. **Read** `requirement.page.md` carefully
2. **Identify** which authentication methods are listed
3. **Create** a scope document showing:
    - ✅ Required methods (MUST implement)
    - ⚠️ Optional methods (implement if requested)
    - ❌ Not applicable methods (skip completely)

**Example scope:**
```
✅ Required: Standard Login, JWT, Email Verification
⚠️ Optional: SMS Verification (if budget allows)
❌ Skip: LDAP, WeChat, WeCom, OAuth2 (not needed for this app)
```

**Implementation rule:**
- Implement EXACTLY what `requirement.page.md` specifies
- Do NOT assume all methods are needed
- Do NOT implement methods "just in case"
- Complexity and cost scales with number of methods

### Step 1: Setup Application Info Loading

**Purpose:** Load app configuration including login method switches (`mSecurity`)

**Implementation:**
1. Add environment variables to startup script:
    - `Z_APP`: Application name (e.g., `r2-cloud.app-admin`)
    - `Z_TENANT`: Tenant ID
    - `Z_APP_ID`: Application ID
    - `Z_ENDPOINT`: Backend API base URL

2. Create data models in `src/models/auth.rs`:
```rust
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct MSecurity {
    #[serde(rename = "pLoginWechat", default)]
    pub p_login_wechat: bool,
    #[serde(rename = "pLoginWecom", default)]
    pub p_login_wecom: bool,
    #[serde(rename = "pLoginEmail", default)]
    pub p_login_email: bool,
    #[serde(rename = "pLoginSMS", default)]
    pub p_login_sms: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct XApp {
    pub id: String,
    #[serde(rename = "mSecurity", default)]
    pub m_security: Option<MSecurity>,
    // ... other fields
}
```

3. Create API function in `src/api/auth.rs`:
```rust
pub async fn fetch_app_by_name() -> Result<XApp, String> {
    let name = config::z_app();
    let url = format!("{}/app/name/{}", base_url(), name);
    let resp = Request::get(&url).send().await
        .map_err(|e| format!("请求应用信息失败: {}", e))?;
    // ... parse response
}
```

4. Load app info on page mount in `src/pages/login.rs`:
```rust
create_effect(move |_| {
    spawn_local(async move {
        match fetch_app_by_name().await {
            Ok(app) => {
                // Store in signal, check mSecurity flags
                // Show/hide tabs based on flags
            },
            Err(e) => log::error!("Failed to load app: {}", e),
        }
    });
});
```

### Step 2: Implement Standard Login with Image Captcha

**Purpose:** Basic username/password authentication with visual captcha protection

**Implementation:**

1. **Add data models** (`src/models/auth.rs`):
```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CaptchaData {
    #[serde(rename = "captchaId")]
    pub captcha_id: String,
    pub image: String, // Base64 with data URI prefix
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RequestLoginCommon {
    pub username: String,
    pub password: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub captcha: Option<String>,
    #[serde(rename = "captchaId", skip_serializing_if = "Option::is_none")]
    pub captcha_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResponseLoginCommon {
    pub token: String,
    pub id: String,
    pub username: String,
}
```

2. **Add API functions** (`src/api/auth.rs`):
```rust
/// GET /auth/captcha - Fetch image captcha
pub async fn fetch_captcha() -> Result<CaptchaData, String> {
    let url = format!("{}/auth/captcha", base_url());
    let resp = Request::get(&url).send().await
        .map_err(|e| format!("获取验证码失败: {}", e))?;
    if !resp.ok() {
        return Err(format!("验证码接口异常: {}", resp.status()));
    }
    let wrapper: CaptchaResponse = resp.json().await
        .map_err(|e| format!("解析验证码响应失败: {}", e))?;
    Ok(wrapper.data)
}

/// POST /auth/login - Standard login with optional captcha
pub async fn login(
    username: &str,
    password: &str,
    captcha: Option<String>,
    captcha_id: Option<String>,
) -> Result<ResponseLoginCommon, String> {
    let url = format!("{}/auth/login", base_url());
    let body = RequestLoginCommon { username, password, captcha, captcha_id };
    let resp = Request::post(&url)
        .header("Content-Type", "application/json")
        .body(serde_json::to_string(&body)?)
        .send().await?;

    if !resp.ok() {
        let text = resp.text().await.unwrap_or_default();
        // Smart error extraction: info > message
        if let Ok(json) = serde_json::from_str::<serde_json::Value>(&text) {
            if let Some(info) = json.get("info").and_then(|v| v.as_str()) {
                if !info.is_empty() { return Err(info.to_string()); }
            }
            if let Some(msg) = json.get("message").and_then(|v| v.as_str()) {
                return Err(msg.to_string());
            }
        }
        return Err(format!("登录失败 ({}): {}", resp.status(), text));
    }

    let data: LoginResponse = resp.json().await?;
    Ok(data.data)
}
```

3. **Add login page state** (`src/pages/login.rs`):
```rust
// Captcha state
let (captcha_id, set_captcha_id) = create_signal(String::new());
let (captcha_image, set_captcha_image) = create_signal(String::new());
let (captcha_input, set_captcha_input) = create_signal(String::new());

// Auto-load captcha after app info loads
create_effect(move |_| {
    if app_loaded.get() {
        spawn_local(async move {
            match fetch_captcha().await {
                Ok(data) => {
                    set_captcha_id.set(data.captcha_id);
                    set_captcha_image.set(data.image);
                },
                Err(e) => log::error!("Failed to load captcha: {}", e),
            }
        });
    }
});

// Refresh captcha function
let refresh_captcha = move || {
    spawn_local(async move {
        match fetch_captcha().await {
            Ok(data) => {
                set_captcha_id.set(data.captcha_id);
                set_captcha_image.set(data.image);
                set_captcha_input.set(String::new());
            },
            Err(e) => set_error_message.set(e),
        }
    });
};
```

4. **Add captcha UI** (`src/pages/login.rs` view):
```rust
<div class="captcha-group">
    <input
        type="text"
        class="captcha-input"
        placeholder="验证码"
        prop:value=move || captcha_input.get()
        on:input=move |ev| set_captcha_input.set(event_target_value(&ev))
    />
    <img
        src=move || captcha_image.get()
        class="captcha-image"
        alt="验证码"
        on:click=move |_| refresh_captcha()
    />
</div>
```

5. **Add styles** (`styles.css`):
```css
.captcha-group {
    display: flex;
    gap: 10px;
    align-items: stretch;
}
.captcha-input {
    flex: 0 0 40%;
    width: auto !important;
}
.captcha-image {
    flex: 0 0 60%;
    object-fit: fill;
    cursor: pointer;
    border-radius: 4px;
    align-self: stretch;
}
.captcha-image:hover {
    opacity: 0.8;
}
```

6. **Handle login with captcha validation**:
```rust
let handle_login = move |_| {
    let username = username.get();
    let password = password.get();
    let captcha = captcha_input.get();

    if captcha.is_empty() {
        set_error_message.set("请输入验证码".to_string());
        return;
    }

    spawn_local(async move {
        match login(&username, &password, Some(captcha), Some(captcha_id.get())).await {
            Ok(user) => {
                // Save token, update context, navigate
            },
            Err(e) => {
                set_error_message.set(e);
                refresh_captcha(); // Auto-refresh on failure
            }
        }
    });
};
```

**Key Lessons:**
- Backend returns Base64 image with `data:image/png;base64,` prefix - use directly in `<img src>`
- Auto-refresh captcha on login failure to prevent reuse
- Validate captcha input before submitting
- Click image to manually refresh

### Step 3: Implement SMS/Email Verification Code Login

**Purpose:** Code-based authentication with countdown timer

**Implementation:**

1. **Add data models** (`src/models/auth.rs`):
```rust
// SMS
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RequestSmsSend {
    pub mobile: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub captcha: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RequestSmsLogin {
    pub mobile: String,
    pub captcha: String, // verification code
}

// Email (similar structure)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RequestEmailSend {
    pub email: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub captcha: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RequestEmailLogin {
    pub email: String,
    pub captcha: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResponseLoginDynamic {
    pub token: String,
    pub id: String,
    #[serde(default)]
    pub username: Option<String>,
}
```

2. **Add API functions** (`src/api/auth.rs`):
```rust
pub async fn send_sms_code(mobile: &str) -> Result<bool, String> {
    let url = format!("{}/auth/sms-send", base_url());
    let body = RequestSmsSend { mobile: mobile.to_string(), captcha: None };
    // ... POST request, error handling with info > message
}

pub async fn sms_login(mobile: &str, code: &str) -> Result<ResponseLoginDynamic, String> {
    let url = format!("{}/auth/sms-login", base_url());
    let body = RequestSmsLogin { mobile: mobile.to_string(), captcha: code.to_string() };
    // ... POST request, error handling
}

// Similar for email: send_email_code(), email_login()
```

3. **Add countdown timer state** (`src/pages/login.rs`):
```rust
let (sms_countdown, set_sms_countdown) = create_signal(0);
let (sending_sms, set_sending_sms) = create_signal(false);
let (send_sms_error, set_send_sms_error) = create_signal(String::new());
let (send_sms_success, set_send_sms_success) = create_signal(String::new());

// Countdown effect
create_effect(move |_| {
    if sms_countdown.get() > 0 {
        set_timeout(
            move || set_sms_countdown.update(|c| *c = c.saturating_sub(1)),
            Duration::from_secs(1),
        );
    }
});
```

4. **Implement send code with validation**:
```rust
let send_sms_code_handler = move |_| {
    let mobile = mobile_input.get();

    // Validation
    if mobile.is_empty() {
        set_send_sms_error.set("请输入手机号".to_string());
        return;
    }
    if !mobile.chars().all(|c| c.is_numeric()) || mobile.len() != 11 {
        set_send_sms_error.set("手机号格式不正确".to_string());
        return;
    }
    if sms_countdown.get() > 0 || sending_sms.get() {
        return; // Prevent spam
    }

    set_sending_sms.set(true);
    set_send_sms_error.set(String::new());
    set_send_sms_success.set(String::new());

    spawn_local(async move {
        match send_sms_code(&mobile).await {
            Ok(_) => {
                set_sms_countdown.set(60); // Start 60s countdown
                set_send_sms_success.set("验证码已发送，请查收短信".to_string());
            },
            Err(e) => set_send_sms_error.set(e),
        }
        set_sending_sms.set(false);
    });
};
```

5. **Add UI with countdown button**:
```rust
<input
    type="tel"
    placeholder="手机号"
    prop:value=move || mobile_input.get()
    on:input=move |ev| set_mobile_input.set(event_target_value(&ev))
/>
<input
    type="text"
    placeholder="验证码"
    prop:value=move || sms_code_input.get()
    on:input=move |ev| set_sms_code_input.set(event_target_value(&ev))
/>
<button
    class="send-code-btn"
    disabled=move || sms_countdown.get() > 0 || sending_sms.get()
    on:click=send_sms_code_handler
>
    {move || {
        if sms_countdown.get() > 0 {
            format!("{}s 后重发", sms_countdown.get())
        } else if sending_sms.get() {
            "发送中...".to_string()
        } else {
            "获取验证码".to_string()
        }
    }}
</button>

// Success/error messages
<Show when=move || !send_sms_success.get().is_empty()>
    <div class="success-message">{move || send_sms_success.get()}</div>
</Show>
<Show when=move || !send_sms_error.get().is_empty()>
    <div class="error-message">{move || send_sms_error.get()}</div>
</Show>
```

**Key Lessons:**
- SMS countdown: 60 seconds (configurable)
- Email countdown: 300 seconds (5 minutes, configurable)
- Validate phone format (11 digits) before sending
- Prevent spam: disable button during countdown and sending
- Show success message after sending
- Clear messages when switching tabs

### Step 4: Implement WeChat Public Account QR Code Login (Polling Mode)

**Purpose:** WeChat MP login using QR code display + frontend status polling

**Architecture:** Frontend-driven polling — frontend generates QR, polls status, handles token on SUCCESS.

**Implementation:**

1. **Add data models** (`src/models/auth.rs`):
```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WeChatQrCodeData {
    pub uuid: String,
    #[serde(rename = "qrUrl")]
    pub qr_url: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RequestWeChatStatus {
    pub uuid: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "UPPERCASE")]
pub enum WeChatStatus {
    Waiting,
    Scanned,
    Success,
    Expired,
    Cancelled,
    Failure,  // CRITICAL: Must include FAILURE status
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WeChatStatusData {
    pub status: WeChatStatus,
    #[serde(default)]
    pub token: Option<String>, // Only present on SUCCESS
}
```

2. **Add API functions** (`src/api/auth.rs`):
```rust
/// GET /auth/wechat-qrcode (Header: expireSeconds)
pub async fn fetch_wechat_qrcode(expire_seconds: u32) -> Result<WeChatQrCodeData, String> {
    let url = format!("{}/auth/wechat-qrcode", base_url());
    let resp = Request::get(&url)
        .header("expireSeconds", &expire_seconds.to_string())
        .send().await?;
    // ... parse response
}

/// POST /auth/wechat-status (Body: { uuid })
pub async fn check_wechat_status(uuid: &str) -> Result<WeChatStatusData, String> {
    let url = format!("{}/auth/wechat-status", base_url());
    let body = RequestWeChatStatus { uuid: uuid.to_string() };
    let resp = Request::post(&url)
        .header("Content-Type", "application/json")
        .body(serde_json::to_string(&body)?)
        .send().await?;

    if !resp.ok() {
        let text = resp.text().await.unwrap_or_default();
        // Smart error extraction: info > message
        if let Ok(json) = serde_json::from_str::<serde_json::Value>(&text) {
            if let Some(info) = json.get("info").and_then(|v| v.as_str()) {
                if !info.is_empty() { return Err(info.to_string()); }
            }
            if let Some(msg) = json.get("message").and_then(|v| v.as_str()) {
                return Err(msg.to_string());
            }
        }
        return Err(text);
    }
    // ... parse response
}
```

3. **Create WeChatLoginPanel component** (`src/pages/login.rs`):
```rust
#[component]
fn WeChatLoginPanel(active_tab: ReadSignal<LoginMethod>) -> impl IntoView {
    let (qr_url, set_qr_url) = create_signal(String::new());
    let (uuid, set_uuid) = create_signal(String::new());
    let (status_msg, set_status_msg) = create_signal("加载中...".to_string());
    let (is_error, set_is_error) = create_signal(false);

    // Load QR code when tab becomes active
    create_effect(move |_| {
        if active_tab.get() == LoginMethod::WeChat {
            spawn_local(async move {
                match fetch_wechat_qrcode(300).await {
                    Ok(data) => {
                        set_qr_url.set(data.qr_url);
                        set_uuid.set(data.uuid);
                        set_status_msg.set("等待扫码...".to_string());
                        set_is_error.set(false);
                        start_polling(); // Begin polling
                    },
                    Err(e) => {
                        set_status_msg.set(e);
                        set_is_error.set(true);
                    }
                }
            });
        }
    });

    // Polling loop (every 3 seconds)
    let start_polling = move || {
        spawn_local(async move {
            loop {
                if active_tab.get() != LoginMethod::WeChat { break; }
                TimeoutFuture::new(3000).await;
                if uuid.get().is_empty() { continue; }

                match check_wechat_status(&uuid.get()).await {
                    Ok(data) => match data.status {
                        WeChatStatus::Waiting => {
                            set_status_msg.set("等待扫码...".to_string());
                        },
                        WeChatStatus::Scanned => {
                            set_status_msg.set("已扫码，请在手机上确认".to_string());
                        },
                        WeChatStatus::Success => {
                            // CRITICAL: Validate token exists
                            if let Some(token) = data.token {
                                // Save token, update context, navigate
                            } else {
                                set_status_msg.set("登录失败，token 缺失".to_string());
                                set_is_error.set(true);
                            }
                            break;
                        },
                        WeChatStatus::Expired => {
                            set_status_msg.set("二维码已过期，请刷新页面".to_string());
                            set_is_error.set(true);
                            break;
                        },
                        WeChatStatus::Cancelled => {
                            set_status_msg.set("用户取消登录".to_string());
                            break;
                        },
                        WeChatStatus::Failure => {
                            set_status_msg.set("登录异常，请重试或联系管理员".to_string());
                            set_is_error.set(true);
                            break;
                        },
                    },
                    Err(e) => {
                        // Display extracted error, not raw JSON
                        set_status_msg.set(e);
                        set_is_error.set(true);
                        break;
                    }
                }
            }
        });
    };

    view! {
        <div class="qr-code-container">
            <img src=move || qr_url.get() class="qr-code-image" alt="微信二维码" />
        </div>
        <p class=move || if is_error.get() { "status-text error" } else { "status-text" }>
            {move || status_msg.get()}
        </p>
    }
}
```

**Key Lessons (from production debugging):**
- `expireSeconds` is passed as HTTP Header, NOT query parameter
- QR code URL from backend is used directly as `<img src>`
- Must include `FAILURE` status in enum — backend can return it
- On `SUCCESS`, always validate `token` field exists before proceeding
- Error responses from status API: extract `info` > `message`, filter out technical JSON
- Display errors in red (`is_error` flag) to distinguish from normal status
- Stop polling when user switches away from WeChat tab
- Clear error state when user switches tabs

### Step 5: Implement WeCom (Enterprise WeChat) QR Code Login (Redirect Mode)

**Purpose:** WeCom login using backend-redirect flow — fundamentally different from WeChat polling.

**Architecture:** Backend-driven redirect — backend handles OAuth callback, redirects browser back with `token` or `ERR_WE_CP` in URL.

**Flow:**
```
1. Frontend: GET /auth/wecom-init?targetUrl=<current_page_url> → { state }
2. Frontend: GET /auth/wecom-qrcode?state=<state> → { qrUrl }
3. Frontend: Display qrUrl as <img> (QR code image link)
4. User: Scans QR with WeCom app and authorizes
5. Backend: Processes OAuth callback, redirects to targetUrl
   - Success: targetUrl?token=<jwt_token>
   - Failure: targetUrl?ERR_WE_CP=<url_encoded_error_message>
6. Frontend: Detects URL params on page load, handles accordingly
```

**Implementation:**

1. **Add dependency** (`Cargo.toml`):
```toml
[dependencies]
urlencoding = "2.1"
```

2. **Add data models** (`src/models/auth.rs`):
```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WeComInitData {
    pub state: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WeComQrCodeData {
    #[serde(rename = "qrUrl")]
    pub qr_url: String,
}
```

3. **Add API functions** (`src/api/auth.rs`):
```rust
/// GET /auth/wecom-init?targetUrl=<encoded_url>
pub async fn fetch_wecom_init(target_url: &str) -> Result<WeComInitData, String> {
    let url = format!(
        "{}/auth/wecom-init?targetUrl={}",
        base_url(),
        urlencoding::encode(target_url)
    );

    #[cfg(debug_assertions)]
    web_sys::console::log_1(&format!("[API] fetch_wecom_init URL: {}", url).into());

    let resp = Request::get(&url).send().await
        .map_err(|e| format!("获取企微 Init 失败: ", e))?;
    // ... error handling with info > message
}

/// GET /auth/wecom-qrcode?state=<state>
pub async fn fetch_wecom_qrcode(state: &str) -> Result<WeComQrCodeData, String> {
    let url = format!("{}/auth/wecom-qrcode?state={}", base_url(), state);
    // ... similar pattern
}
```

4. **Handle URL callback parameters in LoginPage** (`src/pages/login.rs`):
```rust
// On page load: detect token or error in URL
create_effect(move |_| {
    let window = web_sys::window().unwrap();
    let search = window.location().search().unwrap_or_default();
    let params = web_sys::UrlSearchParams::new_with_str(&search).unwrap();

    // Success: token in URL
    if let Some(token) = params.get("token") {
        // Save token, update AppContext, navigate to home
        return;
    }

    // Error: ERR_WE_CP in URL
    if let Some(err_encoded) = params.get("ERR_WE_CP") {
        let err_msg = urlencoding::decode(&err_encoded)
            .unwrap_or(err_encoded.into())
            .to_string();
        set_wecom_error.set(err_msg);
        set_active_tab.set(LoginMethod::WeCom); // Auto-switch to WeCom tab
    }

    // Clean URL after processing
    let _ = window.history().unwrap().replace_state_with_url(
        &wasm_bindgen::JsValue::NULL,
        "",
        Some(&window.location().pathname().unwrap_or_default()),
    );
});
```

5. **Create WeComLoginPanel component** (`src/pages/login.rs`):
```rust
#[component]
fn WeComLoginPanel(active_tab: ReadSignal<LoginMethod>) -> impl IntoView {
    let (qr_url, set_qr_url) = create_signal(String::new());
    let (loading, set_loading) = create_signal(true);
    let (error_message, set_error_message) = create_signal(String::new());

    // Load QR code when tab becomes active
    create_effect(move |_| {
        if active_tab.get() == LoginMethod::WeCom {
            spawn_local(async move {
                set_loading.set(true);
                let window = web_sys::window().unwrap();
                let target_url = window.location().href().unwrap()
                    .split('?').next().unwrap().to_string();

                match fetch_wecom_init(&target_url).await {
                    Ok(init) => {
                        match fetch_wecom_qrcode(&init.state).await {
                            Ok(qr) => {
                                set_qr_url.set(qr.qr_url);
                                set_loading.set(false);
                            },
                            Err(e) => set_error_message.set(e),
                        }
                    },
                    Err(e) => set_error_message.set(e),
                }
            });
        }
    });

    // Clear error when leaving WeCom tab
    create_effect(move |_| {
        if active_tab.get() != LoginMethod::WeCom {
            set_error_message.set(String::new());
        }
    });

    view! {
        <Show when=move || !error_message.get().is_empty()>
            <div class="error-message">{move || error_message.get()}</div>
        </Show>
        <div class="qr-code-container">
            <img
                src=move || qr_url.get()
                class="qr-code-image"
                alt="企微二维码"
                on:load=move |_| {
                    #[cfg(debug_assertions)]
                    web_sys::console::log_1(&"[WeCom] QR image loaded".into());
                }
                on:error=move |_| {
                    #[cfg(debug_assertions)]
                    web_sys::console::error_1(
                        &"[WeCom] QR image load failed (may be ERR_BLOCKED_BY_ORB)".into()
                    );
                }
            />
        </div>
    }
}
```

6. **Component interface simplification** (proven pattern):
```
WeComLoginPanel only needs: active_tab: ReadSignal<LoginMethod>
LoginPage handles: token detection, error detection, tab switching
DO NOT pass: app_context, set_login_success, set_error_modal, navigate
```

**Key Lessons (from production debugging):**
- WeCom uses REDIRECT mode, NOT polling mode (unlike WeChat)
- `targetUrl` must be URL-encoded via `urlencoding::encode()`
- Backend redirects to `targetUrl?token=xxx` on success
- Backend redirects to `targetUrl?ERR_WE_CP=<encoded_error>` on failure
- Must detect BOTH `token` AND `ERR_WE_CP` params on page load
- Auto-switch to WeCom tab when `ERR_WE_CP` detected
- On error: show error message AND reload QR code simultaneously
- Clean URL with `history.replaceState` after processing params
- Clear error when user switches away from WeCom tab
- Use `#[cfg(debug_assertions)]` for dev-only console logging
- Watch for `ERR_BLOCKED_BY_ORB` — browser may block cross-origin QR images
- Keep component props minimal — move token/error handling to parent

### Step 6: Implement OAuth2/OIDC Standard Protocol Login

**Purpose:** Standard OAuth2 Authorization Code flow for SaaS/multi-tenant systems

**Flow:**
```
1. User clicks "Sign in with {Provider}"
2. Generate random state (CSRF protection), store in sessionStorage
3. Redirect to provider's authorization endpoint
4. User approves permissions on provider page
5. Provider redirects back with authorization code + state
6. Exchange code for tokens via POST /oauth2/token
7. Retrieve user info via GET /userinfo with access token
8. Store tokens, update AppContext, navigate to home
```

**Implementation:**

1. **Authorization redirect**:
```rust
let handle_oauth2_signin = |provider: String| {
    let state = generate_random_state();
    let authorize_url = format!(
        "{}?client_id={}&redirect_uri={}&scope={}&state={}",
        provider.authorize_endpoint,
        config.client_id,
        config.redirect_uri,
        "openid profile email",
        state
    );
    window.session_storage().set_item("oauth_state", &state);
    window.location().set_href(&authorize_url);
};
```

2. **Callback handling** (detect `code` + `state` in URL):
```rust
let handle_oauth2_callback = move |code: String, state: String| {
    // Validate state against stored value (CSRF protection)
    let stored = window.session_storage().get_item("oauth_state");
    if stored != Some(state.clone()) {
        set_error.set("Invalid state - possible CSRF attack");
        return;
    }

    spawn_local(async move {
        match exchange_oauth2_token(&code).await {
            Ok(tokens) => {
                store_oauth_tokens(&tokens);
                match get_user_info(&tokens.access_token).await {
                    Ok(user) => {
                        update_app_context(&user);
                        navigate_to_home();
                    },
                    Err(e) => set_error.set(e.to_string()),
                }
            },
            Err(e) => set_error.set(e.to_string()),
        }
    });
};
```

3. **Token management**:
```
Storage: access_token, id_token, refresh_token in localStorage
Refresh: Monitor expiry, call /oauth2/token with refresh_token
Revocation: On logout, POST /oauth2/revoke, clear all tokens
```

### Step 7: Implement Error Modal Component

**Purpose:** Reusable error display for login failures

**Implementation** (`src/components/error_modal.rs`):
```rust
#[component]
pub fn ErrorModal(
    show: ReadSignal<bool>,
    set_show: WriteSignal<bool>,
    title: ReadSignal<String>,
    message: ReadSignal<String>,
) -> impl IntoView {
    view! {
        <Show when=move || show.get()>
            <div class="error-modal-overlay"
                on:click=move |_| set_show.set(false)>
                <div class="error-modal"
                    on:click=|ev| ev.stop_propagation()>
                    <h3>{move || title.get()}</h3>
                    <p>{move || message.get()}</p>
                    <button on:click=move |_| set_show.set(false)>
                        "确定"
                    </button>
                </div>
            </div>
        </Show>
    }
}
```

**Features:**
- Click overlay or button to close
- Fade-in + slide-up animation
- Export in `src/components/mod.rs`
- Used for login failures across all methods

### Step 8: Implement Token Storage and Post-Login Navigation

**Purpose:** Unified token handling after successful authentication

**Implementation:**
```rust
fn handle_login_success(token: &str, user_id: &str, username: Option<&str>) {
    // 1. Store token in localStorage
    let storage = window().local_storage().unwrap().unwrap();
    storage.set_item("token", token).unwrap();

    // 2. Update AppContext
    app_context.set_logged_in(true);
    app_context.set_user_id(user_id.to_string());
    if let Some(name) = username {
        app_context.set_username(name.to_string());
    }

    // 3. Navigate to home (preserve returnUrl if present)
    let return_url = get_return_url().unwrap_or("/".to_string());
    let navigate = use_navigate();
    navigate(&return_url, Default::default());
}
```

**Applies to all login methods:**
- Standard login → `ResponseLoginCommon { token, id, username }`
- SMS/Email login → `ResponseLoginDynamic { token, id, username? }`
- WeChat login → token from polling status response
- WeCom login → token from URL parameter
- OAuth2 login → access_token from token exchange

## Development Insights & Lessons Learned

### Error Handling Best Practices

**Smart Error Message Extraction:**
```rust
// ALWAYS use this pattern for API error responses
if !resp.ok() {
    let text = resp.text().await.unwrap_or_default();
    if let Ok(json) = serde_json::from_str::<serde_json::Value>(&text) {
        // Priority 1: info field (user-friendly message)
        if let Some(info) = json.get("info").and_then(|v| v.as_str()) {
            if !info.is_empty() { return Err(info.to_string()); }
        }
        // Priority 2: message field (technical description)
        if let Some(msg) = json.get("message").and_then(|v| v.as_str()) {
            return Err(msg.to_string());
        }
    }
    return Err(format!("Request failed ({}): {}", resp.status(), text));
}
```

**Why this matters:**
- Backend returns structured errors with `info` (user-facing) and `message` (technical)
- Without extraction, users see raw JSON with status codes, reason fields, etc.
- Extracting `info` first gives clean, actionable error messages

### QR Code Implementation Patterns

**WeChat (Polling Mode):**
- Frontend generates QR, displays image, polls status every 3s
- Status enum MUST include `FAILURE` state
- On `SUCCESS`, validate `token` field exists before proceeding
- Stop polling when user switches tabs
- Display errors in red to distinguish from normal status

**WeCom (Redirect Mode):**
- Backend handles OAuth callback, redirects browser with token/error in URL
- Must detect BOTH `?token=xxx` AND `?ERR_WE_CP=xxx` on page load
- URL-encode `targetUrl` parameter with `urlencoding::encode()`
- Auto-switch to WeCom tab when error detected
- Show error + reload QR simultaneously for better UX
- Clean URL with `history.replaceState()` after processing

### Captcha Integration

**Auto-refresh strategy:**
- Load captcha automatically after app info loads
- Refresh on login failure (prevents reuse of expired captcha)
- Click image to manually refresh
- Backend returns Base64 with `data:image/png;base64,` prefix — use directly

**UI Layout:**
```
Input (40%) | Image (60%)
- Use flexbox with gap
- Image: object-fit: fill, cursor: pointer
- Align image height to input with align-self: stretch
```

### Countdown Timer Pattern

**SMS/Email verification:**
```rust
// State
let (countdown, set_countdown) = create_signal(0);

// Effect (auto-decrement)
create_effect(move |_| {
    if countdown.get() > 0 {
        set_timeout(
            move || set_countdown.update(|c| *c = c.saturating_sub(1)),
            Duration::from_secs(1),
        );
    }
});

// Button text
{move || {
    if countdown.get() > 0 {
        format!("{}s 后重发", countdown.get())
    } else if sending.get() {
        "发送中...".to_string()
    } else {
        "获取验证码".to_string()
    }
}}
```

**Validation before sending:**
- Check field not empty
- Validate format (phone: 11 digits, email: regex)
- Prevent spam: disable during countdown and sending

### Component Architecture

**Separation of concerns:**
- **Panel components** (e.g., `WeComLoginPanel`): Display UI, load resources
- **Page component** (`LoginPage`): Handle callbacks, URL params, token storage, navigation
- Keep panel props minimal — pass only `active_tab: ReadSignal<LoginMethod>`
- Move complex logic (token detection, error handling) to parent

**Why this matters:**
- Easier to test and maintain
- Avoids prop drilling
- Clear responsibility boundaries

### Debugging Support

**Development-only logging:**
```rust
#[cfg(debug_assertions)]
web_sys::console::log_1(&format!("[WeCom] QR URL: {}", url).into());
```

**Use prefixes for clarity:**
- `[API]` — API layer logs
- `[WeCom]` / `[WeChat]` — Component layer logs
- Helps trace issues across layers

### State Management

**Clear state when switching tabs:**
```rust
create_effect(move |_| {
    if active_tab.get() != LoginMethod::WeCom {
        set_error_message.set(String::new());
        set_countdown.set(0);
    }
});
```

**Why:** Prevents state leakage between login methods

## Rules

### 1. API-First Design
- All endpoints from `.r2mo/api/metadata.yaml` `/auth/**` paths
- Field names and types exactly as in API spec
- Use `#[serde(rename = "camelCase")]` for JSON field mapping
- NO hardcoded endpoint paths — use `base_url()` helper

### 2. Error Handling (CRITICAL)
- ALWAYS extract `info` field first, then `message` as fallback
- NEVER show raw JSON or HTTP status codes to users
- Use `ErrorModal` component for login failures
- Auto-refresh captcha on login failure
- Display QR code errors in red with `is_error` flag

### 3. Token Management
- Store JWT in localStorage
- Include in `Authorization: Bearer` header for subsequent requests
- Clear token on logout
- Handle token expiration gracefully

### 4. AppContext Integration
- Update AppContext on successful login
- Set `is_logged_in: true`
- Store user information (id, username, token)
- Check `mSecurity` flags to show/hide login method tabs

### 5. Code-Based Methods (SMS/Email)
- Call send endpoint first, then login endpoint
- Implement countdown timer (SMS: 60s, Email: 300s)
- Prevent spam (disable resend during countdown)
- Validate input format before sending (phone: 11 digits)
- Show success/error messages for send operation

### 6. QR Code Methods
- **WeChat**: Polling mode — fetch QR, poll status every 3s, handle 6 states
- **WeCom**: Redirect mode — init → qrcode → display → backend callback → URL params
- Stop polling when user switches tabs
- Handle `FAILURE` status and token validation on `SUCCESS`
- WeCom: detect both `token` and `ERR_WE_CP` URL params

### 7. Component Design
- Each login method as separate panel component
- Keep panel props minimal (only `active_tab`)
- Parent handles token storage, navigation, URL param detection
- Clear state when switching between tabs

### 8. Redirect After Login
- Navigate to home page on success
- Preserve `returnUrl` parameter if provided
- Use `use_navigate()` from `leptos_router`
- Clean URL params with `history.replaceState()` after processing

### 9. Design System Compliance
- Use colors from `spec.md`
- Apply responsive design (mobile/tablet/desktop)
- Use Tailwind CSS exclusively
- Consistent error message styling (`.error-message` class)

### 10. Debug Logging
- Use `#[cfg(debug_assertions)]` for dev-only console output
- Prefix logs: `[API]` for API layer, `[WeCom]`/`[WeChat]` for components
- Log request URLs, response status, error details
- Monitor image load events (`on:load`, `on:error`)

## Validation Checklist

- [ ] All enabled methods from `requirement.page.md` implemented
- [ ] All `/auth/**` endpoints properly called with correct HTTP methods
- [ ] All request/response schemas match API spec (serde rename)
- [ ] Error extraction uses `info` > `message` fallback pattern
- [ ] Image captcha: auto-load, click-refresh, auto-refresh on failure
- [ ] SMS/Email countdown working (correct duration)
- [ ] SMS/Email input validation before sending
- [ ] WeChat QR polling: 3s interval, all 6 states handled
- [ ] WeChat SUCCESS: token field validated before proceeding
- [ ] WeCom init: targetUrl properly URL-encoded
- [ ] WeCom callback: both `token` and `ERR_WE_CP` detected
- [ ] WeCom error: auto-switch tab + show error + reload QR
- [ ] URL cleaned with `history.replaceState()` after processing
- [ ] State cleared when switching between login tabs
- [ ] ErrorModal component working (overlay + button close)
- [ ] Token stored in localStorage on success
- [ ] AppContext updated on login
- [ ] Navigation works after login
- [ ] Responsive design tested
- [ ] No compilation warnings (remove unused props)
- [ ] Dev logging with `#[cfg(debug_assertions)]`

## Success Criteria

- ✅ Login module compiles without errors or warnings
- ✅ All enabled authentication methods functional
- ✅ Form validation working correctly
- ✅ Error messages clear and user-friendly (no raw JSON)
- ✅ Captcha integration complete (auto-load, refresh, validate)
- ✅ SMS/Email code workflows with countdown
- ✅ WeChat QR polling with all status states
- ✅ WeCom redirect flow with error callback handling
- ✅ Token storage and AppContext update
- ✅ Post-login navigation working
- ✅ State isolation between login method tabs
- ✅ Responsive design on all devices

## Related Skills
- **r2-dev-layout** - Main application layout with authenticated user
- **r2-dev-page** - Regular page development
- **r2-sys-integrate** - System integration with login page routing

## Version

- **Version**: 2.0.0 (Consolidated from production implementation history)
- **Last Updated**: 2026-02-23
- **Status**: Production Ready
- **Framework**: Leptos 0.8.15
- **Language**: Rust 2024 Edition
- **Auth Methods**: 8+ (Standard, JWT, LDAP, SMS, Email, WeChat, WeCom, OAuth2/OIDC)
