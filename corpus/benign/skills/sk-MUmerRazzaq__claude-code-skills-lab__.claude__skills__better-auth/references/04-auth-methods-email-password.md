# Email & Password Authentication

## What Matters

- Enable with `emailAndPassword: { enabled: true }`
- Password reset requires YOU to implement `sendResetPassword`
- Email verification requires YOU to implement `sendVerificationEmail`

## Server Configuration

```typescript
// lib/auth.ts
import { betterAuth } from "better-auth";

export const auth = betterAuth({
  // ... database config

  emailAndPassword: {
    enabled: true,
    minPasswordLength: 8,
    maxPasswordLength: 128,
    autoSignIn: true, // Sign in after registration

    // Required for password reset
    sendResetPassword: async ({ user, url, token }) => {
      await sendEmail({
        to: user.email,
        subject: "Reset your password",
        html: `<a href="${url}">Reset Password</a>`,
      });
    },
  },

  // Email verification (recommended for production)
  emailVerification: {
    sendVerificationEmail: async ({ user, url, token }) => {
      await sendEmail({
        to: user.email,
        subject: "Verify your email",
        html: `<a href="${url}">Verify Email</a>`,
      });
    },
    sendOnSignUp: true,
    autoSignInAfterVerification: true,
  },
});
```

## Client Usage

### Sign Up

```typescript
import { authClient } from "@/lib/auth-client";

const signUp = async (email: string, password: string, name: string) => {
  const { data, error } = await authClient.signUp.email({
    email,
    password,
    name,
  });

  if (error) {
    console.error(error.message);
    return;
  }

  // Success - user created
  console.log(data.user);
};
```

### Sign In

```typescript
const signIn = async (email: string, password: string) => {
  const { data, error } = await authClient.signIn.email({
    email,
    password,
  });

  if (error) {
    console.error(error.message);
    return;
  }

  // Success - user signed in
  window.location.href = "/dashboard";
};
```

### Sign Out

```typescript
const signOut = async () => {
  await authClient.signOut();
  window.location.href = "/";
};
```

### Request Password Reset

```typescript
const requestReset = async (email: string) => {
  const { error } = await authClient.forgetPassword({
    email,
    redirectTo: "/reset-password", // Where user lands after clicking email link
  });

  if (error) {
    console.error(error.message);
  }
};
```

### Complete Password Reset

```typescript
// On /reset-password page, get token from URL
const resetPassword = async (newPassword: string) => {
  const token = new URLSearchParams(window.location.search).get("token");

  const { error } = await authClient.resetPassword({
    token: token!,
    newPassword,
  });

  if (error) {
    console.error(error.message);
  }
};
```

## API Endpoints Created

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/sign-up/email` | POST | Register new user |
| `/api/auth/sign-in/email` | POST | Sign in user |
| `/api/auth/sign-out` | POST | Sign out user |
| `/api/auth/forget-password` | POST | Request password reset |
| `/api/auth/reset-password` | POST | Complete password reset |
| `/api/auth/verify-email` | GET | Verify email from link |

## Common Mistakes

| Mistake | Result | Fix |
|---------|--------|-----|
| Missing sendResetPassword | Password reset silently fails | Implement the async function |
| Missing sendVerificationEmail | Email verification fails | Implement the async function |
| No email service configured | Emails never sent | Set up Resend/SendGrid/etc |
