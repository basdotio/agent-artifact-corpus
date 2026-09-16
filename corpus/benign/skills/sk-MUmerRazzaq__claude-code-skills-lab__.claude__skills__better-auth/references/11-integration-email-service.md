# Email Service Integration

## What Matters

- better-auth doesn't send emails - YOU provide the `sendEmail` function
- Works with any email provider (Resend, SendGrid, Nodemailer, etc.)
- Create a reusable utility function

## Resend Setup (Recommended)

### Install

```bash
npm install resend
```

### Environment Variable

```bash
# .env.local
RESEND_API_KEY="re_xxxxxxxxxxxxxxxx"
```

### Email Utility

```typescript
// lib/email.ts
import { Resend } from "resend";

const resend = new Resend(process.env.RESEND_API_KEY);

interface SendEmailParams {
  to: string;
  subject: string;
  html: string;
}

export async function sendEmail({ to, subject, html }: SendEmailParams) {
  const { error } = await resend.emails.send({
    from: "Your App <noreply@yourdomain.com>", // Must be verified domain
    to,
    subject,
    html,
  });

  if (error) {
    console.error("Email error:", error);
    throw error;
  }
}
```

### Use in Auth Config

```typescript
// lib/auth.ts
import { betterAuth } from "better-auth";
import { sendEmail } from "./email";

export const auth = betterAuth({
  emailVerification: {
    sendVerificationEmail: async ({ user, url }) => {
      await sendEmail({
        to: user.email,
        subject: "Verify your email",
        html: `<a href="${url}">Verify Email</a>`,
      });
    },
  },

  emailAndPassword: {
    enabled: true,
    sendResetPassword: async ({ user, url }) => {
      await sendEmail({
        to: user.email,
        subject: "Reset your password",
        html: `<a href="${url}">Reset Password</a>`,
      });
    },
  },
});
```

## Alternative: Nodemailer

```typescript
// lib/email.ts
import nodemailer from "nodemailer";

const transporter = nodemailer.createTransport({
  host: process.env.SMTP_HOST,
  port: Number(process.env.SMTP_PORT),
  auth: {
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASS,
  },
});

export async function sendEmail({ to, subject, html }: {
  to: string;
  subject: string;
  html: string;
}) {
  await transporter.sendMail({
    from: process.env.SMTP_FROM,
    to,
    subject,
    html,
  });
}
```

## Alternative: SendGrid

```typescript
// lib/email.ts
import sgMail from "@sendgrid/mail";

sgMail.setApiKey(process.env.SENDGRID_API_KEY!);

export async function sendEmail({ to, subject, html }: {
  to: string;
  subject: string;
  html: string;
}) {
  await sgMail.send({
    from: "noreply@yourdomain.com",
    to,
    subject,
    html,
  });
}
```

## Common Mistakes

| Mistake | Result | Fix |
|---------|--------|-----|
| Unverified domain | Emails rejected | Verify domain in provider dashboard |
| Missing API key | Runtime error | Set environment variable |
| Using `onboarding@resend.dev` in prod | Blocked emails | Use your verified domain |
