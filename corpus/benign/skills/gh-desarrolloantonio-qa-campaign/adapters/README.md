# Backend adapters

The one piece this skill cannot give you: **how to ask your server what is true**.

The API oracle (R5) is what turns "the screen says the label is on the card" into "the label is on
the card". Everything else in the harness reads the *client*; this reads the server. "Source of
truth" is not automatic — R5 says how disagreements are adjudicated — but online it is the oracle
that decides.

## What an adapter has to do

A small module — a Python file is plenty — that:

1. Reads credentials from **`qa.credentials.json`**, a file that is **gitignored in your project**
   (§2.1 adds it). `qa.config.json` holds no secrets. Never hard-code them, never print them, never
   pass them — or a session token obtained with them — on a command line (R11). One shape for every
   project, so a human who has filled one in knows the next:

   ```json
   {
     "accounts": {
       "A": { "username": "qa-owner", "password": "…" },
       "B": { "username": "qa-recipient", "password": "…" },
       "C": { "token": "…" }
     },
     "serverSecret": "… only for a disposable server you run (R11)"
   }
   ```

   Per account, `username` + `password`, **or** `token` when the server hands out one you can paste
   (an app password, a session cookie), **or** whatever identifier the server signs people in with —
   `nfc` for a card id, for instance. Keys that don't apply are left out. When the session lives in
   another app (SKILL.md R11, mechanism 5), the adapter can still sign in through the API with a test
   identifier, and no password exists anywhere.
2. Authenticates as any of the campaign's accounts (`A` owner, `B` recipient, `C` negative control,
   or one per role — R7) **the way this server signs people in**: a password, an app password, a
   token it hands out, or a token made with the server's own secret on a disposable server you run
   (R11). `qa.credentials.json` holds whichever of those it is — it need not hold a password at all.
   The adapter talks to the test server agreed at setup (§2.1), and to nothing else.
3. Exposes one `request(method, path, account="A", ...)` that returns `(status, parsed_body)` — and an
   `upload(path, file, fields, account="A")` when the product takes files: photos and attachments are
   fixtures too, and a fix about them needs a record that has some (measured).
4. Knows the server's **quirks**, and records them next to the code rather than in someone's head.
5. **Knows when its own session died.** Signing out in the app revokes the session the adapter may
   have cached for the same account: drop that cached token whenever the app signs out. And treat a
   "not authenticated" answer as an authentication error **whatever its status** — one server said
   400 on some endpoints, and the adapter, re-logging in only on 401, returned
   `{"error": "User is not authenticated"}` as if it were data (measured). An oracle that goes dead
   quietly is worse than none (R8).

That last point is most of the value. Real quirks found this way on one server (a self-hosted
suite; yours will have different ones), each of which had produced a wrong conclusion first:

- a list endpoint that reports `readonly: false` for a resource the single-item endpoint reports as
  `readonly: true` — so a client can only learn the truth by attempting a write;
- a write on a read-only share answered with **412**, not 403, so an authorization guard never fired;
- a list ETag that is a **content hash**, so it returns to a previous value when the server returns
  to a previous state — and a conditional request then gets a 304 that skips a needed prune;
- `limit` above a certain value answered with HTTP 500;
- a `DELETE` that is permanent rather than a trash.

## Shape

```python
def request(method, path, account="A", params=None, json=None, headers=None):
    """Returns (status, body). Body is parsed JSON when it is JSON, text otherwise."""

def account(key="A"):
    """accounts[key] from qa.credentials.json: {username, password} or {token}. Never printed."""
```

Keep it under a few hundred lines. It is a test oracle, not a client library — it should be
*obviously* correct by reading it, because when it and the app disagree you need to know which one
to believe.

## A backend you don't own

Some backends cannot be queried programmatically as A/B/C — CloudKit's private database, a vendor
sync service with no server-to-server API. Then the API oracle is whatever *can* see the server's
state independently of the client under test: the vendor's console (CloudKit Dashboard), or the
same account signed in on a **second device**. Record that in CAMPAIGN.md §5, and the gate wording
changes from "verified through the API" to "verified on the second device". It is a weaker oracle;
say so rather than pretend.
