# Passkey Authentication (WebAuthn)

## What Matters

- Passwordless auth using biometrics or security keys
- Requires `@better-auth/passkey` package (separate install)
- Plugin needed on both server and client

## Install

```bash
npm install @better-auth/passkey
```

## Server Configuration

```typescript
// lib/auth.ts
import { betterAuth } from "better-auth";
import { passkey } from "@better-auth/passkey";

export const auth = betterAuth({
  // ... database config

  plugins: [
    passkey(),
  ],
});
```

## Client Configuration

```typescript
// lib/auth-client.ts
import { createAuthClient } from "better-auth/react";
import { passkeyClient } from "@better-auth/passkey/client";

export const authClient = createAuthClient({
  plugins: [passkeyClient()],
});
```

## Client Usage

### Register a Passkey (in account settings)

```typescript
import { authClient } from "@/lib/auth-client";

const registerPasskey = async () => {
  const { error } = await authClient.passkey.register({
    name: "My Laptop", // User-friendly name
  });

  if (error) {
    console.error(error.message);
  }
};
```

### Sign In with Passkey

```typescript
const signInWithPasskey = async () => {
  const { error } = await authClient.signIn.passkey({
    autoFill: true, // Enable browser autofill prompt
  });

  if (error) {
    console.error(error.message);
  }
};
```

### Enable Autofill on Sign-In Page

```typescript
import { useEffect } from "react";
import { authClient } from "@/lib/auth-client";

function SignInPage() {
  useEffect(() => {
    // Pre-load passkey credentials for autofill
    if (window.PublicKeyCredential?.isConditionalMediationAvailable) {
      authClient.signIn.passkey({ autoFill: true });
    }
  }, []);

  return (
    <input
      type="email"
      autoComplete="username webauthn"
      placeholder="Email"
    />
  );
}
```

## API Endpoints Created

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/passkey/register` | POST | Register new passkey |
| `/api/auth/passkey/signin` | POST | Sign in with passkey |
| `/api/auth/passkey/list-user-passkeys` | GET | List user's passkeys |
| `/api/auth/passkey/delete-passkey` | POST | Delete a passkey |

## Database

Run CLI after adding plugin:

```bash
npx @better-auth/cli generate
npx prisma db push
```

## Common Mistakes

| Mistake | Result | Fix |
|---------|--------|-----|
| Missing package install | Import error | `npm install @better-auth/passkey` |
| Missing client plugin | Method not found | Add `passkeyClient()` |
| No HTTPS in production | WebAuthn fails | Passkeys require HTTPS |
