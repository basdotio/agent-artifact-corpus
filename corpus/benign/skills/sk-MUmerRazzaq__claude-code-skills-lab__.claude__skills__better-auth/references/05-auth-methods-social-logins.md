# Social Login (OAuth)

## What Matters

- Each provider needs `clientId`, `clientSecret`, and `redirectURI`
- `redirectURI` must EXACTLY match what's in provider console
- Use environment variable for `AUTH_URL` to build redirectURI dynamically

## Server Configuration

```typescript
// lib/auth.ts
import { betterAuth } from "better-auth";

export const auth = betterAuth({
  // ... database config

  socialProviders: {
    google: {
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      redirectURI: `${process.env.AUTH_URL}/api/auth/callback/google`,
    },
    github: {
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
      redirectURI: `${process.env.AUTH_URL}/api/auth/callback/github`,
    },
    discord: {
      clientId: process.env.DISCORD_CLIENT_ID!,
      clientSecret: process.env.DISCORD_CLIENT_SECRET!,
      redirectURI: `${process.env.AUTH_URL}/api/auth/callback/discord`,
    },
  },
});
```

## Environment Variables

```bash
# .env.local
AUTH_URL="http://localhost:3000"

# Google - https://console.cloud.google.com/apis/credentials
GOOGLE_CLIENT_ID="xxx.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="GOCSPX-xxx"

# GitHub - https://github.com/settings/developers
GITHUB_CLIENT_ID="Iv1.xxx"
GITHUB_CLIENT_SECRET="xxx"

# Discord - https://discord.com/developers/applications
DISCORD_CLIENT_ID="xxx"
DISCORD_CLIENT_SECRET="xxx"
```

## Client Usage

```typescript
import { authClient } from "@/lib/auth-client";

// Sign in with Google
const signInWithGoogle = async () => {
  await authClient.signIn.social({
    provider: "google",
    callbackURL: "/dashboard",
  });
};

// Sign in with GitHub
const signInWithGitHub = async () => {
  await authClient.signIn.social({
    provider: "github",
    callbackURL: "/dashboard",
  });
};
```

## Provider Console Setup

| Provider | Console URL | Redirect URI |
|----------|-------------|--------------|
| Google | https://console.cloud.google.com/apis/credentials | `{AUTH_URL}/api/auth/callback/google` |
| GitHub | https://github.com/settings/developers | `{AUTH_URL}/api/auth/callback/github` |
| Discord | https://discord.com/developers/applications | `{AUTH_URL}/api/auth/callback/discord` |

## Common Mistakes

| Mistake | Result | Fix |
|---------|--------|-----|
| redirectURI mismatch | "redirect_uri_mismatch" error | Copy exact URL to provider console |
| HTTP in production | Callback fails | Use HTTPS in production |
| Hardcoded localhost | Fails in production | Use `AUTH_URL` env variable |
