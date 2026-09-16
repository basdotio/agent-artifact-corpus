# Two-Factor Authentication (2FA)

## What Matters

- Uses TOTP (Time-based One-Time Password) with authenticator apps
- Generates backup codes for account recovery
- Requires `twoFactor` plugin on server and client

## Server Configuration

```typescript
// lib/auth.ts
import { betterAuth } from "better-auth";
import { twoFactor } from "better-auth/plugins";

export const auth = betterAuth({
  appName: "Your App Name", // Used as TOTP issuer

  plugins: [
    twoFactor({
      issuer: "Your App Name", // Shows in authenticator app
      // Optional: customize backup codes
      backupCodes: {
        amount: 10,
        length: 10,
      },
    }),
  ],
});
```

## Client Configuration

```typescript
// lib/auth-client.ts
import { createAuthClient } from "better-auth/react";
import { twoFactorClient } from "better-auth/client/plugins";

export const authClient = createAuthClient({
  plugins: [
    twoFactorClient({
      onTwoFactorRedirect() {
        window.location.href = "/verify-2fa";
      },
    }),
  ],
});
```

## Client Usage

### Enable 2FA (in account settings)

```typescript
import { authClient } from "@/lib/auth-client";

const enable2FA = async (password: string) => {
  const { data, error } = await authClient.twoFactor.enable({
    password, // Verify user's password first
  });

  if (error) {
    console.error(error.message);
    return;
  }

  // Display QR code from data.totpURI
  // Show backup codes from data.backupCodes
  console.log("Scan this QR:", data.totpURI);
  console.log("Save these backup codes:", data.backupCodes);
};
```

### Verify TOTP Code (after sign-in)

```typescript
const verify2FA = async (code: string) => {
  const { error } = await authClient.twoFactor.verifyTotp({
    code, // 6-digit code from authenticator app
  });

  if (error) {
    console.error(error.message);
    return;
  }

  // Success - redirect to dashboard
  window.location.href = "/dashboard";
};
```

### Use Backup Code

```typescript
const useBackupCode = async (code: string) => {
  const { error } = await authClient.twoFactor.verifyBackupCode({
    code, // One of the backup codes
  });

  if (error) {
    console.error(error.message);
  }
};
```

### Disable 2FA

```typescript
const disable2FA = async (password: string) => {
  const { error } = await authClient.twoFactor.disable({
    password, // Verify user's password
  });
};
```

## 2FA Sign-In Flow

```
1. User signs in with email/password
2. Server returns { twoFactorRedirect: true }
3. onTwoFactorRedirect callback fires → redirect to /verify-2fa
4. User enters 6-digit code from authenticator app
5. Call authClient.twoFactor.verifyTotp({ code })
6. Success → user is fully signed in
```

## API Endpoints Created

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/two-factor/enable` | POST | Enable 2FA, get QR code |
| `/api/auth/two-factor/disable` | POST | Disable 2FA |
| `/api/auth/two-factor/verify-totp` | POST | Verify TOTP code |
| `/api/auth/two-factor/verify-backup-code` | POST | Use backup code |

## Database

Run CLI after adding plugin:

```bash
npx @better-auth/cli generate
npx prisma db push
```

## Common Mistakes

| Mistake | Result | Fix |
|---------|--------|-----|
| Missing appName | Generic issuer in authenticator | Set `appName` in auth config |
| Not showing backup codes | User locked out | Always display and tell user to save |
| Missing client plugin | Methods not found | Add `twoFactorClient()` |
