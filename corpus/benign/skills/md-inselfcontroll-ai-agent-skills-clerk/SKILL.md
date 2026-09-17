---
name: clerk
description: Expert for Clerk authentication integration. Use when setting up Clerk in React, implementing Clerk Go middleware for session validation, or managing Clerk user profiles.
---
# Clerk Integration Skill

This skill provides patterns for integrating Clerk's fully managed authentication service into a Go/React stack.

## Architectural Standards

### 1. Go Backend Integration (Session & Hydration)
*   **Middleware:** Use `clerk.WithSession()` to inject the user's Clerk ID and metadata into the Go context.
*   **Hydration:** Implement a `SyncUser` helper that pulls the full user object from Clerk's API using the `clerk-sdk-go` and updates your local DB if needed.
*   **Metadata:** Use `privateMetadata` for sensitive backend-only fields (e.g., Stripe Customer ID) and `publicMetadata` for UI-facing attributes (e.g., User Role).

### 2. Reliable Webhooks (Svix)
*   **Verification:** Always verify Clerk webhooks using the `svix` package to prevent spoofing.
*   **Idempotency:** Webhooks can be delivered multiple times. Ensure your DB handlers are idempotent using a `webhook_id` table or check-before-update logic.
*   **Events:** Prioritize handling `user.created`, `user.updated`, and `session.ended`.

### 3. React Frontend Excellence
*   **Custom UI:** While Clerk components are great, use `useClerk()` and `useAuth()` to build custom branded login flows for higher-tier enterprise feel.
*   **TanStack Query:**
    ```typescript
    const { getToken } = useAuth();
    const { data } = useQuery({
      queryKey: ['resource'],
      queryFn: async () => {
        const token = await getToken(); // Automatically handles refresh
        return fetchResource(token);
      }
    });
    ```
*   **Control Components:** Use `<SignedIn>`, `<SignedOut>`, and `<Protect>` for declarative access control.

### 4. Security Patterns
*   **SSO:** Enable Enterprise SSO (SAML) in the Clerk dashboard. Map provider groups to internal roles.
*   **Rate Limiting:** Implement rate limiting in the Go backend based on the Clerk `user_id`.

## Interaction Protocol
*   **Input:** Clerk Publishable Key, Secret Key, and user synchronization requirements.
*   **Output:** Go middleware/webhook handlers and React Clerk component integration.

**Tag**: Start your response with `[CLERK-AUTH]`.
