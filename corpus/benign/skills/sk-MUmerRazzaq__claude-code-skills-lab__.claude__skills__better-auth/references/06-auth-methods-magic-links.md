# Magic Link Authentication

## What Matters

- Passwordless login via email link
- Requires `magicLink` plugin on server and client
- YOU must implement `sendMagicLink` function

## Server Configuration

```typescript
// lib/auth.ts
import { betterAuth } from "better-auth";
import { magicLink } from "better-auth/plugins";

export const auth = betterAuth({
  // ... database config

  plugins: [
    magicLink({
      sendMagicLink: async ({ email, url, token }) => {
        await sendEmail({
          to: email,
          subject: "Sign in to Your App",
          html: `<a href="${url}">Click here to sign in</a>`,
        });
      },
      expiresIn: 300, // 5 minutes
    }),
  ],
});
```

## Client Configuration

```typescript
// lib/auth-client.ts
import { createAuthClient } from "better-auth/react";
import { magicLinkClient } from "better-auth/client/plugins";

export const authClient = createAuthClient({
  plugins: [magicLinkClient()],
});
```

## Client Usage

```typescript
import { authClient } from "@/lib/auth-client";

const requestMagicLink = async (email: string) => {
  const { error } = await authClient.signIn.magicLink({
    email,
    callbackURL: "/dashboard",
  });

  if (error) {
    console.error(error.message);
    return;
  }

  // Show "check your email" message
};
```

## Database

Run CLI after adding plugin:

```bash
npx @better-auth/cli generate
npx prisma db push
```

## Common Mistakes

| Mistake | Result | Fix |
|---------|--------|-----|
| Missing client plugin | Method not found | Add `magicLinkClient()` |
| Not regenerating schema | Missing tables | Run CLI generate |
