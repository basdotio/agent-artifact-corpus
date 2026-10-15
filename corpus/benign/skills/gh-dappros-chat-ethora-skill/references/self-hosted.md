# Self-hosted Ethora servers

Customers with a self-hosted deployment run the **same API and XMPP stack** under their own hostnames (e.g. `api.chat.acme.com`, `xmpp.chat.acme.com`, admin at `app.chat.acme.com`). Nothing changes in the SDK contract — only the endpoints.

> **Only Ethora-compatible servers work.** "Self-hosted" means an Ethora server deployment (the same API as `https://api.chat.ethora.com/api-docs/` and the same XMPP stack), not "any API". A backend that doesn't implement these exact endpoints and payloads — the user's own REST API, Firebase, another chat product — will not work with the SDK or with these scripts. Tell the user this before collecting endpoints. Quick check: `GET <api>/v1/apps/get-config?domainName=app` must return JSON with `xmppHost`.

## Ask the user for

1. API origin — e.g. `https://api.chat.acme.com` (with or without `/v1`).
2. Optionally XMPP host / WebSocket / conference. If not known, derive from `GET <api>/v1/apps/get-config?domainName=app` → `xmppHost`:
   - WebSocket `wss://<xmppHost>/ws` (older installs used port `5443`: `wss://<xmppHost>:5443/ws` — try the plain one first)
   - conference `conference.<xmppHost>`
3. Base app `domainName` if their install does not use `app` (needed only for terminal login).

## Terminal flow

```bash
node scripts/ethora-admin.mjs setup --api https://api.chat.acme.com [--base-domain app]
```
Everything else (login/register, list/create apps, profile, write-env) is identical; the profile gets `type: "self-hosted"` and the custom endpoints. If `get-config` is not reachable (older backend), ask the user for the base app id + app token and use `use <appId>` after `login`.

## Config differences

Only the values:
```ts
baseUrl: 'https://api.chat.acme.com',
xmppSettings: { devServer: 'wss://xmpp.chat.acme.com/ws' /* RN: 'xmpp.chat.acme.com' */, host: 'xmpp.chat.acme.com', conference: 'conference.xmpp.chat.acme.com' },
```
Push for self-hosted uses the same `/v1/push/*` endpoints; a legacy `ethora-node-push` gateway is configured via `pushNotifications.apiUrl` (RN) if they still run one.

## Checks

- `node scripts/verify-setup.mjs` — API reachable, token, client-JWT exchange, XMPP DNS/WS.
- CORS: the browser calls the API directly, so the API must allow the app's origin (ask their ops if `verify-setup` passes but the browser fails with CORS).
- TLS: WebSocket must be `wss://` with a valid certificate; mixed content is blocked on https pages.
