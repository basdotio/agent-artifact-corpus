# Authentication

Load this file when a task involves login, cookie reuse, or protected pages.

## Preferred Order

1. Auth vault
2. Existing browser profile
3. Session-name persistence
4. Manual state save/load

This order minimizes secret exposure while keeping repeat runs practical.

## Auth Vault

Use auth vault when credentials need to be reused but should not be echoed back
into prompts or shell history.

```bash
echo "$PASSWORD" | agent-browser auth save myapp \
  --url https://app.example.com/login \
  --username user@example.com \
  --password-stdin

agent-browser auth login myapp
```

Use this as the default recommendation when the user wants recurring login
automation.

## Existing Profile Reuse

Use an existing Chrome profile when the user is already logged in and the task
is local, one-off, or interactive.

```bash
agent-browser profiles
agent-browser --profile Default open https://app.example.com
```

This is fast, but it inherits whatever cookies and extensions exist in that
profile.

## Session-Name Persistence

Use `--session-name` when the goal is to save and restore browser state across
multiple runs without reusing a full browser profile.

```bash
agent-browser --session-name myapp open https://app.example.com/login
# complete login flow
agent-browser close

agent-browser --session-name myapp open https://app.example.com/dashboard
```

## Manual State Save/Load

Use raw state files only when the task explicitly needs them or another flow is
not practical.

```bash
agent-browser state save ./auth-state.json
agent-browser state load ./auth-state.json
agent-browser open https://app.example.com/dashboard
```

Rules:

- Treat state files as secrets.
- Add them to `.gitignore`.
- Delete one-off state files after use.
- Prefer encrypted-at-rest configuration when available.

## Delayed Login Screens and SPAs

If the login form renders slowly:

- Use `agent-browser wait --text "Sign in"` or `wait <selector>` before
  filling.
- Prefer `auth login` when the vault already knows the login URL and
  credentials.
- Avoid `networkidle` if the site polls or keeps sockets open.

## 2FA, Captcha, and Human Steps

Do not promise full automation for:

- MFA codes
- WebAuthn or passkeys
- captcha challenges
- SSO flows that require device approval

The reliable pattern is:

1. Open the login page.
2. Automate only the stable steps.
3. Let the human complete the challenge.
4. Save state after successful login for reuse.

## Verification

After login, verify success with one or more of:

- `agent-browser get url`
- `agent-browser wait --url "**/dashboard"`
- `agent-browser wait --text "Welcome"`
- `agent-browser snapshot -i`

Do not assume login succeeded just because the submit button was clicked.
