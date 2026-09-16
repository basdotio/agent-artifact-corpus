# ADVANCED SECURITY PATTERNS & HARDENING

## 1. AUTHENTICATION FLOW SECURITY

### Secure JWT Implementation

```typescript
// lib/security/jwt-secure.ts
import jwt from 'jsonwebtoken';
import { randomBytes } from 'crypto';

/**
 * Generate JWT with security hardening
 */
export function generateSecureJWT(
    payload: object,
    expiresIn: string = '15m'
): string {
    return jwt.sign(payload, process.env.JWT_SECRET!, {
        algorithm: 'HS256',
        expiresIn,
        issuer: 'your-app.com',
        audience: 'your-app-users',
        jwtid: randomBytes(16).toString('hex'),
        notBefore: '0',
    });
}

/**
 * Verify JWT with all security checks
 */
export function verifySecureJWT(token: string): object | null {
    try {
        return jwt.verify(token, process.env.JWT_SECRET!, {
            algorithms: ['HS256'],
            issuer: 'your-app.com',
            audience: 'your-app-users',
        });
    } catch (error) {
        if (error instanceof jwt.TokenExpiredError) {
            console.error('Token expired');
        } else if (error instanceof jwt.JsonWebTokenError) {
            console.error('Invalid token');
        }
        return null;
    }
}

/**
 * Secure token rotation strategy
 */
export async function rotateTokens(userId: string) {
    const accessToken = generateSecureJWT(
        { userId, type: 'access' },
        '15m'
    );
    const refreshToken = generateSecureJWT(
        { userId, type: 'refresh' },
        '7d'
    );

    // Store refresh token hash in database
    const tokenHash = await hashToken(refreshToken);
    await saveRefreshToken(userId, tokenHash);

    return { accessToken, refreshToken };
}
```

### Secure Password Management

```typescript
// lib/security/password.ts
import { hash, compare } from 'bcryptjs';
import { scrypt, randomBytes } from 'crypto';
import { promisify } from 'util';

const scryptAsync = promisify(scrypt);

/**
 * Hash password with bcrypt (12 rounds = secure)
 */
export async function hashPassword(password: string): Promise<string> {
    // Validate password strength
    validatePasswordStrength(password);
    return hash(password, 12);
}

/**
 * Verify password
 */
export async function verifyPassword(
    password: string,
    hash: string
): Promise<boolean> {
    return compare(password, hash);
}

/**
 * Validate password strength
 */
export function validatePasswordStrength(password: string): boolean {
    if (password.length < 12) {
        throw new Error('Password must be at least 12 characters');
    }
    if (!password.match(/[A-Z]/)) {
        throw new Error('Must contain uppercase letter');
    }
    if (!password.match(/[a-z]/)) {
        throw new Error('Must contain lowercase letter');
    }
    if (!password.match(/[0-9]/)) {
        throw new Error('Must contain digit');
    }
    if (!password.match(/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/)) {
        throw new Error('Must contain special character');
    }
    return true;
}

/**
 * Generate secure password reset token
 */
export async function generatePasswordResetToken(): Promise<string> {
    const token = randomBytes(32).toString('hex');
    const hash = await scryptAsync(token, 'salt', 32);
    return hash.toString('hex');
}
```

## 2. DATA PRIVACY & ENCRYPTION

### Client-Side Encryption

```typescript
// lib/security/encryption.ts
/**
 * Encrypt sensitive data client-side
 * Uses Web Crypto API (native browser)
 */
export async function encryptData(
    data: string,
    passphrase: string
): Promise<string> {
    // Derive key from passphrase
    const encoder = new TextEncoder();
    const data_utf8 = encoder.encode(data);
    const passphrase_utf8 = encoder.encode(passphrase);

    const key = await crypto.subtle.importKey(
        'raw',
        passphrase_utf8,
        { name: 'PBKDF2' },
        false,
        ['deriveKey']
    );

    const derived = await crypto.subtle.deriveKey(
        {
            name: 'PBKDF2',
            salt: encoder.encode('salt'),
            iterations: 100000,
            hash: 'SHA-256',
        },
        key,
        { name: 'AES-GCM', length: 256 },
        false,
        ['encrypt']
    );

    const iv = crypto.getRandomValues(new Uint8Array(12));
    const encrypted = await crypto.subtle.encrypt(
        { name: 'AES-GCM', iv },
        derived,
        data_utf8
    );

    // Combine IV + encrypted data
    const combined = new Uint8Array(iv.length + encrypted.byteLength);
    combined.set(iv);
    combined.set(new Uint8Array(encrypted), iv.length);

    return btoa(String.fromCharCode(...combined));
}

/**
 * Decrypt sensitive data
 */
export async function decryptData(
    encrypted: string,
    passphrase: string
): Promise<string> {
    const encoder = new TextEncoder();
    const combined = new Uint8Array(
        atob(encrypted).split('').map((c) => c.charCodeAt(0))
    );

    const iv = combined.slice(0, 12);
    const data = combined.slice(12);

    const passphrase_utf8 = encoder.encode(passphrase);
    const key = await crypto.subtle.importKey(
        'raw',
        passphrase_utf8,
        { name: 'PBKDF2' },
        false,
        ['deriveKey']
    );

    const derived = await crypto.subtle.deriveKey(
        {
            name: 'PBKDF2',
            salt: encoder.encode('salt'),
            iterations: 100000,
            hash: 'SHA-256',
        },
        key,
        { name: 'AES-GCM', length: 256 },
        false,
        ['decrypt']
    );

    const decrypted = await crypto.subtle.decrypt(
        { name: 'AES-GCM', iv },
        derived,
        data
    );

    return new TextDecoder().decode(decrypted);
}
```

### PII Handling

```typescript
// lib/security/pii.ts
/**
 * Mask sensitive personal information
 */
export function maskSSN(ssn: string): string {
    return ssn.replace(/^(.{2})(.*)(.{2})$/, '$1****$3');
}

export function maskCreditCard(cc: string): string {
    return cc.replace(/(\d{4})(\d{4})(\d{4})/, '$1 **** **** ');
}

export function maskEmail(email: string): string {
    const [local, domain] = email.split('@');
    const masked = local
        .slice(0, 2)
        .padEnd(local.length, '*');
    return `${masked}@${domain}`;
}

/**
 * Audit trail for PII access
 */
export async function logPIIAccess(
    userId: string,
    dataType: string,
    action: string
) {
    await db.piiAuditLog.create({
        userId,
        dataType,
        action,
        timestamp: new Date(),
        ipAddress: getClientIP(),
        userAgent: getUserAgent(),
    });
}

/**
 * Data retention policy
 */
export async function retentionPolicy() {
    // Delete old audit logs
    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    
    await db.auditLog.deleteMany({
        where: { createdAt: { lt: thirtyDaysAgo } },
    });
}
```

## 3. SUPPLY CHAIN SECURITY

### Dependency Vulnerability Scanning

```json
{
    "scripts": {
        "audit": "npm audit --audit-level=moderate",
        "audit:fix": "npm audit fix",
        "security:check": "snyk test",
        "license:check": "npm-check-licenses",
        "outdated": "npm outdated"
    },
    "devDependencies": {
        "snyk": "^latest",
        "npm-check-licenses": "^latest",
        "dependabot": "^latest"
    }
}
```

### Package Lock & Integrity

```bash
#!/bin/bash
# security/check-integrity.sh

# Verify package lock
npm ci --verify-peer-deps

# Check for known vulnerabilities
npm audit --production

# Verify checksums
npm ls

# Check for outdated packages
npm outdated

# Generate SBOM (Software Bill of Materials)
cyclonedx-npm --output-file sbom.json
```

## 4. NETWORK & TRANSPORT SECURITY

### HTTPS Enforcement

```typescript
// middleware.ts - Next.js middleware
import { NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
    // Force HTTPS in production
    if (
        process.env.NODE_ENV === 'production' &&
        request.headers.get('x-forwarded-proto') !== 'https'
    ) {
        return NextResponse.redirect(
            `https://${request.headers.get('host')}${request.nextUrl.pathname}`,
            301
        );
    }

    // Add security headers
    const response = NextResponse.next();

    // HSTS - Force HTTPS for 1 year
    response.headers.set(
        'Strict-Transport-Security',
        'max-age=31536000; includeSubDomains; preload'
    );

    // Prevent MIME sniffing
    response.headers.set('X-Content-Type-Options', 'nosniff');

    // Clickjacking protection
    response.headers.set('X-Frame-Options', 'DENY');

    // XSS protection
    response.headers.set('X-XSS-Protection', '1; mode=block');

    // Referrer policy
    response.headers.set(
        'Referrer-Policy',
        'strict-origin-when-cross-origin'
    );

    // Permissions policy
    response.headers.set(
        'Permissions-Policy',
        'geolocation=(), microphone=(), camera=(), payment=()'
    );

    return response;
}

export const config = {
    matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
```

## 5. MONITORING & INCIDENT RESPONSE

### Security Event Logging

```typescript
// lib/security/logging.ts
/**
 * Log security events with PII redaction
 */
export async function logSecurityEvent(
    event: {
        type: string;
        severity: 'low' | 'medium' | 'high' | 'critical';
        description: string;
        userId?: string;
        ipAddress?: string;
        userAgent?: string;
        metadata?: Record<string, any>;
    }
) {
    // Redact sensitive data
    const redactedMetadata = redactPII(event.metadata || {});

    const log = {
        timestamp: new Date().toISOString(),
        type: event.type,
        severity: event.severity,
        description: event.description,
        userId: event.userId,
        ipAddress: event.ipAddress,
        userAgent: event.userAgent,
        metadata: redactedMetadata,
    };

    // Store in secure log service
    await storeSecurityLog(log);

    // Alert if critical
    if (event.severity === 'critical') {
        await alertSecurityTeam(log);
    }
}

function redactPII(obj: Record<string, any>): Record<string, any> {
    const sensitive = ['password', 'credit_card', 'ssn', 'email'];
    
    return Object.entries(obj).reduce((acc, [key, value]) => {
        if (sensitive.some(s => key.toLowerCase().includes(s))) {
            acc[key] = '***REDACTED***';
        } else if (typeof value === 'object') {
            acc[key] = redactPII(value);
        } else {
            acc[key] = value;
        }
        return acc;
    }, {} as Record<string, any>);
}
```

### Anomaly Detection

```typescript
// lib/security/anomaly-detection.ts
/**
 * Detect suspicious user behavior
 */
export async function detectAnomalies(userId: string) {
    const recentActivity = await getUserActivity(userId, 24); // Last 24 hours

    const checks = {
        unusualLocation: await checkUnusualLocation(userId),
        unusualTime: checkUnusualTime(recentActivity),
        frequentFailedLogins: checkFailedLogins(recentActivity),
        dataAccessAnomaly: await checkDataAccessPatterns(userId),
        suspiciousIPAddresses: await checkSuspiciousIPs(recentActivity),
    };

    const riskScore = calculateRiskScore(checks);

    if (riskScore > 0.7) {
        // Trigger MFA re-verification
        await requireMFAVerification(userId);
    }

    if (riskScore > 0.9) {
        // Lock account and notify user
        await lockAccount(userId);
        await notifyUser(userId, 'Suspicious activity detected');
    }

    return { checks, riskScore };
}
```

## 6. COMPLIANCE & GDPR

### Data Processing Agreement

```typescript
// lib/compliance/gdpr.ts
/**
 * GDPR: Right to be forgotten
 */
export async function deleteUserData(userId: string) {
    // Get all user data
    const user = await db.user.findUnique({ where: { id: userId } });

    // Delete personal data
    await db.user.delete({ where: { id: userId } });
    await db.userProfile.deleteMany({ where: { userId } });
    await db.userSessions.deleteMany({ where: { userId } });

    // Anonymize activity logs (keep for compliance)
    await db.auditLog.updateMany(
        { where: { userId } },
        { userId: 'ANONYMIZED' }
    );

    // Archive for retention period
    await archiveForRetention({
        userId,
        data: user,
        reason: 'GDPR deletion',
        retentionDays: 90,
    });
}

/**
 * GDPR: Data export
 */
export async function exportUserData(userId: string) {
    const data = {
        profile: await db.user.findUnique({ where: { id: userId } }),
        preferences: await db.userPreferences.findUnique({ where: { userId } }),
        activity: await db.auditLog.findMany({ where: { userId } }),
        connections: await db.connections.findMany({ where: { userId } }),
    };

    return {
        exportedAt: new Date().toISOString(),
        data,
    };
}

/**
 * GDPR: Consent management
 */
export async function manageConsent(
    userId: string,
    consentType: 'marketing' | 'analytics' | 'cookies'
) {
    await db.userConsent.upsert({
        where: { userId_consentType: { userId, consentType } },
        update: { givenAt: new Date() },
        create: { userId, consentType, givenAt: new Date() },
    });
}
```

---

This covers all advanced security aspects comprehensively!