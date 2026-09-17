---
name: auth-patterns
description: Authentication security patterns and standards for NextAuth.js v5. Use when implementing or reviewing authentication code.
---

# Authentication Patterns and Standards

Security patterns and best practices for implementing authentication in the Posterns MVP using NextAuth.js v5 (Auth.js).

## Security Requirements

### Password Security

**Hashing**:
- **Algorithm**: bcrypt
- **Salt rounds**: 12 (minimum)
- **File**: `lib/auth/password.ts`

```typescript
import bcrypt from 'bcryptjs';

const SALT_ROUNDS = 12;

export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, SALT_ROUNDS);
}

export async function verifyPassword(
  password: string,
  hashedPassword: string
): Promise<boolean> {
  return bcrypt.compare(password, hashedPassword);
}
```

**Password Requirements**:
- Minimum 8 characters
- At least one uppercase letter (A-Z)
- At least one lowercase letter (a-z)
- At least one number (0-9)
- Validated with Zod schema

**Validation Pattern**:
```typescript
import { z } from 'zod';

const password = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
  .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
  .regex(/[0-9]/, 'Password must contain at least one number');
```

### Token Security

**Token Generation**:
- **Algorithm**: `crypto.randomBytes(32)`
- **Format**: Hexadecimal string
- **File**: `lib/auth/tokens.ts`

```typescript
import crypto from 'crypto';

export function generateVerificationToken(): string {
  return crypto.randomBytes(32).toString('hex');
}

export function generatePasswordResetToken(): string {
  return crypto.randomBytes(32).toString('hex');
}
```

**Token Expiry**:
- **Email verification**: 24 hours
- **Password reset**: 1 hour

```typescript
export const TOKEN_EXPIRY = {
  EMAIL_VERIFICATION: 24 * 60 * 60 * 1000, // 24 hours
  PASSWORD_RESET: 60 * 60 * 1000, // 1 hour
} as const;

export function getTokenExpiry(
  type: 'EMAIL_VERIFICATION' | 'PASSWORD_RESET'
): Date {
  return new Date(Date.now() + TOKEN_EXPIRY[type]);
}
```

**Token Usage**:
- **One-time use**: Delete token after successful use
- **Expiry check**: Validate `expires` field before accepting token
- **Storage**: Store in `VerificationToken` table with type field

### Rate Limiting

**Endpoints and Limits**:
- **Login**: 5 requests per minute
- **Register**: 3 requests per minute
- **Forgot Password**: 3 requests per minute
- **Verify Email**: 5 requests per minute
- **Resend Verification**: 2 requests per minute

**Implementation** (`lib/rate-limit.ts`):
```typescript
export const authRateLimiter = {
  login: (identifier: string) =>
    rateLimit(`login:${identifier}`, 5, 60000),
  register: (identifier: string) =>
    rateLimit(`register:${identifier}`, 3, 60000),
  forgotPassword: (identifier: string) =>
    rateLimit(`forgot:${identifier}`, 3, 60000),
  verifyEmail: (identifier: string) =>
    rateLimit(`verify:${identifier}`, 5, 60000),
  resendVerification: (identifier: string) =>
    rateLimit(`resend:${identifier}`, 2, 60000),
};
```

**Client Identification**:
```typescript
export function getClientIdentifier(request: Request): string {
  const forwarded = request.headers.get('x-forwarded-for');
  const ip = forwarded ? forwarded.split(',')[0].trim() : 'unknown';
  return ip;
}
```

**Rate Limit Response**:
```typescript
if (!rateLimitResult.success) {
  return NextResponse.json(
    { error: 'Too many requests. Please try again later.' },
    { status: 429 }
  );
}
```

## Authentication Flows

### Registration Flow

1. **User submits**: name, email, password, confirmPassword
2. **Validate input**: Zod schema validation
3. **Normalize email**: Convert to lowercase
4. **Check existing user**: Query database for email
5. **Hash password**: bcrypt with 12 salt rounds
6. **Create user**: Insert into database
7. **Generate token**: 32-byte random hex string
8. **Create verification token**: Store in VerificationToken table
9. **Send email**: Email verification link via Resend
10. **Return success**: Prompt user to check email

**API Route Pattern** (`app/api/auth/register/route.ts`):
```typescript
export async function POST(request: Request) {
  try {
    // Rate limiting
    const clientId = getClientIdentifier(request);
    const rateLimitResult = authRateLimiter.register(clientId);
    if (!rateLimitResult.success) {
      return NextResponse.json(
        { error: 'Too many requests. Please try again later.' },
        { status: 429 }
      );
    }

    const body = await request.json();

    // Validate input
    const validated = registerSchema.safeParse(body);
    if (!validated.success) {
      return NextResponse.json(
        { error: 'Invalid input', details: validated.error.flatten() },
        { status: 400 }
      );
    }

    const { name, email, password } = validated.data;
    const normalizedEmail = email.toLowerCase();

    // Check existing user
    const existingUser = await prisma.user.findUnique({
      where: { email: normalizedEmail },
    });

    if (existingUser) {
      return NextResponse.json(
        { error: 'An account with this email already exists' },
        { status: 400 }
      );
    }

    // Hash password
    const hashedPassword = await hashPassword(password);

    // Create user
    const user = await prisma.user.create({
      data: {
        name,
        email: normalizedEmail,
        password: hashedPassword,
      },
    });

    // Create verification token
    const token = generateVerificationToken();
    await prisma.verificationToken.create({
      data: {
        identifier: normalizedEmail,
        token,
        expires: getTokenExpiry('EMAIL_VERIFICATION'),
        type: 'EMAIL_VERIFICATION',
      },
    });

    // Send verification email
    const emailResult = await sendVerificationEmail(normalizedEmail, token);

    if (!emailResult.success) {
      console.error('Failed to send verification email:', emailResult.error);
      return NextResponse.json(
        {
          message: 'Account created but verification email could not be sent.',
          userId: user.id,
          emailFailed: true,
        },
        { status: 201 }
      );
    }

    return NextResponse.json(
      {
        message: 'Account created successfully. Please check your email.',
        userId: user.id,
      },
      { status: 201 }
    );
  } catch (error) {
    console.error('Registration error:', error);
    return NextResponse.json(
      { error: 'An error occurred during registration' },
      { status: 500 }
    );
  }
}
```

### Login Flow

1. **User submits**: email, password, rememberMe (optional)
2. **Rate limit check**: 5 requests per minute
3. **Validate input**: Zod schema validation
4. **Normalize email**: Convert to lowercase
5. **Find user**: Query database for email
6. **Verify password**: bcrypt.compare with stored hash
7. **Check email verified**: Ensure user verified email
8. **Create session**: NextAuth session with user data
9. **Return success**: Redirect to dashboard

**Credentials Provider Pattern** (`lib/auth.config.ts`):
```typescript
import Credentials from 'next-auth/providers/credentials';
import { loginSchema } from '@/lib/validations/auth';
import { verifyPassword } from '@/lib/auth/password';

export default {
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        // Validate input
        const validated = loginSchema.safeParse(credentials);
        if (!validated.success) {
          throw new Error('Invalid credentials');
        }

        const { email, password } = validated.data;
        const normalizedEmail = email.toLowerCase();

        // Find user
        const user = await prisma.user.findUnique({
          where: { email: normalizedEmail },
        });

        if (!user || !user.password) {
          throw new Error('Invalid credentials');
        }

        // Verify password
        const isValid = await verifyPassword(password, user.password);
        if (!isValid) {
          throw new Error('Invalid credentials');
        }

        // Check email verified
        if (!user.emailVerified) {
          throw new Error('Please verify your email before logging in');
        }

        return {
          id: user.id,
          name: user.name,
          email: user.email,
          emailVerified: user.emailVerified,
        };
      },
    }),
  ],
};
```

### Email Verification Flow

1. **User clicks link**: From verification email with token parameter
2. **Rate limit check**: 5 requests per minute
3. **Validate token**: Check token exists and not expired
4. **Update user**: Set `emailVerified` to current timestamp
5. **Delete token**: Remove used token from database
6. **Return success**: Show success message, allow login

### Password Reset Flow

1. **User requests reset**: Submits email address
2. **Rate limit check**: 3 requests per minute
3. **Find user**: Query database for email
4. **Generate token**: 32-byte random hex string
5. **Create reset token**: Store in VerificationToken table with 1-hour expiry
6. **Send email**: Password reset link via Resend
7. **User clicks link**: Token in URL parameter
8. **User submits new password**: With token from URL
9. **Validate token**: Check exists and not expired
10. **Hash new password**: bcrypt with 12 salt rounds
11. **Update user**: Replace old password hash
12. **Delete token**: Remove used token
13. **Invalidate sessions**: Force re-login
14. **Return success**: Redirect to login

## Email Service Integration

### Resend API Configuration

**Environment Variables**:
```env
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxx
EMAIL_FROM=noreply@posterns.lv
```

**Email Sending Pattern** (`lib/email/index.ts`):
```typescript
import { Resend } from 'resend';

const resend = new Resend(process.env.RESEND_API_KEY);

export async function sendVerificationEmail(
  email: string,
  token: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const verificationUrl = `${process.env.NEXTAUTH_URL}/verify-email?token=${token}`;

    await resend.emails.send({
      from: process.env.EMAIL_FROM!,
      to: email,
      subject: 'Verify your email address',
      html: `
        <p>Please verify your email address by clicking the link below:</p>
        <a href="${verificationUrl}">Verify Email</a>
        <p>This link will expire in 24 hours.</p>
      `,
    });

    return { success: true };
  } catch (error) {
    console.error('Email send error:', error);
    return { success: false, error: String(error) };
  }
}
```

## Session Management

### NextAuth.js v5 Session Configuration

**Auth Configuration** (`lib/auth.ts`):
```typescript
import NextAuth from 'next-auth';
import authConfig from './auth.config';

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  session: {
    strategy: 'jwt',
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.emailVerified = user.emailVerified;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string;
        session.user.emailVerified = token.emailVerified as Date | null;
      }
      return session;
    },
  },
});
```

**Session Access Patterns**:

**Server Components**:
```typescript
import { auth } from '@/lib/auth';

export default async function Page() {
  const session = await auth();
  if (!session?.user) {
    redirect('/login');
  }

  return <div>Welcome {session.user.name}</div>;
}
```

**API Routes**:
```typescript
import { auth } from '@/lib/auth';

export async function GET(request: Request) {
  const session = await auth();
  if (!session?.user?.id) {
    return new Response('Unauthorized', { status: 401 });
  }

  // User is authenticated
  const userId = session.user.id;
  // ... handle request
}
```

**Client Components**:
```typescript
'use client';
import { useSession } from 'next-auth/react';

export function UserProfile() {
  const { data: session, status } = useSession();

  if (status === 'loading') {
    return <div>Loading...</div>;
  }

  if (!session?.user) {
    return <div>Not logged in</div>;
  }

  return <div>Hello {session.user.name}</div>;
}
```

## Security Best Practices

### Input Validation

**Always use Zod schemas**:
```typescript
import { z } from 'zod';

// Validate ALL user inputs
const validated = schema.safeParse(userInput);
if (!validated.success) {
  return error response;
}
// Use validated.data (never use userInput directly)
```

### SQL Injection Prevention

**Use Prisma parameterization** (never raw SQL unless absolutely necessary):
```typescript
// Good - Prisma handles parameterization
const user = await prisma.user.findUnique({
  where: { email: userEmail },
});

// Bad - Vulnerable to SQL injection
const user = await prisma.$queryRaw`
  SELECT * FROM User WHERE email = ${userEmail}
`;
```

### XSS Prevention

**React auto-escapes by default**, but:
- Never use `dangerouslySetInnerHTML` with user input
- Validate all inputs with Zod
- Sanitize before storing in database

### CSRF Protection

**NextAuth.js provides built-in CSRF protection**:
- CSRF tokens automatically included in forms
- State-changing operations use POST/PUT/DELETE (never GET)
- Verify origin header in API routes

### Timing Attacks

**Use constant-time comparisons for sensitive operations**:
```typescript
// Good - bcrypt.compare is constant-time
const isValid = await bcrypt.compare(password, hashedPassword);

// Good - crypto.timingSafeEqual for token comparison
import crypto from 'crypto';

function compareTokens(a: string, b: string): boolean {
  const bufferA = Buffer.from(a, 'hex');
  const bufferB = Buffer.from(b, 'hex');

  if (bufferA.length !== bufferB.length) {
    return false;
  }

  return crypto.timingSafeEqual(bufferA, bufferB);
}
```

### Error Messages

**Don't reveal if email exists**:
```typescript
// Good - Generic message
if (!user || !isPasswordValid) {
  throw new Error('Invalid credentials');
}

// Bad - Reveals email existence
if (!user) {
  throw new Error('Email not found');
}
if (!isPasswordValid) {
  throw new Error('Wrong password');
}
```

## Testing Authentication

### Manual Testing Checklist

- [ ] Register new user with valid data
- [ ] Try registering with existing email (should fail)
- [ ] Try registering with weak password (should fail)
- [ ] Verify email verification link works
- [ ] Try logging in before email verification (should fail)
- [ ] Login with correct credentials
- [ ] Login with incorrect password (should fail)
- [ ] Test rate limiting (make 10 rapid requests)
- [ ] Request password reset
- [ ] Reset password with valid token
- [ ] Try reusing password reset token (should fail)
- [ ] Try using expired token (should fail after 1 hour)
- [ ] Test "remember me" functionality
- [ ] Test session expiry
- [ ] Test logout functionality

### Security Audit Checklist

- [ ] Passwords are hashed with bcrypt (12 rounds minimum)
- [ ] Tokens are generated with crypto.randomBytes (32 bytes minimum)
- [ ] Rate limiting is applied to all auth endpoints
- [ ] Email addresses are normalized (lowercase)
- [ ] Email verification is required
- [ ] Password requirements are enforced
- [ ] Error messages don't reveal user existence
- [ ] No secrets in client-side code
- [ ] Environment variables used for sensitive config
- [ ] HTTPS enforced in production
- [ ] CSRF protection enabled
- [ ] Session timeout configured
- [ ] No SQL injection vulnerabilities
- [ ] XSS prevention implemented
- [ ] Proper input validation with Zod

## Common Vulnerabilities to Avoid

### 1. Weak Password Storage
❌ **Don't**:
- Store plaintext passwords
- Use weak hashing (MD5, SHA1)
- Use insufficient salt rounds

✅ **Do**:
- Use bcrypt with 12+ salt rounds
- Never store plaintext passwords

### 2. Insufficient Rate Limiting
❌ **Don't**:
- Allow unlimited login attempts
- Skip rate limiting on sensitive endpoints

✅ **Do**:
- Implement rate limiting on all auth endpoints
- Use IP-based identification
- Return 429 status for rate limit exceeded

### 3. Predictable Tokens
❌ **Don't**:
- Use sequential IDs for tokens
- Use timestamps or guessable patterns

✅ **Do**:
- Use crypto.randomBytes (32+ bytes)
- Use sufficient entropy

### 4. Missing Email Verification
❌ **Don't**:
- Allow unverified users full access
- Skip email verification

✅ **Do**:
- Require email verification before login
- Set reasonable token expiry (24 hours)

### 5. Exposing User Existence
❌ **Don't**:
- "Email not found"
- "Password incorrect"
- Different error messages for different failures

✅ **Do**:
- "Invalid credentials" for all login failures
- Same response time regardless of failure reason

## References

- [NextAuth.js v5 Documentation](https://next-auth.js.org/)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [bcrypt NPM Package](https://www.npmjs.com/package/bcryptjs)
- [Resend Documentation](https://resend.com/docs)
