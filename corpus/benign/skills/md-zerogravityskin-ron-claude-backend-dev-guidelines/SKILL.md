---
name: backend-dev-guidelines
description: Comprehensive backend development guide for Node.js/Express/TypeScript microservices. Use when creating routes, controllers, services, repositories, middleware, or working with Express APIs, Prisma database access, Sentry error tracking, Zod validation, unifiedConfig, dependency injection, or async patterns. Covers layered architecture (routes → controllers → services → repositories), BaseController pattern, error handling, performance monitoring, testing strategies, and migration from legacy patterns.
---

# Backend Development Guidelines

## Purpose

Establish consistency and best practices for the Quantum Skincare backend API using modern Node.js/Express/TypeScript patterns with Clerk authentication, Prisma ORM, and structured error handling.

## When to Use This Skill

Automatically activates when working on:
- Creating or modifying routes, endpoints, APIs
- Building controllers and services
- Implementing middleware (auth, validation, error handling, rate limiting)
- Database operations with Prisma and DAOs
- Error handling with custom error classes
- Input validation with Zod
- Clerk authentication integration
- Backend testing and refactoring

---

## Quick Start

### New Backend Feature Checklist

- [ ] **Route**: Clean definition in `routes/`, delegate to controller
- [ ] **Controller**: Request handlers with asyncHandler wrapper
- [ ] **Service**: Business logic (if needed for complex operations)
- [ ] **DAO**: Database access via `@quantum/data-access`
- [ ] **Validation**: Zod schema from `@quantum/shared-validation`
- [ ] **Error Handling**: Use custom error classes (ValidationError, NotFoundError, etc.)
- [ ] **Auth**: Apply `requireAuthClerk` middleware for protected routes
- [ ] **Tests**: Unit + integration tests with Jest
- [ ] **Logging**: Use Pino logger with structured logging

### Key Architecture Components

- [ ] Express app setup in `app.ts`
- [ ] Middleware chain (helmet, cors, rate limiting, auth)
- [ ] Clerk authentication with `requireAuthClerk`
- [ ] Centralized error handling via `errorHandler`
- [ ] Structured logging with Pino
- [ ] Versioned API routes under `/v1`

---

## Architecture Overview

### Layered Architecture

```
HTTP Request
    ↓
Routes (routing only)
    ↓
Controllers (request handling)
    ↓
Services (business logic)
    ↓
Repositories (data access)
    ↓
Database (Prisma)
```

**Key Principle:** Each layer has ONE responsibility.

See [architecture-overview.md](architecture-overview.md) for complete details.

---

## Directory Structure

```
apps/backend/src/
├── controllers/         # Request handlers (e.g., users.controller.ts)
│   └── quota/          # Feature-specific controllers
├── services/            # Business logic organized by domain
│   ├── clerk/          # Clerk user synchronization
│   ├── consent/        # Consent management
│   ├── geo/            # IP geolocation
│   ├── quota/          # Quota management
│   ├── scans/          # Scan processing
│   ├── skin-analysis/  # Skin analysis orchestration
│   ├── storage/        # S3 storage
│   └── treatment/      # Treatment recommendations
├── routes/              # Route definitions (e.g., users.ts, skin-analysis.ts)
├── middleware/          # Express middleware (auth, validation, error handling)
├── types/               # Backend-specific TypeScript types
├── utils/               # Utilities (logger, errors)
├── __tests__/           # Tests (unit + integration)
├── app.ts               # Express app setup + middleware chain
└── main.ts              # Server entry point + secret initialization
```

**Naming Conventions:**
- Controllers: `kebab-case.controller.ts` - `users.controller.ts`
- Services: `kebab-case.service.ts` - `user-deletion.service.ts`
- Routes: `kebab-case.ts` - `skin-analysis.ts`
- Middleware: `kebab-case.ts` - `auth-clerk.ts`

---

## Core Principles (8 Key Rules)

### 1. Routes Only Route, Controllers Handle Requests

```typescript
// ❌ NEVER: Business logic in routes
router.post('/submit', async (req, res) => {
    // 200 lines of logic
});

// ✅ ALWAYS: Delegate to controller function
router.post('/submit', asyncHandler(submitController));
```

### 2. All Controllers Use asyncHandler

```typescript
// Wraps async functions to catch errors automatically
export const getUser = asyncHandler(async (req: Request, res: Response) => {
    const user = await getUserById(req.params.id);
    res.json(createSuccessResponse(user, 'User retrieved'));
});
```

### 3. Use Custom Error Classes

```typescript
import { ValidationError, NotFoundError, UnauthorizedError } from '../utils/errors.js';

// Throw specific errors - errorHandler will format response
if (!user) {
    throw new NotFoundError('User');
}

if (!isValid) {
    throw new ValidationError('Invalid email format');
}
```

### 4. Environment Variables Directly (No Wrapper Config)

```typescript
// ✅ Access environment variables directly
const port = process.env.PORT || 5000;
const clerkSecretKey = process.env.CLERK_SECRET_KEY;

// Validate critical env vars at startup (see main.ts)
if (!process.env.CLERK_SECRET_KEY) {
    logger.fatal('Missing CLERK_SECRET_KEY');
    process.exit(1);
}
```

### 5. Validate All Input with Zod

```typescript
import { validateRequest } from '../middleware/validation.js';
import { consentSchemas } from '@quantum/shared-validation';

// Use validateRequest middleware
export const acceptConsent: RequestHandler[] = [
    validateRequest({ body: consentSchemas.acceptConsent }),
    asyncHandler(async (req, res) => {
        // req.body is now type-safe and validated
    })
];
```

### 6. Use DAOs from @quantum/data-access

```typescript
import { getUserByClerkId, upsertUserFromClerk } from '@quantum/data-access';

// ✅ Use DAOs for database access
const user = await getUserByClerkId(clerkUserId);

// ❌ Don't use Prisma directly in controllers
const user = await prisma.users.findUnique(...);
```

### 7. Protect Routes with requireAuthClerk

```typescript
import { requireAuthClerk } from '../middleware/auth-clerk.js';

// Apply auth middleware to protected routes
router.get('/me', requireAuthClerk, getUserController);

// User payload available via getUserPayload(req)
const user = getUserPayload(req); // { id, email, tier, consent }
```

### 8. Structured Logging with Pino

```typescript
import { logger } from '../utils/logger.js';

// Include requestId and relevant context
logger.info({
    userId: user.id,
    requestId: req.requestId,
    event: 'consent.accepted'
}, 'Consent accepted successfully');

logger.error({ error, userId: user.id }, 'Failed to process request');
```

---

## Common Imports

```typescript
// Express
import express, { Request, Response, NextFunction, Router, RequestHandler } from 'express';

// Error handling
import { asyncHandler } from '../middleware/error-handler.js';
import {
    ValidationError,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    ConflictError,
    QuotaExceededError
} from '../utils/errors.js';

// Response helpers
import { createSuccessResponse, createErrorResponse } from '../types/api-responses.js';

// Validation
import { validateRequest } from '../middleware/validation.js';
import { z } from 'zod';

// Database (via DAOs)
import {
    getUserByClerkId,
    upsertUserFromClerk,
    createConsentAudit,
    getPersonalInfo
} from '@quantum/data-access';

// Shared validation schemas
import { consentSchemas } from '@quantum/shared-validation';

// Shared types
import type { UserApp, ConsentProfile } from '@quantum/shared-types';

// Auth
import { requireAuthClerk, requireClerkToken } from '../middleware/auth-clerk.js';
import { getUserPayload } from '../types/express-auth.js';
import { clerkClient } from '@clerk/express';

// Logging
import { logger } from '../utils/logger.js';
```

---

## Quick Reference

### HTTP Status Codes

| Code | Use Case |
|------|----------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 500 | Server Error |

### Example Services

**apps/backend/src/** - Quantum Skincare Backend API
- Routes: `routes/users.ts`, `routes/skin-analysis.ts`
- Controllers: `controllers/users.controller.ts`
- Services: `services/consent/`, `services/skin-analysis/`
- Middleware: `middleware/auth-clerk.ts`, `middleware/validation.ts`

---

## Anti-Patterns to Avoid

❌ Business logic in routes
❌ Direct Prisma access in controllers (use DAOs)
❌ Missing error handling or asyncHandler wrapper
❌ No input validation
❌ console.log instead of logger
❌ Not using custom error classes
❌ Forgetting requireAuthClerk on protected routes
❌ Accessing req.user without getUserPayload helper

---

## Navigation Guide

| Need to... | Read this |
|------------|-----------|
| Understand architecture | [architecture-overview.md](architecture-overview.md) |
| Create routes/controllers | [routing-and-controllers.md](routing-and-controllers.md) |
| Organize business logic | [services-and-repositories.md](services-and-repositories.md) |
| Validate input | [validation-patterns.md](validation-patterns.md) |
| Add error tracking | [sentry-and-monitoring.md](sentry-and-monitoring.md) |
| Create middleware | [middleware-guide.md](middleware-guide.md) |
| Database access | [database-patterns.md](database-patterns.md) |
| Manage config | [configuration.md](configuration.md) |
| Handle async/errors | [async-and-errors.md](async-and-errors.md) |
| Write tests | [testing-guide.md](testing-guide.md) |
| See examples | [complete-examples.md](complete-examples.md) |

---

## Resource Files

### [architecture-overview.md](architecture-overview.md)
Layered architecture, request lifecycle, separation of concerns

### [routing-and-controllers.md](routing-and-controllers.md)
Route definitions, BaseController, error handling, examples

### [services-and-repositories.md](services-and-repositories.md)
Service patterns, DI, repository pattern, caching

### [validation-patterns.md](validation-patterns.md)
Zod schemas, validation, DTO pattern

### [sentry-and-monitoring.md](sentry-and-monitoring.md)
Sentry init, error capture, performance monitoring

### [middleware-guide.md](middleware-guide.md)
Auth, audit, error boundaries, AsyncLocalStorage

### [database-patterns.md](database-patterns.md)
PrismaService, repositories, transactions, optimization

### [configuration.md](configuration.md)
UnifiedConfig, environment configs, secrets

### [async-and-errors.md](async-and-errors.md)
Async patterns, custom errors, asyncErrorWrapper

### [testing-guide.md](testing-guide.md)
Unit/integration tests, mocking, coverage

### [complete-examples.md](complete-examples.md)
Full examples, refactoring guide

---

## Related Skills

- **frontend-dev-guidelines** - React/TypeScript patterns for Next.js frontend
- **route-tester** - Testing authenticated routes with Clerk JWT
- **skill-developer** - Meta-skill for creating and managing skills

---

**Skill Status**: COMPLETE ✅
**Line Count**: < 500 ✅
**Progressive Disclosure**: 11 resource files ✅
