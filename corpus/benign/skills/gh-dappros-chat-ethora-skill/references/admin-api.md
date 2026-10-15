# Ethora admin API — what the scripts call

Base: `https://api.chat.ethora.com` (Ethora Cloud). Swagger: https://api.chat.ethora.com/api-docs/ . Self-hosted servers expose the same API under their own host.

The admin panel https://app.chat.ethora.com is just a UI over these endpoints, so everything the user would do there can be done from the terminal with `scripts/ethora-admin.mjs`.

## Bootstrap: the base app

Admin accounts live in the platform's **base app** (`domainName: "app"`, id `646cc8dc96d4a4dc8f7b2f2d` on Cloud). Its public config (incl. its app token, needed as `Authorization` for login/sign-up) is fetched without auth:

```
GET /v1/apps/get-config?domainName=app
→ { result: { _id, displayName, domainName, appToken, xmppHost, isBaseApp, isAllowedNewAppCreate, … } }
```
`xmppHost` is install-wide → XMPP WebSocket `wss://<xmppHost>/ws`, conference `conference.<xmppHost>`. Self-hosted installs may use a different base `domainName` (`--base-domain`).

## Account

| Step | Call | Notes |
| --- | --- | --- |
| Register | `POST /v2/users/sign-up-with-email` `{ email, firstName, lastName, password, appId }`, header `Authorization: <base appToken>` | v2 sets the password immediately. Some installs enable Cloudflare Turnstile (`cfToken`) → register in the browser instead. |
| Login | `POST /v2/users/login-with-email` `{ email, password, appId }`, header `Authorization: <base appToken>` | Returns `{ user, token, refreshToken }`. |
| MFA | if login returns `{ mfaRequired: true, mfaToken }` → `POST /v2/users/login/mfa` `{ mfaToken, code, appId }` | 6-digit TOTP or backup code; response = normal login payload. |
| Refresh | `POST /v1/users/login/refresh`, header `Authorization: <refreshToken>` | `{ token, refreshToken }` |
| Me | `GET /v1/users/me`, header `Authorization: <token>` | |

User tokens carry the `JWT ` prefix and are sent verbatim in `Authorization`.

## Apps (tenant admin)

| Step | Call |
| --- | --- |
| List | `GET /v1/apps?limit=200&offset=0&order=desc&orderBy=createdAt` → `{ apps: [{ _id, displayName, domainName, appToken, appSecret, defaultRooms, … }], total }` (paginate with `offset`; `appSecret` is included — verified) |
| Create | `POST /v1/apps` `{ displayName, domainName?, createDefaultChat: true, usersCanFree, defaultAccessProfileOpen, defaultAccessAssetsOpen }` → `{ app }` (v2: `POST /v2/apps`) |
| Get | `GET /v1/apps/{id}` |
| Rotate app JWT | `DELETE /v1/apps/rotate-jwt/{id}` |
| App tokens (v2) | `GET/POST /v2/apps/{appId}/tokens`, `…/rotate` — server-side B2B tokens, alternative to signing with the secret |
| Default rooms | `POST /v1/apps/create-app-chat/{id}`, `GET /v1/apps/get-default-rooms/app-id/{appId}` |

`domainName` is alphanumeric, unique platform-wide; it becomes `https://<domainName>.chat.ethora.com` (the hosted web app for that Ethora app).

If `appSecret` is missing from the API response, it is shown in the admin panel → app → Settings → API ("Secret"); store it with `ethora-admin.mjs set-secret`.

## End-user side (what the SDK and your backend call)

| Purpose | Call |
| --- | --- |
| Client JWT exchange | `POST /v1/users/client`, header `x-custom-token: <client JWT>` → `{ user, token, refreshToken }`; `401 USER_NOT_FOUND` if the user was never created |
| Create/sync users | `POST /v1/users/batch` (or `/v2/apps/{appId}/users/batch`), header `x-custom-token: <server JWT>` |
| Email login inside the app | `POST /v1/users/login-with-email` `{ email, password, appId }`, `Authorization: <app token>` |
| Rooms | `POST /v1/chats`, `POST /v2/chats/users-access`, `GET /v1/chats/my`, `POST /v2/apps/{appId}/chats/private` |
| Push | `POST /v1/push/subscription/{appId}` (SDK does it), `POST /v1/push/apns/{appId}`, `POST /v1/push/firebase-service-account/{appId}` |

## Local state written by the scripts

`~/.ethora/profiles.json` — shared with `npx @ethora/setup`:
```json
{
  "activeProfile": "my-app",
  "profiles": {
    "my-app": {
      "name": "my-app", "type": "cloud",
      "endpoints": { "apiUrl": "https://api.chat.ethora.com/v1", "xmppWebSocket": "wss://xmpp.chat.ethora.com/ws", "xmppBosh": "https://xmpp.chat.ethora.com/bosh", "xmppHost": "xmpp.chat.ethora.com", "xmppConference": "conference.xmpp.chat.ethora.com" },
      "appId": "…", "appToken": "JWT …", "appSecret": "…", "displayName": "My App", "domainName": "myapp", "email": "dev@example.com",
      "webAppUrl": "https://myapp.chat.ethora.com", "adminUrl": "https://app.chat.ethora.com/app/admin/apps/…"
    }
  }
}
```
`~/.ethora/session.json` — admin user token/refresh token per API origin (`ethora-admin.mjs logout` removes it).
