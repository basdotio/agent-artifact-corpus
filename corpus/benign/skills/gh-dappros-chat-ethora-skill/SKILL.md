---
name: ethora-skill
description: Integrate Ethora chat into a React (web) or React Native (Expo / bare) app, or scaffold a new app with chat built in. Installs @ethora/chat-component or @ethora/chat-component-rn, wraps the web app in XmppProvider, creates the chat page/screen, signs into the Ethora admin (app.chat.ethora.com) from the terminal to create/select an app and fetch its credentials, wires the "user without login" client-JWT flow with a backend token route (or, for frontend-only devs, a backend handoff doc + dev token / zero-backend login), supports self-hosted Ethora servers, and verifies the setup. Use this whenever someone mentions Ethora, @ethora/chat-component(-rn), api.chat.ethora.com, app.chat.ethora.com, "add chat to my app", in-app messaging/chat rooms for a React or RN app, XmppProvider, or wants chat with their own users logged in automatically — even if they don't say "Ethora".
---

# Ethora chat integration

Goal: the user ends with a working chat in their app in minutes, with their own users signed in automatically. You do the legwork: detect the project, install the right package, place the component, get credentials from the Ethora admin in the terminal, write config, wire auth, verify.

Paths in this file are relative to the skill directory. Scripts are plain Node (>= 18), no installs needed: run them with `node <skill>/scripts/<name>.mjs`. They keep state in `~/.ethora/` (override with the `ETHORA_HOME` env var).

## 0. Orient

1. Run `node scripts/detect-project.mjs <projectDir> --json`. It tells you platform (web / react-native / none), framework (vite, next, cra, expo, bare-rn), router, package manager, env convention, entry files, existing pages/screens, and `backend`: servers in any language (Node, Python, PHP, Ruby, Go, Java/Kotlin, .NET) found in the project, its subfolders or sibling folders. The backend result feeds §7.
2. Decide the track:
   - **Existing app** → continue below.
   - **No project** (`platform: none`) or the user wants a new app → scaffold first, then continue as "existing":
     - web: `npm create vite@latest <name> -- --template react-ts` (or Next if they ask: `npx create-next-app@latest`)
     - mobile: `npx create-expo-app@latest <name>` (Expo is the fastest path; bare RN only if they insist)
   - **Backend-only repo** → only section 4 (token route) applies.
3. Read the matching reference now, it is short and has the exact install/placement rules:
   - web → `references/web-integration.md`
   - React Native → `references/rn-integration.md`

Keep the user in the loop with short confirmations, but do not stop for things you can decide (package manager, file names, where templates go). Stop and ask (AskUserQuestion when available) only for the five real decisions: which page/screen, **how users sign in to the chat (which decides whether the backend changes, §7)**, Cloud vs self-hosted, account (login/register), which app. Ask the sign-in question early, together with the page question. Never change a backend the user did not agree to change.

## 1. Install the SDK

- web: `@ethora/chat-component` (+ import `@ethora/chat-component/dist/main.css` once)
- RN: follow `references/rn-integration.md` §1 exactly. The order matters: native peers first via `npx expo install …` (including `react-native-worklets` for Reanimated 4 and `expo-asset`), then `npm install @ethora/chat-component-rn@latest --legacy-peer-deps`. A plain `npm install` of the SDK fails with ERESOLVE on fresh Expo apps, or pulls native versions the Expo SDK doesn't support. Finish with `npx expo-doctor`. **Tell the user right away that Expo Go cannot run the chat**: they need a development build (`npx expo run:ios|android`).

**Always the current stable release.** Before installing, run `npm view <package> dist-tags --json` and install the `latest` tag explicitly: `<package>@latest` (`npm i` / `yarn add` / `pnpm add` / `bun add`). Never pick a `next`/`beta`/`rc` tag unless the user asks. If the package is already installed, compare the installed version (`npm ls <package>`) with `latest`; if it is older, tell the user both versions and offer the upgrade (don't upgrade silently: it can change behaviour in an existing app). The notes in this skill were verified on 26.9.x; if `latest` is a newer minor/major, skim the package changelog/README on npm for breaking changes before relying on the version-specific workarounds below.

Use the detected package manager.

## 2. Where does the chat go?

Ask: *existing page/screen or a new one?* Offer the list from `detect-project` (existing pages) plus "new route /chat". Then:

- Copy templates and adapt names/paths:
  - web: `assets/templates/web/ethora.config.ts`, `EthoraChat.tsx`, `ChatPage.tsx` (Next: also `EthoraChatNext.tsx`, and use it instead of importing `EthoraChat` directly). Fix the env prefix in `ethora.config.ts` for Next/CRA (literal `process.env.NEXT_PUBLIC_…` reads).
  - RN: `assets/templates/rn/ethora.config.ts`, `EthoraChatScreen.tsx`.
- Register the route/screen in their router (react-router `<Route>`, Next `app/chat/page.tsx`, Expo Router `app/chat.tsx`, React Navigation `Stack.Screen`). Add a link/tab so it is reachable.
- Give the container a real height (web: `100vh`/flex; RN: `flex: 1`).

## 3. Wrap with `XmppProvider` (web; RN: see the end of this section)

`Chat` must live inside `XmppProvider`. Two valid placements — pick with the user's usage in mind, don't ask unless it matters:
- **page-level** (template default): simplest, chat only on that page.
- **app root**: when they want unread badges elsewhere, chat on several pages, or push. Move `XmppProvider config={config}` to `main.tsx`/`App.tsx`/root layout (client component in Next) and keep `<Chat config={config} />` in the page.

Rules that prevent the classic bugs: one memoized `config` object passed to **both** provider and chat; `initBeforeLoad: true`; never call the XMPP client login yourself. (Templates already comply.)

**React Native is different: no outer `XmppProvider`.** RN `<Chat>` mounts its own redux store and `XmppProvider` (26.4.x and 26.9.x). In 26.9.x an outer `XmppProvider` crashes the screen with `could not find react-redux context value` (its video-call overlay sits outside the store). Render only `<Chat config={config} />`, as the RN template does. Everything above about the provider is for the web SDK.

**React StrictMode must not wrap the chat (web SDK 26.9.x).** StrictMode's double-invoked effects start the XMPP bootstrap twice: the first connect takes ~30 s instead of ~2 s and sent messages stay at "sending…" then show "Not delivered" although the server stored them (verified live). Vite/CRA templates wrap the app in `<StrictMode>` in `main.tsx` — remove it (or move it so it does not enclose the chat page); Next.js: `reactStrictMode: false` in `next.config`. Tell the user why.

## 4. Which API?

Ask: **Ethora Cloud** (default, `https://api.chat.ethora.com`, admin at https://app.chat.ethora.com) or **self-hosted** (customers who run their own Ethora server — same API, their hostnames). For self-hosted read `references/self-hosted.md` and pass `--api <origin>` to the admin script in the next step.

**Say this plainly when the user picks a custom API:** the SDK and the scripts only work against a server that exposes the **Ethora API** (the same `/v1/...` and `/v2/...` endpoints and payloads as `https://api.chat.ethora.com/api-docs/`) plus an Ethora-compatible XMPP server. That is what self-hosted Ethora deployments provide. A different backend (the user's own REST API, Firebase, another chat vendor) will not work, even if it has "similar" endpoints. If the user isn't sure, run `curl -s <api>/v1/apps/get-config?domainName=app` (an Ethora server answers with JSON containing `xmppHost`) before going further.

## 5. Credentials from the Ethora admin — in the terminal

The admin panel is an API client; `scripts/ethora-admin.mjs` does the same from the terminal (login with MFA support, registration, list/create apps, profile). It needs an interactive terminal for passwords, so **the user runs it**, not you:

```bash
node <skill>/scripts/ethora-admin.mjs setup            # Cloud
node <skill>/scripts/ethora-admin.mjs setup --api https://api.chat.acme.com   # self-hosted
```
It needs a real TTY, so the `!` prefix in Claude Code does not work for it: ask the user to run it in a separate terminal window. The flow asks: account exists? (login / register) → pick an existing app or create one → saves the profile to `~/.ethora/profiles.json` (same format as `npx @ethora/setup`, so either tool works).

The password and MFA code are only accepted at the script's hidden prompt: never ask the user to paste them into the chat, and there is no environment-variable or flag alternative. Non-secret answers can be passed as flags to shorten the flow (`--email <email>`, `--app <appId>` or `--create-app "<name>"`).

**An existing profile is not proof the app still exists.** If `~/.ethora/profiles.json` already has an active profile, run `node scripts/verify-setup.mjs --user-id skill-check-1 --email skill-check-1@example.com` before reusing it. `APP_NOT_FOUND` means the app was deleted: `ethora-admin.mjs apps` shows what is left, then `use <appId>` or `create-app --name "<name>"` (ask the user which). The admin session in `~/.ethora/session.json` often still works, so these commands run without the interactive login.

Afterwards run (non-interactive, you can do it): `node scripts/ethora-admin.mjs profile --json` to read appId / endpoints, and check `appSecret` is present. If the API did not return the secret, the user copies it from admin → app → Settings → API → Secret and runs `node scripts/ethora-admin.mjs set-secret <secret>`.

Individual commands exist too (`login`, `register`, `apps`, `create-app --name`, `use <appId>`, `logout`) — see `references/admin-api.md` for what each endpoint does.

## 6. Write the config into the project

```bash
node scripts/write-env.mjs --target vite|next|cra|expo|rn --dir <projectDir>
node scripts/write-env.mjs --target backend --dir <backendDir>     # ETHORA_APP_ID / ETHORA_APP_SECRET / ETHORA_API_URL
```
It merges keys into `.env.local` / `.env` / `src/ethora.config.ts`, adds them to `.gitignore`, and never writes the secret with a public prefix. The templates read exactly these keys.

## 7. Auth — decide WITH the user whether the backend changes

"My users should land in the chat already logged in" means the **client JWT** flow, and **that always needs a server**: the JWT is signed with the app secret, and the secret must never be in a browser or mobile bundle. So tell the user plainly, before writing any code, that this mode adds one route to their backend (`GET /api/ethora/token`) plus one helper file. Then pick the path using the `backend` result from `detect-project` and the user's answer:

| Situation | What to do |
| --- | --- |
| **A. User owns a backend in this workspace** (detected, and they confirm), **in any language** | Add the token route. Node: `assets/templates/backend/ethora-token.js` + `express-route.js`, or `next-route.ts` for Next. **Other languages** (Django/FastAPI/Flask, Laravel/Symfony, Rails, Go, Spring/Ktor, ASP.NET…): write the same route idiomatically in their framework from the contract in `references/auth-modes.md` (HS256 JWT signed with the app secret, `ensureEthoraUser` via `POST /v1/users/batch` with a server JWT in `x-custom-token`), using the JWT library the project already has or the standard one for that stack; port `ethora-token.js` line by line, it is ~70 lines. Env keys are the same (`write-env.mjs --target backend` writes a plain `.env`; wire it the way that project loads config). Put it **behind the app's existing auth middleware** so the token is minted for `req.user`, not a demo user. `write-env.mjs --target backend --dir <backendDir>`; with Docker, pass `backend/.env` via `env_file` and keep it out of the image (`.dockerignore`). Frontend sends the app's session (Bearer/cookie) to the route. |
| **B. Backend exists but isn't here, or belongs to another team** (typical for a frontend dev) | Don't touch it. Write `ETHORA_BACKEND.md` into the frontend repo from `assets/templates/backend/BACKEND_HANDOFF.md`: fill `__APP_ID__`, `__API_URL__`, `__DEV_MODE__`, **never the secret**, and say who to ask for it. Copy `ethora-token.js` next to it as reference code. Meanwhile wire the frontend to the final contract (`GET <api>/api/ethora/token` with the session header) and unblock local work with a **dev token** (`client-jwt.mjs` → `write-env.mjs --dev-jwt`). Make clear that every user is the same chat user and the token expires. |
| **C. No backend at all, and the user is fine with a separate chat login** | Zero-backend modes: the chat's built-in Ethora login/registration (no `jwtLogin`; `appId` + `customAppToken`), or `customLogin` with a test account (dev only). Chat accounts are separate from the app's accounts. Web caveat: web-integration.md §7. |
| **D. No backend, but they want auto sign-in anyway** | Explain it isn't possible safely without a server. Offer: the Vite dev plugin (web, dev only), a dev token (dev only), or a minimal token service (the Express template is self-contained: one file plus a route, deployable as a serverless function). Do **not** sign tokens in the client with the secret. |

Rules for every path:
- `userId` in the token = the app's own stable user id (same on web and mobile). `ensureEthoraUser` must run before the first token: `/v1/users/client` never creates users. Names must be ≥ 2 characters (the helper handles it).
- Dev-only pieces (dev token, Vite plugin, customLogin test password) are labelled as such in code comments and in the final summary.
- If the app has its own logout, call the SDK's `logoutService.performLogout()` (web and RN) before clearing the app session.

Details and payloads: `references/auth-modes.md`. Frontend-only specifics: `references/web-integration.md` §7, `references/rn-integration.md` §5.

## 8. Verify, then run

```bash
node scripts/verify-setup.mjs --user-id <someUserId> --email <email>
```
Checks API reachability, that the app token matches the app, that a client JWT signed with the stored secret is accepted by `/v1/users/client` (creating the user if needed), and that the XMPP host answers. Fix what it reports before starting the app.

Then start the dev server / native build and ask the user to open the chat page. RN: development build (`npx expo run:ios|android`), never Expo Go. If a Metro server was running during the install, stop it and start `npx expo start --dev-client -c`: a stale transform cache shows up as the Worklets version-mismatch error. Expect a "Connecting…" spinner for a couple of seconds on the first load (JWT exchange, rooms, XMPP auth); 30 s means StrictMode is still on. A freshly created app has a "Main chat" room; sending a message there is the success criterion. Common failures and fixes: `references/troubleshooting.md`.

## 9. Finish

Tell the user, briefly: what was installed, which files were created/changed **(list frontend and backend changes separately, so a frontend dev sees at a glance whether the backend was touched)**, where the credentials live (`~/.ethora/profiles.json`, env files — gitignored), how auth works and what is dev-only (and, for path B, that `ETHORA_BACKEND.md` must go to the backend team), and the next optional steps (room provisioning from their backend, push notifications, theming via `colors`/`colorScheme`/`dark`, single-room mode with `roomJID` + `disableRooms`). Admin panel for the app: `https://app.chat.ethora.com/app/admin/apps/<appId>` (Cloud).

## Reference map

| Need | File |
| --- | --- |
| Web install, provider placement, routers, env, frontend-only options | `references/web-integration.md` |
| RN peers, native rebuild, screens, env, push | `references/rn-integration.md` |
| Auth modes, client JWT payload, user sync, rooms, token glossary | `references/auth-modes.md` |
| Handoff doc for a backend you don't own | `assets/templates/backend/BACKEND_HANDOFF.md` |
| Endpoints behind the admin panel, profile file format | `references/admin-api.md` |
| Self-hosted servers | `references/self-hosted.md` |
| Errors → fixes | `references/troubleshooting.md` |
| Official docs | https://ethora.com · admin https://app.chat.ethora.com · https://api.chat.ethora.com/api-docs/ · package READMEs on npm |
