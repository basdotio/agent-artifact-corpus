# Security checklist

Check the relevant sections whenever a change touches input handling, authentication, files, external calls, or secrets.

## Input
- Validate every input at the boundary: type, length, range, format. In FastAPI, Pydantic models do most of this; add constraints (max_length, ge, le) instead of trusting clients.
- Reject unknown fields where the framework allows it, so typos do not silently pass.

## Injection
- SQL: use the ORM or parameterized queries. Never build SQL with f-strings or string concatenation.
- Shell: never pass user input to a shell. Use argument lists (`subprocess.run([...], shell=False)`).
- Templates and HTML: rely on auto-escaping, and never mark user content as safe.
- NoSQL: do not pass raw request objects as query filters.

## Authentication and authorization
- Every endpoint states who may call it, and the check runs on the server for every request.
- Check ownership as well as login: user A must not read user B's order by changing an ID in the URL.
- Hash passwords with a slow algorithm (argon2 or bcrypt). Short-lived access tokens, rotating refresh tokens.
- Apply rate limits to login, signup, password reset, and any expensive endpoint.

## Secrets
- No secrets in code, tests, fixtures, logs, or commit messages. Load them from environment variables or Secret Manager.
- Never read or print .env files during a session; the file guard blocks reading them. Ask the user for variable names instead.
- If a secret was committed, tell the user to rotate it. Deleting it from the latest commit is not enough.

## Network and files
- SSRF: when the server fetches a URL supplied by a user, allow-list hosts, block private and metadata addresses, and set timeouts.
- Path traversal: never join user input into file paths without normalizing and checking that the result stays inside the allowed folder.
- Uploads: check size and type, store outside the web root or in object storage, and generate the stored file names yourself.
- Deserialization: never unpickle or deserialize untrusted data with formats that can execute code.

## Web specifics
- CORS: allow only the origins that need access. Never combine a wildcard origin with credentials.
- Cookies: Secure, HttpOnly, and SameSite. CSRF protection for cookie-authenticated forms.
- Send security headers (Content-Security-Policy, X-Content-Type-Options) from the server or the CDN.

## Dependencies
- Scan regularly: `pip-audit` for Python, `npm audit` for JavaScript, and the Gradle dependency-check or GitHub Dependabot for Android.
- Pin versions and review changelogs before upgrading anything security-relevant.

## Android
- No API secrets inside the APK; anything shipped can be extracted. Keep secrets on the server.
- Keystores and their passwords never go into the repository. Use local.properties (git-ignored) or CI secrets.
- Use the network security config to block cleartext traffic, and keep R8 or ProGuard on for release builds.
- Store tokens in EncryptedSharedPreferences or DataStore with encryption, not in plain preferences.

## Personal data
- Collect only what the feature needs, and know where it is stored and for how long.
- Mask personal data in logs and analytics.
