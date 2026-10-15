# Auth modes — how the chat knows who the user is

Both SDKs accept the same `config` auth blocks. Pick **one**.

| Mode | Config | When |
| --- | --- | --- |
| **Client JWT (recommended)** | `jwtLogin: { enabled: true, token }` | Your app already has its own users. Backend signs a short JWT with the **app secret**; the chat exchanges it at `POST /v1/users/client` and opens already logged in. No Ethora login screen. |
| Injected user | `userLogin: { enabled: true, user }` | Your backend already called the Ethora login/batch API and holds the full user object (`token`, `refreshToken`, `xmppPassword`, `xmppUsername`/`defaultWallet`). |
| Custom async login | `customLogin: { enabled: true, loginFunction }` | Same as above but resolved lazily by a function you provide. |
| Email/password | `user={{ email, password }}` prop, or `customAppToken` + built-in form | Demos, or when users should register/log in inside the chat (accounts live in the Ethora app). |
| Google | `googleLogin: { enabled: true, firebaseConfig }` | Firebase Google SSO (web). |

## Client JWT — the "user without login" flow

**It always needs a server.** The JWT is signed with the app secret, and the secret must never reach a browser or mobile bundle. So this mode means a backend change: one route plus one helper file. Agree on it with the user before writing it (SKILL.md §7). Frontend-only alternatives are in web-integration.md §7 and rn-integration.md §5.

```
your frontend ──GET /api/ethora/token──▶ your backend ──sign HS256 with APP_SECRET──▶ { token }
      │                                                                                    │
      └── <Chat config={{ jwtLogin: { enabled: true, token } }} />  ──POST /v1/users/client (x-custom-token)──▶ Ethora
                                                                       ◀── { user, token, refreshToken } ── chat opens
```

Token payload (HS256, secret = **app secret** from admin panel → app → Settings → API):
```json
{ "data": { "type": "client", "appId": "<APP_ID>", "userId": "<your stable user id>" }, "iat": 1700000000, "exp": 1700043200 }
```
- `userId` is **your** id for the user (uuid, db id, email hash…). The Ethora username becomes `<appId>_<userId>`; the same `userId` always maps to the same chat identity, across web and mobile.
- Keep `exp` short-ish (hours); the SDK keeps its own session with `refreshTokens: { enabled: true }` and only needs a fresh client JWT on a cold start.
- **The secret never leaves the server.** Not in `VITE_*`/`NEXT_PUBLIC_*`/`EXPO_PUBLIC_*`, not in the mobile bundle.

### Make sure the user exists in the app (required)

`POST /v1/users/client` never creates users: for an unknown `userId` it answers `401 { code: "USER_NOT_FOUND" }` (verified against Ethora Cloud, Oct 2026). Sync users server-side once (idempotent) with the server token (`data.type: 'server'`, same secret) — `POST /v1/users/batch`:
```json
{ "bypassEmailConfirmation": true, "usersList": [{ "uuid": "<userId>", "email": "...", "firstName": "...", "lastName": "..." }] }
```
Do this when the user is created in your system or lazily before minting their first token (templates do the lazy version). `uuid` must equal the `userId` you sign.
`firstName` and `lastName` are required and must be **≥ 2 characters** (`422 VALIDATION_ERROR` otherwise; verified on Ethora Cloud, Oct 2026). Many apps have one `name` field: split it and fall back to `User` (template helper `ensureEthoraUser({ userId, email, name })`). `scripts/ensure-user.mjs` does it from the terminal; `scripts/verify-setup.mjs --user-id X --email Y` proves the whole chain.

### Backend templates

- Node/Express: `assets/templates/backend/ethora-token.js` + `express-route.js`
- Next.js App Router: `assets/templates/backend/next-route.ts` (`app/api/ethora/token/route.ts`)
- Any other language (Python, PHP, Ruby, Go, Java/Kotlin, C#…): the route is the same everywhere. Sign an HS256 JWT with the payload above (any standard JWT library), sync the user with `POST /v1/users/batch` using a server JWT (`data.type: 'server'`) in the `x-custom-token` header, return `{ token }`. Port `ethora-token.js`; nothing in it is Node-specific.

Frontend contract used by the templates: `GET /api/ethora/token` (with the app's own session cookie/bearer) → `200 { "token": "<jwt>" }`.

### Rooms for your users (optional, server-side)

- Create: `POST /v1/chats` `{ title, uuid: "<your room id>", type: "group" }` (x-custom-token = server token)
- Add members: `POST /v2/chats/users-access` `{ chatName: "<appId>_<room uuid>", members: ["<userId>", …] }`
- Room JID for `roomJID` prop: `<appId>_<room uuid>@conference.<xmppHost>`
- 1:1: `POST /v2/apps/{appId}/chats/private`

## Dev-only shortcuts (say so to the user every time)

- `node scripts/client-jwt.mjs --user-id dev-user-1 --expires 7d` → paste into `…ETHORA_DEV_CLIENT_JWT`. Expires; never commit; remove before release.
- Vite: `assets/templates/web/vite-dev-token-plugin.ts` signs on the dev server from `.env.ethora`.

## Admin (the developer) vs end users

The account used in `ethora-admin.mjs login` is the **tenant admin** on the base app ("app.chat.ethora.com"). End users of the chat are users **of the child app** (`appId`), created via the batch endpoint, the built-in registration form, or the admin panel → Users. The admin's own account is not automatically a user of the child app; mint a client JWT for an id like `admin-<something>` if the developer wants to chat too.

## Token glossary

| Token | Looks like | Who uses it |
| --- | --- | --- |
| App token (`appToken`, `customAppToken`) | `JWT eyJ…` (with the `JWT ` prefix) | Client SDKs, for app-scoped calls like login-with-email / sign-up. Public-ish (shipped in apps). |
| App secret (`appSecret`) | random string | Your backend only: signs client & server JWTs. Rotate in admin panel if leaked. |
| Client JWT | `eyJ…` (`data.type: client`) | Browser/mobile → `/v1/users/client`. Short-lived. |
| Server JWT | `eyJ…` (`data.type: server`) | Backend → `x-custom-token` for users/chats management. |
| User access/refresh tokens | `JWT eyJ…` | Returned by login; the SDK stores and refreshes them. |
