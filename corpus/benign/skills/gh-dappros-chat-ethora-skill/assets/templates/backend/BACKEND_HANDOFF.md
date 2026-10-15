# Ethora chat: the one backend endpoint we need

The app now has an Ethora chat. For users to land in it **already signed in** (no second login), the backend has to sign a short-lived token for the current user. This cannot be done in the frontend: signing needs the Ethora **app secret**, and anything shipped to a browser or a mobile bundle is public.

## Contract

```
GET /api/ethora/token
Authorization: <the app's normal session — cookie or Bearer, whatever /me already uses>

200 { "token": "<client JWT>" }
401 if there is no session
```

The frontend calls it once when the chat opens and passes the token to the chat component (`jwtLogin`).

## What the endpoint does

1. **Find the current user** from the existing session (same as `/me`).
2. **Make sure the user exists in the Ethora app** (idempotent, can be cached per user):
   `POST {ETHORA_API_URL}/v1/users/batch`, header `x-custom-token: <server JWT>`, body
   `{ "bypassEmailConfirmation": true, "usersList": [{ "uuid": "<user id>", "email": "...", "firstName": "...", "lastName": "..." }] }`
   - `firstName` / `lastName` must be **at least 2 characters** (otherwise 422). If you only have one name field, split it and use a placeholder such as `User`.
   - An "already exists" error is fine.
3. **Sign the client JWT**, HS256 with the app secret:
   `{ "data": { "type": "client", "appId": "<ETHORA_APP_ID>", "userId": "<user id>" }, "iat": <now>, "exp": <now + 12h> }`
   - The server JWT from step 2 is the same thing with `{ "data": { "type": "server", "appId": "<ETHORA_APP_ID>" } }`.
   - `userId` is **your** stable user id. The same id always maps to the same chat account (web and mobile).

## Configuration (server only, never with a public prefix)

```
ETHORA_APP_ID=__APP_ID__
ETHORA_APP_SECRET=<ask the person who set up Ethora, or admin panel → app → Settings → API>
ETHORA_API_URL=__API_URL__
```

## Ready-made code

- Node / Express: `ethora-token.js` (no dependencies) + a route:
  ```js
  const { clientToken, ensureEthoraUser } = require('./ethora-token');
  app.get('/api/ethora/token', requireAuth, async (req, res) => {
    await ensureEthoraUser({ userId: req.user.id, email: req.user.email, firstName: req.user.firstName, lastName: req.user.lastName });
    res.json({ token: clientToken(req.user.id) });
  });
  ```
- Next.js App Router: `app/api/ethora/token/route.ts`.
- Other languages: any HS256 JWT library and an HTTP client. The payloads above are the whole protocol.

## How to check it

```bash
curl -H "Authorization: Bearer <a real session token>" https://<backend>/api/ethora/token    # → { "token": "eyJ…" }
curl -X POST __API_URL__/v1/users/client -H "x-custom-token: <that token>"                  # → 200 with "user"
```

Until this endpoint ships, the frontend uses a temporary dev setup (__DEV_MODE__). It will be removed once the endpoint is live.
