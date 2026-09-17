---
name: workos
description: Expert for WorkOS integration, focusing on Enterprise SSO and Directory Sync. Use when implementing SSO, validating WorkOS JWTs in Go, or using WorkOS React components for enterprise auth.
---
# WorkOS Integration Skill

This skill provides patterns for WorkOS integration, focusing on Enterprise SSO, Auth Kit, and Organization management in a Go/React stack.

## Architectural Standards

### 1. Auth Kit & AuthLinks
*   **Auth Kit:** Use the hosted UI for login/Sign-up. Handle the redirect in Go using `workos.UserManagement.AuthenticateWithCode`.
*   **AuthLink:** Programmatically generate AuthLinks for enterprise customers to allow them to self-configure SSO.
*   **FIDC:** Handle "Fraud & Identity Identity Checks" by validating the `risk_score` in the user profile if enabled.

### 2. Organization Management (Multi-tenancy)
*   **Frictionless Onboarding:** Use "Domain Verification" to automatically assign users to Orgs.
*   **SCIM Directory Sync:** Implement Go handlers for WorkOS SCIM webhooks. Sync `directory_user.created` and `directory_user.deleted` events to your local DB.
*   **Admin Portal:** Link to the WorkOS Admin Portal for "Zero-code" SSO configuration by the customer.

### 3. Go Backend Security
*   **Webhook Validation:** **MANDATORY** to use `workos.ValidatePayload(payload, sig, secret)` for all webhooks.
*   **JWT Verification:** WorkOS uses public keys for JWT signature verification. Fetch and cache these keys periodically.
*   **Context Isolation:** Ensure every Go service call includes the `organization_id` extracted from the WorkOS session.

### 4. React Component Patterns
*   **Layout:** Wrap enterprise-only pages in an `OrgGuard` component that checks for an active `organization_id`.
*   **Management:** Build custom UI for "Organization Invitations" using the WorkOS API to invite users by email.

## Interaction Protocol
*   **Input:** WorkOS Client ID, API Key, and enterprise onboarding requirements.
*   **Output:** Go handlers for SSO/SCIM/AuthKit and React integration code.

**Tag**: Start your response with `[WORKOS-AUTH]`.
