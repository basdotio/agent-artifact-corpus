# Web integration — `@ethora/chat-component` (React 18/19)

Package: https://www.npmjs.com/package/@ethora/chat-component · repo: https://github.com/dappros/ethora-chat-component

## 1. Install

```bash
npm view @ethora/chat-component dist-tags --json   # check the current stable (`latest`)
npm i @ethora/chat-component@latest                # yarn add / pnpm add / bun add
```

Peer deps: `react` and `react-dom` ^18.3 or ^19. Everything else (xmpp client, redux, styled-components) is bundled.
Import the base stylesheet once (fonts/resets; the rest is styled-components):

```ts
import '@ethora/chat-component/dist/main.css';
```

## 2. Exports you will use

| Export | Purpose |
| --- | --- |
| `XmppProvider` | Owns the XMPP connection. Must wrap `Chat` (and anything using `useUnread`). |
| `Chat` | The chat UI (room list + room). Props: `config`, `roomJID`, `user`, `MainComponentStyles`, custom components. |
| `useUnread()` | `{ totalCount, unreadByRoom, loading }` — badges outside the chat. |
| `logoutService.performLogout()` | Programmatic logout (clears store + disconnects XMPP). Call it before your own sign-out. |
| `usePushNotifications`, `useInAppNotifications`, `useRoomMute`, `useQRCodeChat` | Optional features. |

## 3. Where to put `XmppProvider`

- **Chat on a single page only** → wrap just that page's content (template `assets/templates/web/EthoraChat.tsx` already does this). Simplest; the socket lives while the page is mounted.
- **Chat used across pages / unread badge in a global header / push** → wrap the app root (`main.tsx` / `App.tsx` / Next `app/layout.tsx` via a client component) with `XmppProvider config={config}` and render `<Chat config={config} />` on the page. Then the badge (`useUnread`) works anywhere and the connection survives navigation.

Either way follow the **single initialization contract**:
- **no `<React.StrictMode>` around the chat** — in 26.9.x the double-invoked dev effects bootstrap XMPP twice (30 s connect, messages stuck at "sending…"/"Not delivered"). Vite's `main.tsx` and CRA's `index.tsx` ship with it: remove it. Next.js: `reactStrictMode: false` in `next.config.js` (the App Router enables it by default in dev);
- pass the *same memoized* `config` object to `XmppProvider` and `Chat`;
- with `initBeforeLoad: true` the provider opens the socket and `Chat` reuses it; never also call `client.login()` yourself.

## 4. Minimal config (Ethora Cloud)

```tsx
const config = useMemo(() => ({
  appId: ETHORA.appId,                       // from the admin panel / profile
  customAppToken: ETHORA.appToken,           // app JWT ("JWT eyJ…"), used for app-scoped calls
  baseUrl: 'https://api.chat.ethora.com',    // API origin; a trailing /v1 is tolerated
  xmppSettings: {
    devServer: 'wss://xmpp.chat.ethora.com/ws',   // web: FULL wss URL (RN differs: bare host)
    host: 'xmpp.chat.ethora.com',
    conference: 'conference.xmpp.chat.ethora.com',
  },
  initBeforeLoad: true,
  newArch: true,
  refreshTokens: { enabled: true },
  jwtLogin: { enabled: true, token: clientJwt },   // "user without login" — see auth-modes.md
}), [clientJwt]);

<XmppProvider config={config}>
  <Chat config={config} />
</XmppProvider>
```

Omitting `baseUrl`/`xmppSettings` falls back to the Ethora Cloud defaults, so for Cloud they are optional; keep them explicit so a later move to self-hosted is a config change only.

Useful `config` toggles (full list in the package README "Full Config Reference"): `colors`, `colorScheme: 'light'|'dark'|'system'`, `typography`, `disableRooms` + `roomJID` (single-room mode), `disableHeader`, `disableNewChatButton`, `disableRoomConfig`, `disableProfilesInteractions`, `hiddenRooms`, `fallbackScreens`, `eventHandlers.onError`, `inAppNotifications`, `pushNotifications`, `translates`, `i18n`.

## 5. Routers

**react-router (Vite/CRA):**
```tsx
<Route path="/chat" element={<ChatPage />} />
```
Give the page a fixed height (`100vh` or flex column) — the chat fills its container.

**Next.js App Router:** the component uses `window`/WebSocket → client-only.
```tsx
// app/chat/page.tsx
import EthoraChat from '@/components/EthoraChatNext';   // 'use client' + next/dynamic({ ssr:false }) wrapper
export default function Page() { return <main style={{ height: '100vh' }}><EthoraChat /></main>; }
```
The token route goes to `app/api/ethora/token/route.ts` (template `backend/next-route.ts`). Env: `NEXT_PUBLIC_ETHORA_*` for the browser, `ETHORA_APP_SECRET` server-only.

**Next.js Pages Router:** same `next/dynamic` wrapper; route in `pages/api/ethora/token.ts` with the handler signature `(req, res)`.

**Remix / React Router framework mode:** render the chat inside a `ClientOnly`/`useEffect`-gated component; put the token route in a `loader`/resource route.

## 6. Env variables by bundler (written by `scripts/write-env.mjs`)

| Bundler | File | Prefix |
| --- | --- | --- |
| Vite | `.env.local` | `VITE_ETHORA_*` |
| Next.js | `.env.local` | `NEXT_PUBLIC_ETHORA_*` (+ `ETHORA_APP_SECRET`, server only) |
| CRA | `.env.local` | `REACT_APP_ETHORA_*` |

Keys: `…ETHORA_APP_ID`, `…ETHORA_APP_TOKEN`, `…ETHORA_API_URL`, `…ETHORA_XMPP_HOST`, `…ETHORA_XMPP_WS`, `…ETHORA_XMPP_CONFERENCE`, optional `…ETHORA_DEV_CLIENT_JWT`.
`ETHORA_APP_SECRET` must never get a public prefix.

## 7. Frontend-only project (no backend yet)

The "no login screen" mode needs a server to sign the client JWT. Options, best first:
1. **Vite dev plugin** `assets/templates/web/vite-dev-token-plugin.ts` serves `/api/ethora/token` from the dev server using `.env.ethora` (secret stays on disk, dev only). Production still needs a real route.
2. **Pre-signed dev token**: `node scripts/client-jwt.mjs --user-id dev-user-1 --expires 7d` → `write-env.mjs --dev-jwt <token>` → `VITE_ETHORA_DEV_CLIENT_JWT`. Tell the user it expires and must not ship.
3. **Programmatic test user via `customLogin`** (zero backend, browser only): `loginFunction` calls `POST /v1/users/login-with-email` `{ email, password, appId }` with `Authorization: <appToken>`; on failure signs the user up with `POST /v2/users/sign-up-with-email` (same header, `appId` in body) and logs in again; return the `{ ...user, token, refreshToken }` object. Dev only — the test password sits in `.env.local`.
4. **Built-in login/registration UI**: no `jwtLogin`; set `customAppToken` + `appId`; users register/log in inside the chat (accounts live in the Ethora app). Works with zero backend; no silent SSO. Note: in 26.9.x the built-in form and the `user={{ email, password }}` prop send a hard-coded `appId` (package bug), so they only work for the base Ethora app until fixed — prefer option 3.

## 8. Logout & session

- Call `logoutService.performLogout()` when your app signs out, then drop your own session.
- With `refreshTokens.enabled: true` the SDK refreshes its own tokens; when the Ethora session is dead for good, the chat shows the fallback screen — re-fetch a client JWT and re-render.

## 9. Checklist before "it works"

1. `node scripts/verify-setup.mjs --user-id <id> --email <email>` passes (API, token, client-JWT exchange, XMPP host).
2. Dev server runs; the chat page shows the room list (a new app has "Main chat" if created with `createDefaultChat`).
3. Browser console has no `useXmppClient must be used within an XmppProvider` and no duplicate `wss://…/ws` connections.
4. Sending a message works; open the admin panel → app → Chats to see it.
