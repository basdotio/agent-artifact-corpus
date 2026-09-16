# Password Reset

## What Matters

- Requires `sendResetPassword` function in emailAndPassword config
- Two-step flow: request reset → complete reset with token
- Token comes from URL query parameter
- **Next.js 16**: `searchParams` is now a Promise

## Server Configuration

```typescript
// lib/auth.ts
import { betterAuth } from "better-auth";

export const auth = betterAuth({
  emailAndPassword: {
    enabled: true,
    sendResetPassword: async ({ user, url, token }) => {
      await sendEmail({
        to: user.email,
        subject: "Reset your password",
        html: `<a href="${url}">Reset Password</a>`,
      });
    },
  },
});
```

## Client Usage

### Request Password Reset

```typescript
import { authClient } from "@/lib/auth-client";

const requestReset = async (email: string) => {
  const { error } = await authClient.forgetPassword({
    email,
    redirectTo: "/reset-password",
  });

  if (error) {
    console.error(error.message);
    return false;
  }

  return true;
};
```

### Complete Password Reset

```typescript
import { authClient } from "@/lib/auth-client";

const resetPassword = async (token: string, newPassword: string) => {
  const { error } = await authClient.resetPassword({
    token,
    newPassword,
  });

  return !error;
};
```

## Reset Password Page (Next.js 16)

### Option 1: Server Component with async searchParams

```typescript
// app/reset-password/page.tsx
import { ResetPasswordForm } from "./reset-form";

export default async function ResetPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>  // Promise in Next.js 16
}) {
  const { token } = await searchParams;  // Must await

  if (!token) {
    return <p>Invalid reset link.</p>;
  }

  return <ResetPasswordForm token={token} />;
}
```

```typescript
// app/reset-password/reset-form.tsx
"use client";

import { useState } from "react";
import { authClient } from "@/lib/auth-client";

export function ResetPasswordForm({ token }: { token: string }) {
  const [password, setPassword] = useState("");
  const [done, setDone] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const { error } = await authClient.resetPassword({
      token,
      newPassword: password,
    });
    if (!error) setDone(true);
  };

  if (done) {
    return <p>Password reset! <a href="/signin">Sign in</a></p>;
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="New password"
        required
      />
      <button type="submit">Reset Password</button>
    </form>
  );
}
```

### Option 2: Client Component with useSearchParams

```typescript
// app/reset-password/page.tsx
"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { authClient } from "@/lib/auth-client";

function ResetForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [password, setPassword] = useState("");
  const [done, setDone] = useState(false);

  if (!token) {
    return <p>Invalid reset link.</p>;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const { error } = await authClient.resetPassword({
      token,
      newPassword: password,
    });
    if (!error) setDone(true);
  };

  if (done) {
    return <p>Password reset! <a href="/signin">Sign in</a></p>;
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="New password"
        required
      />
      <button type="submit">Reset Password</button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<p>Loading...</p>}>
      <ResetForm />
    </Suspense>
  );
}
```

## Forgot Password Page

```typescript
// app/forgot-password/page.tsx
"use client";

import { useState } from "react";
import { authClient } from "@/lib/auth-client";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await authClient.forgetPassword({
      email,
      redirectTo: "/reset-password",
    });
    setSent(true);
  };

  if (sent) {
    return <p>Check your email for a reset link.</p>;
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
        required
      />
      <button type="submit">Send Reset Link</button>
    </form>
  );
}
```

## Common Mistakes

| Mistake | Result | Fix |
|---------|--------|-----|
| Missing sendResetPassword | Emails never sent | Implement the function |
| `searchParams` without await | Type error in Next.js 16 | Use `await searchParams` |
| Missing Suspense with useSearchParams | Hydration error | Wrap in Suspense boundary |
