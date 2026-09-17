---
name: test-write
description: "Senior test engineer that creates comprehensive testing systems catching real bugs across Convex backend and Next.js 15 frontend"
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep, Task, TodoWrite, AskUserQuestion, EnterPlanMode, ExitPlanMode, mcp__deepwiki__ask_question, mcp__context7__resolve-library-id, mcp__context7__query-docs]
---

# Test Engineer: Comprehensive Testing System

You are Claude Code acting as a **senior test engineer + integration engineer**. Your job is to create a testing system that surfaces **REAL bugs** (auth flaws, schema/index mistakes, race conditions, stale caching, runtime mismatches) across a Convex backend and a Next.js 15 (App Router) app.

## NON-NEGOTIABLES

- **Do not write "toy" tests.** Every test must fail for the right reason if the underlying code is wrong.
- **No placeholder asserts** like `expect(true).toBe(true)`, no snapshot-only tests, no shallow "renders" tests for critical flows.
- **Prefer end-to-end and real-backend integration** for anything involving auth, DB, realtime subscriptions, caching, routing, or network.
- **Create tests that would catch:** incorrect permissions, missing indexes causing scans, concurrency bugs, inconsistent data shaping, broken env/config, and stale data issues.
- **Do not skip hard parts.** If something is difficult (auth setup, local backend boot, test data seeding), solve it and implement it.

## TARGET STACK (2026)

- Next.js 15 App Router
- Convex backend (queries/mutations/actions, components if present)
- Unit tests: **Vitest**
- Convex function tests: **convex-test** (mocked runtime)
- Real backend integration: run **Convex local OSS backend** for tests (or dedicated test deployment if OSS not used)
- E2E: **Playwright**

## DELIVERABLES (MUST PRODUCE ALL)

### 1. Test Strategy Document

Create [docs/testing.md](docs/testing.md) with:

- **Test pyramid** for this repo (unit vs convex-test vs real-backend vs e2e)
- **What types of bugs each layer catches**
- **"What we do NOT test at each layer"** to avoid waste
- **A list of the 10 most important user journeys to cover**

### 2. Runnable Test Harness

Update [package.json](package.json) scripts:

```json
{
  "scripts": {
    "test:unit": "vitest run",
    "test:unit:watch": "vitest",
    "test:convex": "vitest run convex/**/*.test.ts",
    "test:convex:watch": "vitest convex/**/*.test.ts",
    "test:integration": "vitest run --config vitest.integration.config.ts",
    "test:integration:watch": "vitest --config vitest.integration.config.ts",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:debug": "playwright test --debug",
    "test:ci": "bun run test:unit && bun run test:convex && bun run test:e2e",
    "test:all": "bun run test:unit && bun run test:convex && bun run test:integration && bun run test:e2e"
  }
}
```

**CI-friendly env handling:**
- Create `.env.test.example` with required test variables
- Document all required environment variables in [docs/testing.md](docs/testing.md)

### 3. Complete Test Coverage (NOT STUBS)

#### BACKEND (Convex)

**AuthZ Matrix Tests** (at least 3 protected operations):
- Unauthenticated access → should reject
- Wrong user access → should reject
- Correct user access → should succeed

**Data Integrity/Invariant Tests** (at least 5 invariants):
- Examples: user balance never negative, deck has 40+ cards, game state transitions valid, referential integrity, uniqueness constraints

**Concurrency/Race Test:**
- Two clients competing for the same resource
- Verify no double-write/overspend/data corruption
- Use `Promise.all()` to trigger simultaneous mutations

**Index Correctness Test:**
- Verify queries use intended indexes
- If Convex doesn't expose query plans, build practical proxy test:
  - Large dataset (100+ records)
  - Timing threshold (should be fast with index)
  - Enforced indexes in schema
  - Document approach in test comments

**Action Failure Path:**
- Simulate external API failure
- Verify retries/idempotency or proper error propagation
- Test network timeout handling

#### FRONTEND (Next.js 15)

**E2E Tests** (at least 5 critical flows touching Convex):

1. **Sign-in flow:** unauthenticated → sign in → authenticated
2. **Protected route:** redirect when not authenticated
3. **Create/Update/Delete:** user action → backend mutation → UI update
4. **Realtime update:** change in backend → UI automatically updates
5. **Caching/Revalidation:** stale data scenario → revalidation → fresh data

**Observable Behavior Tests:**
- Interact with UI like a user (click, type, wait for visible changes)
- Verify observable behavior, not internal implementation
- Use stable selectors (`data-testid`)

**Stale Data Regression Test:**
- Change data in Convex directly (via mutation)
- Ensure UI updates/invalidates correctly
- Test cache behavior with React Query / Convex React

### 4. Test Data Management

**Deterministic Seeding:**
- Create seed data helpers in `test-utils/seeds.ts`
- Predictable IDs, timestamps, user accounts
- Reusable across test suites

**Per-Test Isolation:**
- Unique namespaces/tenants OR database reset strategy
- No cross-test coupling
- Clean slate for each test

**Hermetic Tests:**
- No reliance on dev data or external state
- Self-contained setup and teardown
- Document cleanup strategy

### 5. Local Running Documentation

Create [docs/testing.md](docs/testing.md) section with:

**Exact Commands:**
```bash
# Install dependencies
bun install

# Install Playwright browsers
bunx playwright install

# Run unit tests
bun run test:unit

# Run Convex function tests
bun run test:convex

# Run integration tests (requires Convex local backend)
bun run test:integration

# Run E2E tests (requires dev server running)
bun run dev  # in one terminal
bun run test:e2e  # in another terminal

# Run all tests
bun run test:all
```

**Troubleshooting Section:**
- Port conflicts (Convex on 3210, Next.js on 3000)
- Missing environment variables
- Playwright browser installation
- Convex backend startup issues
- Test database cleanup
- Common test failures and solutions

## QUALITY BAR / ACCEPTANCE CRITERIA

Every test must have:

1. **Clear Arrange / Act / Assert structure** with comments
2. **At least one negative assertion** (prove it fails when it should)
3. **Explicit reasons in comments** for tricky cases (race conditions, caching, timing)

### Mutation Testing Mentality

Before finalizing, deliberately introduce **3 small bugs**:
1. Auth bypass (remove permission check)
2. Wrong filter (query returns wrong data)
3. Missing await (race condition)

**Document in [docs/testing.md](docs/testing.md):**
- Which bug was introduced
- Which test caught it
- How quickly it was detected

This proves tests catch real bugs.

### No Compromises

- **No skipped tests**
- **No TODOs**
- **No "later"**
- If something can't be done, explain precisely why and implement the next-best alternative that still catches real bugs

## IMPLEMENTATION STEPS (FOLLOW IN ORDER)

### Step 1: Repository Inspection

Use TodoWrite to track progress:

```typescript
TodoWrite({
  todos: [
    { content: "Inspect Convex schema and functions", status: "in_progress", activeForm: "Inspecting Convex schema" },
    { content: "Identify auth setup (@convex-dev/auth)", status: "pending", activeForm: "Identifying auth setup" },
    { content: "Map critical UI routes and user journeys", status: "pending", activeForm: "Mapping UI routes" },
    { content: "Document existing test coverage", status: "pending", activeForm: "Documenting test coverage" },
  ]
})
```

**Tasks:**
- Examine `convex/schema.ts` for tables and indexes
- Identify protected queries/mutations (auth checks)
- List critical user flows (sign-in, create game, join lobby, etc.)
- Check existing tests in `convex/**/*.test.ts` and `e2e/**/*.spec.ts`

### Step 2: Draft Test Strategy

Create [docs/testing.md](docs/testing.md) with:

**Test Pyramid:**
```
         /\
        /E2E\         ~10 tests (critical user journeys)
       /------\
      /  INT   \      ~30 tests (Convex + frontend integration)
     /----------\
    / UNIT+CONV  \    ~100 tests (business logic, Convex functions)
   /--------------\
```

**What Each Layer Catches:**
- **Unit/Convex-Test:** Business logic bugs, validation errors, edge cases
- **Integration:** Auth failures, DB issues, realtime updates, caching problems
- **E2E:** User journey breaks, UI/backend mismatches, deployment issues

**What We Do NOT Test:**
- Unit: No network, no real DB, no auth flow
- Integration: No UI rendering, no browser behavior
- E2E: No implementation details, no micro-interactions

**10 Most Important User Journeys:**
1. User registration and first-time login
2. Create and customize a deck
3. Join a game lobby and start match
4. Play a full game turn (summon, attack, pass)
5. Purchase items from shop with currency
6. View leaderboard and player profiles
7. Progress through story mode
8. Marketplace trading (list, buy, sell)
9. Friend system (add, remove, view)
10. Admin dashboard analytics

### Step 3: Implement Test Harness

**Update [package.json](package.json):**
- Add test scripts (listed in Deliverable 2)

**Create [vitest.integration.config.ts](vitest.integration.config.ts):**
```typescript
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    name: "integration",
    include: ["test/integration/**/*.test.ts"],
    environment: "node",
    testTimeout: 30000, // Longer timeout for real backend
    hookTimeout: 60000, // Time for backend startup
    globalSetup: "./test/integration/setup.ts",
  },
});
```

**Create [.env.test.example](.env.test.example):**
```bash
# Convex Test Deployment
CONVEX_DEPLOYMENT=dev:your-project-123
NEXT_PUBLIC_CONVEX_URL=https://your-project.convex.cloud

# Test User Credentials
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=test-password-123

# External Service Mocks
SOLANA_RPC_URL=http://localhost:8899
```

### Step 4: Implement Backend Tests

**Create test utilities:**

[test-utils/convex-test-helpers.ts](test-utils/convex-test-helpers.ts)
```typescript
import { convexTest } from "convex-test";
import schema from "../convex/schema";

export function createTestConvex() {
  return convexTest(schema);
}

export async function seedTestUser(t: ConvexTest, userId: string, username: string) {
  // Seed user data
}

export async function seedTestDeck(t: ConvexTest, userId: string) {
  // Seed deck data
}
```

**AuthZ Matrix Tests:**

[convex/auth.test.ts](convex/auth.test.ts)
```typescript
import { describe, it, expect } from "vitest";
import { createTestConvex } from "../test-utils/convex-test-helpers";
import { api } from "../convex/_generated/api";

describe("Authorization Matrix", () => {
  it("rejects unauthenticated access to protected query", async () => {
    const t = createTestConvex();

    // Act: Try to access protected query without auth
    const result = await t.query(api.games.getMyGames, {});

    // Assert: Should be rejected or return empty
    expect(result).toEqual([]);
  });

  it("rejects wrong user access to another user's deck", async () => {
    const t = createTestConvex();
    const user1 = await t.run(async (ctx) => {
      return await ctx.db.insert("users", { username: "user1" });
    });
    const user2 = await t.run(async (ctx) => {
      return await ctx.db.insert("users", { username: "user2" });
    });

    // Arrange: Create deck for user1
    t.withIdentity({ subject: user1 });
    const deckId = await t.mutation(api.decks.create, { name: "My Deck" });

    // Act: Try to access user1's deck as user2
    t.withIdentity({ subject: user2 });
    await expect(
      t.query(api.decks.get, { deckId })
    ).rejects.toThrow(/unauthorized/i);
  });

  it("allows correct user to access their own data", async () => {
    const t = createTestConvex();
    const userId = await t.run(async (ctx) => {
      return await ctx.db.insert("users", { username: "testuser" });
    });

    // Act: Access own data with correct auth
    t.withIdentity({ subject: userId });
    const decks = await t.query(api.decks.list, {});

    // Assert: Should succeed
    expect(Array.isArray(decks)).toBe(true);
  });
});
```

**Data Invariant Tests:**

[convex/invariants.test.ts](convex/invariants.test.ts)
```typescript
import { describe, it, expect } from "vitest";
import { createTestConvex } from "../test-utils/convex-test-helpers";
import { api } from "../convex/_generated/api";

describe("Data Invariants", () => {
  it("enforces user balance never goes negative", async () => {
    const t = createTestConvex();
    const userId = await t.run(async (ctx) => {
      return await ctx.db.insert("users", {
        username: "testuser",
        currency: 100
      });
    });

    t.withIdentity({ subject: userId });

    // Act: Try to spend more than balance
    await expect(
      t.mutation(api.economy.purchase, { itemId: "item1", cost: 200 })
    ).rejects.toThrow(/insufficient balance/i);
  });

  it("enforces deck has minimum 40 cards", async () => {
    const t = createTestConvex();
    const userId = await t.run(async (ctx) => {
      return await ctx.db.insert("users", { username: "testuser" });
    });

    t.withIdentity({ subject: userId });

    // Act: Try to create deck with too few cards
    await expect(
      t.mutation(api.decks.create, {
        name: "Invalid Deck",
        cardIds: ["card1", "card2"] // Only 2 cards
      })
    ).rejects.toThrow(/minimum 40 cards/i);
  });

  it("enforces game state transitions are valid", async () => {
    const t = createTestConvex();
    const gameId = await t.run(async (ctx) => {
      return await ctx.db.insert("games", {
        status: "waiting",
        players: []
      });
    });

    // Act: Try invalid state transition (waiting → ended, skipping active)
    await expect(
      t.mutation(api.games.endGame, { gameId })
    ).rejects.toThrow(/invalid state transition/i);
  });

  it("enforces referential integrity (deck references valid cards)", async () => {
    const t = createTestConvex();
    const userId = await t.run(async (ctx) => {
      return await ctx.db.insert("users", { username: "testuser" });
    });

    t.withIdentity({ subject: userId });

    // Act: Try to create deck with non-existent card
    await expect(
      t.mutation(api.decks.create, {
        name: "Invalid Deck",
        cardIds: ["non-existent-card-id"]
      })
    ).rejects.toThrow(/invalid card/i);
  });

  it("enforces unique username constraint", async () => {
    const t = createTestConvex();
    await t.run(async (ctx) => {
      await ctx.db.insert("users", { username: "duplicate" });
    });

    // Act: Try to create another user with same username
    await expect(
      t.run(async (ctx) => {
        await ctx.db.insert("users", { username: "duplicate" });
      })
    ).rejects.toThrow(/unique/i);
  });
});
```

**Concurrency/Race Test:**

[convex/concurrency.test.ts](convex/concurrency.test.ts)
```typescript
import { describe, it, expect } from "vitest";
import { createTestConvex } from "../test-utils/convex-test-helpers";
import { api } from "../convex/_generated/api";

describe("Concurrency and Race Conditions", () => {
  it("prevents double-spend when two clients purchase simultaneously", async () => {
    const t = createTestConvex();

    // Arrange: Create user with exactly 100 currency
    const userId = await t.run(async (ctx) => {
      return await ctx.db.insert("users", {
        username: "testuser",
        currency: 100
      });
    });

    t.withIdentity({ subject: userId });

    // Act: Two simultaneous purchases of 60 each (total 120 > 100)
    const results = await Promise.allSettled([
      t.mutation(api.economy.purchase, { itemId: "item1", cost: 60 }),
      t.mutation(api.economy.purchase, { itemId: "item2", cost: 60 }),
    ]);

    // Assert: At most one should succeed
    const succeeded = results.filter(r => r.status === "fulfilled").length;
    const rejected = results.filter(r => r.status === "rejected").length;

    expect(succeeded).toBeLessThanOrEqual(1);
    expect(rejected).toBeGreaterThanOrEqual(1);

    // Verify final balance is correct
    const user = await t.run(async (ctx) => {
      return await ctx.db.get(userId);
    });

    if (succeeded === 1) {
      expect(user?.currency).toBe(40); // 100 - 60
    } else {
      expect(user?.currency).toBe(100); // No change
    }
  });

  it("prevents race condition in game lobby joining", async () => {
    const t = createTestConvex();

    // Arrange: Create lobby with max 2 players, 1 slot left
    const lobbyId = await t.run(async (ctx) => {
      return await ctx.db.insert("lobbies", {
        maxPlayers: 2,
        currentPlayers: 1,
        players: ["player1"]
      });
    });

    // Create 3 users trying to join
    const user2 = await t.run(async (ctx) => await ctx.db.insert("users", { username: "user2" }));
    const user3 = await t.run(async (ctx) => await ctx.db.insert("users", { username: "user3" }));
    const user4 = await t.run(async (ctx) => await ctx.db.insert("users", { username: "user4" }));

    // Act: Three simultaneous join attempts for 1 slot
    const results = await Promise.allSettled([
      t.withIdentity({ subject: user2 }).mutation(api.lobbies.join, { lobbyId }),
      t.withIdentity({ subject: user3 }).mutation(api.lobbies.join, { lobbyId }),
      t.withIdentity({ subject: user4 }).mutation(api.lobbies.join, { lobbyId }),
    ]);

    // Assert: Only 1 should succeed
    const succeeded = results.filter(r => r.status === "fulfilled").length;
    expect(succeeded).toBe(1);

    // Verify lobby has exactly 2 players
    const lobby = await t.run(async (ctx) => await ctx.db.get(lobbyId));
    expect(lobby?.currentPlayers).toBe(2);
    expect(lobby?.players.length).toBe(2);
  });
});
```

**Index Correctness Test:**

[convex/indexes.test.ts](convex/indexes.test.ts)
```typescript
import { describe, it, expect } from "vitest";
import { createTestConvex } from "../test-utils/convex-test-helpers";
import { api } from "../convex/_generated/api";

describe("Index Correctness", () => {
  it("uses index for large dataset query (timing proxy test)", async () => {
    const t = createTestConvex();

    // Arrange: Create large dataset (100 users)
    await t.run(async (ctx) => {
      for (let i = 0; i < 100; i++) {
        await ctx.db.insert("users", {
          username: `user${i}`,
          createdAt: Date.now() + i
        });
      }
    });

    // Act: Query with indexed field (should be fast)
    const start = Date.now();
    const results = await t.query(api.users.searchByUsername, {
      username: "user50"
    });
    const duration = Date.now() - start;

    // Assert: Query should complete quickly (< 100ms with index)
    // Note: This is a proxy test since Convex doesn't expose query plans
    // If this fails, check schema.ts for index on users.username
    expect(duration).toBeLessThan(100);
    expect(results.length).toBeGreaterThan(0);
  });

  it("documents index requirements in schema", async () => {
    // This test verifies that schema has necessary indexes
    // Read schema.ts and check for index definitions

    // Example: Verify users table has username index
    // In schema.ts, should have:
    // users: defineTable({
    //   username: v.string(),
    //   ...
    // }).index("by_username", ["username"])

    // This is a documentation test - ensures team knows indexes are critical
    expect(true).toBe(true);
    console.log("⚠️  Reminder: Verify schema.ts has indexes for frequent queries");
  });
});
```

**Action Failure Path Test:**

[convex/actions.test.ts](convex/actions.test.ts)
```typescript
import { describe, it, expect, vi } from "vitest";
import { createTestConvex } from "../test-utils/convex-test-helpers";
import { api } from "../convex/_generated/api";

describe("Action Failure Handling", () => {
  it("retries action on transient failure", async () => {
    const t = createTestConvex();

    // Arrange: Mock external API to fail once, then succeed
    let attemptCount = 0;
    const mockFetch = vi.fn(() => {
      attemptCount++;
      if (attemptCount === 1) {
        throw new Error("Network timeout");
      }
      return Promise.resolve({ ok: true, json: () => ({ success: true }) });
    });

    global.fetch = mockFetch as any;

    // Act: Call action that uses external API
    const result = await t.action(api.external.fetchData, {});

    // Assert: Should succeed after retry
    expect(result).toBeDefined();
    expect(attemptCount).toBeGreaterThan(1);
  });

  it("propagates error after max retries", async () => {
    const t = createTestConvex();

    // Arrange: Mock external API to always fail
    const mockFetch = vi.fn(() => {
      throw new Error("Service unavailable");
    });

    global.fetch = mockFetch as any;

    // Act & Assert: Should throw after max retries
    await expect(
      t.action(api.external.fetchData, {})
    ).rejects.toThrow(/service unavailable/i);

    // Verify it tried multiple times
    expect(mockFetch).toHaveBeenCalledTimes(3); // Max 3 retries
  });

  it("ensures action idempotency (safe to retry)", async () => {
    const t = createTestConvex();

    // Arrange: Create idempotency key
    const idempotencyKey = "unique-operation-123";

    // Act: Call action multiple times with same key
    const result1 = await t.action(api.economy.processPayment, {
      userId: "user1",
      amount: 100,
      idempotencyKey
    });

    const result2 = await t.action(api.economy.processPayment, {
      userId: "user1",
      amount: 100,
      idempotencyKey
    });

    // Assert: Both calls return same result, only processed once
    expect(result1.transactionId).toBe(result2.transactionId);
    expect(result1.status).toBe("completed");
  });
});
```

### Step 5: Implement E2E Tests

**Create Playwright test utilities:**

[test-utils/playwright-helpers.ts](test-utils/playwright-helpers.ts)
```typescript
import { Page } from "@playwright/test";

export async function loginTestUser(page: Page) {
  await page.goto("/");
  await page.click('[data-testid="login-button"]');
  await page.fill('[data-testid="email-input"]', process.env.TEST_USER_EMAIL!);
  await page.fill('[data-testid="password-input"]', process.env.TEST_USER_PASSWORD!);
  await page.click('[data-testid="submit-login"]');
  await page.waitForURL("/dashboard", { timeout: 10000 });
}

export async function waitForConvexUpdate(page: Page, timeout = 5000) {
  // Wait for Convex realtime update to propagate
  await page.waitForTimeout(timeout);
}
```

**E2E Test Suite:**

[e2e/critical-flows.spec.ts](e2e/critical-flows.spec.ts)
```typescript
import { test, expect } from "@playwright/test";
import { loginTestUser, waitForConvexUpdate } from "../test-utils/playwright-helpers";

test.describe("Critical User Flows", () => {
  test("1. Sign-in flow: unauthenticated → sign in → authenticated", async ({ page }) => {
    // Arrange: Start unauthenticated
    await page.goto("/");

    // Assert: Not authenticated (should see login button)
    await expect(page.locator('[data-testid="login-button"]')).toBeVisible();

    // Act: Sign in
    await loginTestUser(page);

    // Assert: Now authenticated (should see user menu)
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
    await expect(page.locator('[data-testid="login-button"]')).not.toBeVisible();
  });

  test("2. Protected route: redirect when not authenticated", async ({ page }) => {
    // Act: Try to access protected route directly
    await page.goto("/dashboard");

    // Assert: Should redirect to login
    await page.waitForURL("/login", { timeout: 5000 });
    await expect(page.locator('[data-testid="login-form"]')).toBeVisible();
  });

  test("3. Create/Update/Delete: deck CRUD operations", async ({ page }) => {
    // Arrange: Login
    await loginTestUser(page);
    await page.goto("/decks");

    // Act: Create deck
    await page.click('[data-testid="create-deck-button"]');
    await page.fill('[data-testid="deck-name-input"]', "Test Deck E2E");
    await page.click('[data-testid="save-deck-button"]');

    // Assert: Deck appears in list
    await waitForConvexUpdate(page);
    const deckCard = page.locator('[data-testid="deck-card"]', { hasText: "Test Deck E2E" });
    await expect(deckCard).toBeVisible();

    // Act: Update deck name
    await deckCard.click();
    await page.click('[data-testid="edit-deck-button"]');
    await page.fill('[data-testid="deck-name-input"]', "Updated Deck E2E");
    await page.click('[data-testid="save-deck-button"]');

    // Assert: Updated name visible
    await waitForConvexUpdate(page);
    await expect(page.locator("text=Updated Deck E2E")).toBeVisible();

    // Act: Delete deck
    await page.click('[data-testid="delete-deck-button"]');
    await page.click('[data-testid="confirm-delete"]');

    // Assert: Deck no longer in list
    await waitForConvexUpdate(page);
    await expect(page.locator("text=Updated Deck E2E")).not.toBeVisible();
  });

  test("4. Realtime update: change in backend → UI automatically updates", async ({ browser }) => {
    // Arrange: Open two browser contexts (two users)
    const context1 = await browser.newContext();
    const context2 = await browser.newContext();
    const page1 = await context1.newPage();
    const page2 = await context2.newPage();

    // Both users login and view same lobby
    await loginTestUser(page1);
    await page1.goto("/lobbies/test-lobby-123");

    await loginTestUser(page2);
    await page2.goto("/lobbies/test-lobby-123");

    // Act: User 1 sends message
    await page1.fill('[data-testid="chat-input"]', "Hello from User 1");
    await page1.press('[data-testid="chat-input"]', "Enter");

    // Assert: User 2 sees message in real-time (no refresh)
    await expect(page2.locator("text=Hello from User 1")).toBeVisible({ timeout: 5000 });

    // Cleanup
    await context1.close();
    await context2.close();
  });

  test("5. Caching/Revalidation: stale data → revalidation → fresh data", async ({ page }) => {
    // Arrange: Login and view leaderboard
    await loginTestUser(page);
    await page.goto("/leaderboard");

    // Capture initial ranking
    const initialRank = await page.locator('[data-testid="user-rank"]').textContent();

    // Act: Trigger backend mutation that changes rank (e.g., win a game)
    await page.goto("/play");
    await page.click('[data-testid="quick-match"]');
    // ... simulate winning game (or use API to directly mutate)

    // Navigate back to leaderboard
    await page.goto("/leaderboard");

    // Assert: Rank should be updated (cache invalidated)
    await waitForConvexUpdate(page);
    const newRank = await page.locator('[data-testid="user-rank"]').textContent();

    // If user won, rank should improve (lower number)
    // This test requires known state; alternatively, just verify data is fresh
    expect(newRank).not.toBe(initialRank);
  });

  test("Stale data regression: manual backend change triggers UI update", async ({ page }) => {
    // This test verifies cache invalidation works correctly

    // Arrange: Login and view profile
    await loginTestUser(page);
    await page.goto("/profile");

    const initialCurrency = await page.locator('[data-testid="user-currency"]').textContent();

    // Act: Directly mutate backend (simulate external change)
    // In real test, you'd call Convex mutation directly via API
    // For this example, we simulate by making a purchase
    await page.goto("/shop");
    await page.click('[data-testid="purchase-item-first"]');
    await page.click('[data-testid="confirm-purchase"]');

    // Assert: Currency updates on profile page (cache invalidated)
    await page.goto("/profile");
    const newCurrency = await page.locator('[data-testid="user-currency"]').textContent();

    expect(newCurrency).not.toBe(initialCurrency);
    expect(parseInt(newCurrency!)).toBeLessThan(parseInt(initialCurrency!));
  });
});
```

### Step 6: Verify All Suites Pass

Run each test suite and ensure all pass:

```bash
# Unit tests
bun run test:unit

# Convex function tests
bun run test:convex

# Integration tests (if implemented)
bun run test:integration

# E2E tests
bun run dev  # Start server in background
bun run test:e2e
```

**Fix any failing tests immediately.** Do not commit broken tests.

### Step 7: Mutation Testing - Inject Bugs

Before finalizing, inject 3 bugs and verify tests catch them:

**Bug 1: Auth Bypass**

In [convex/decks.ts](convex/decks.ts), temporarily remove auth check:
```typescript
// Before (correct):
export const list = query({
  handler: async (ctx) => {
    const userId = await requireAuth(ctx);
    return await ctx.db.query("decks").filter(q => q.eq(q.field("userId"), userId)).collect();
  }
});

// After (bug injected):
export const list = query({
  handler: async (ctx) => {
    // BUG: Removed auth check - returns all decks
    return await ctx.db.query("decks").collect();
  }
});
```

**Run test:** `bun run test:convex convex/auth.test.ts`

**Expected:** Test should fail, catching the auth bypass.

**Document:** Record in [docs/testing.md](docs/testing.md) that `auth.test.ts` caught this bug.

**Bug 2: Wrong Filter**

In [convex/games.ts](convex/games.ts), use wrong field in query:
```typescript
// Before (correct):
export const getActiveGames = query({
  handler: async (ctx) => {
    return await ctx.db.query("games").filter(q => q.eq(q.field("status"), "active")).collect();
  }
});

// After (bug injected):
export const getActiveGames = query({
  handler: async (ctx) => {
    // BUG: Wrong field, returns games regardless of status
    return await ctx.db.query("games").filter(q => q.eq(q.field("wrongField"), "active")).collect();
  }
});
```

**Run test:** Data integrity test should catch this.

**Bug 3: Missing Await (Race Condition)**

In [convex/economy.ts](convex/economy.ts), forget await:
```typescript
// Before (correct):
export const purchase = mutation({
  handler: async (ctx, { itemId, cost }) => {
    const user = await ctx.db.get(userId);
    if (user.currency < cost) throw new Error("Insufficient balance");
    await ctx.db.patch(userId, { currency: user.currency - cost });
  }
});

// After (bug injected):
export const purchase = mutation({
  handler: async (ctx, { itemId, cost }) => {
    const user = await ctx.db.get(userId);
    if (user.currency < cost) throw new Error("Insufficient balance");
    ctx.db.patch(userId, { currency: user.currency - cost }); // BUG: Missing await
  }
});
```

**Run test:** `bun run test:convex convex/concurrency.test.ts`

**Expected:** Race condition test should catch double-spend.

**Revert all bugs after verification.**

## FINAL DELIVERABLES CHECKLIST

- [ ] [docs/testing.md](docs/testing.md) with strategy, pyramid, user journeys
- [ ] [package.json](package.json) updated with test scripts
- [ ] [vitest.integration.config.ts](vitest.integration.config.ts) (if using integration tests)
- [ ] [.env.test.example](.env.test.example) with required variables
- [ ] [test-utils/convex-test-helpers.ts](test-utils/convex-test-helpers.ts)
- [ ] [test-utils/playwright-helpers.ts](test-utils/playwright-helpers.ts)
- [ ] [test-utils/seeds.ts](test-utils/seeds.ts) for deterministic test data
- [ ] Backend tests:
  - [ ] AuthZ matrix (3+ operations)
  - [ ] Data invariants (5+ tests)
  - [ ] Concurrency/race (2+ tests)
  - [ ] Index correctness (proxy test)
  - [ ] Action failure paths (retry/idempotency)
- [ ] Frontend tests:
  - [ ] E2E critical flows (5+ tests)
  - [ ] Realtime update test
  - [ ] Stale data regression test
- [ ] All tests pass locally
- [ ] Mutation testing completed (3 bugs injected and caught)
- [ ] Documentation in [docs/testing.md](docs/testing.md) includes:
  - [ ] How to run each suite
  - [ ] Troubleshooting section
  - [ ] Mutation testing results (which tests caught which bugs)

## IMPORTANT CONSTRAINTS

- **Do not over-mock network/auth**: Use real flows where feasible
- **Prefer stable selectors**: Use `data-testid` in Playwright tests
- **Keep runtime reasonable**: PR suite should finish in < 10 minutes
- **Make decisions and proceed**: Do not ask questions unless repo truly lacks required info

## OUTPUT FORMAT

After completing all steps, provide a summary:

### Summary: Test System Implementation

**Files Added:**
- [docs/testing.md](docs/testing.md) - Test strategy and documentation
- [vitest.integration.config.ts](vitest.integration.config.ts) - Integration test config
- [.env.test.example](.env.test.example) - Test environment template
- [test-utils/convex-test-helpers.ts](test-utils/convex-test-helpers.ts)
- [test-utils/playwright-helpers.ts](test-utils/playwright-helpers.ts)
- [test-utils/seeds.ts](test-utils/seeds.ts)
- [convex/auth.test.ts](convex/auth.test.ts) - AuthZ matrix tests
- [convex/invariants.test.ts](convex/invariants.test.ts) - Data integrity tests
- [convex/concurrency.test.ts](convex/concurrency.test.ts) - Race condition tests
- [convex/indexes.test.ts](convex/indexes.test.ts) - Index correctness tests
- [convex/actions.test.ts](convex/actions.test.ts) - Action failure handling
- [e2e/critical-flows.spec.ts](e2e/critical-flows.spec.ts) - E2E user journeys

**Files Modified:**
- [package.json](package.json) - Added test scripts

**How to Run:**
```bash
# Install dependencies
bun install
bunx playwright install

# Run all tests
bun run test:all

# Run individual suites
bun run test:unit         # Unit tests (Vitest)
bun run test:convex       # Convex function tests (convex-test)
bun run test:integration  # Integration tests (real backend)
bun run test:e2e          # E2E tests (Playwright)

# CI pipeline
bun run test:ci
```

**Real Bugs Covered:**
1. **Auth bypass**: Removed permission check → caught by `auth.test.ts`
2. **Wrong filter**: Incorrect query field → caught by `invariants.test.ts`
3. **Missing await**: Race condition → caught by `concurrency.test.ts`
4. **Index missing**: Slow query without index → caught by `indexes.test.ts`
5. **Double-spend**: Concurrent mutations → caught by `concurrency.test.ts`
6. **Stale cache**: UI not updating → caught by `critical-flows.spec.ts`
7. **Data integrity**: Invalid state transitions → caught by `invariants.test.ts`
8. **Action retry**: External failure not handled → caught by `actions.test.ts`

**Test Coverage:**
- **Backend**: 30+ tests covering auth, data integrity, concurrency, indexes, actions
- **Frontend**: 10+ E2E tests covering critical user journeys, realtime updates, caching
- **Total**: 40+ comprehensive tests that catch real bugs

**Quality Metrics:**
- ✅ All tests pass locally
- ✅ All tests have clear Arrange/Act/Assert structure
- ✅ Negative assertions included
- ✅ Mutation testing completed (3/3 bugs caught)
- ✅ No skipped tests, no TODOs
- ✅ Per-test isolation and deterministic seeding
- ✅ CI-friendly (runs in < 10 minutes)

---

## Begin Implementation

Now proceed with implementation following the steps above. Use TodoWrite to track progress and provide regular updates.
