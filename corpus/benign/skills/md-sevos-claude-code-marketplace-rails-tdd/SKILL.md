---
name: rails-tdd
description: TDD workflow for Rails applications. Use when implementing features or fixing bugs. Provides Red-Green cycle with test decision framework.
---

# Rails TDD Workflow

## Overview

This skill provides development workflows for Ruby on Rails applications. It defines methodologies for different types of engineering work.

## Workflows

### Implementation Workflow (TDD Red-Green)

When implementing features or fixing bugs, follow the Test-Driven Development cycle.

#### RED Phase

Write failing tests FIRST:
- Use fixtures for test data (check `test/fixtures/` for existing patterns)
- Refer to rails-basecamp-engineer skill references for test patterns
- Run `bin/ci` to confirm tests fail for the RIGHT reason
- Do NOT proceed until you have a failing test

#### GREEN Phase

Write the MINIMAL code to make tests pass:
- Refer to rails-basecamp-engineer skill references for implementation patterns
- Run `bin/ci` - do NOT proceed until all tests pass
- Avoid over-engineering; implement only what's needed for the test

#### Error Handling

If `bin/ci` fails:
- Read the error output carefully
- Fix the failing tests or implementation
- Do NOT proceed to the next phase until CI is green
- If stuck, explain the issue and ask for guidance

If you discover additional work needed:
- Note the discovery for the user
- Continue with current task unless blocking

#### Completion Criteria

- All tests pass (`bin/ci` or `bin/rails test`)
- Implementation is minimal and focused
- Code follows patterns from rails-basecamp-engineer references

## Test Decision Framework

### Rails Test Types

| Directory | Base Class | Purpose |
|-----------|------------|---------|
| `test/models/` | `ActiveSupport::TestCase` | Model logic, validations, scopes |
| `test/controllers/` | `ActionDispatch::IntegrationTest` | Controller actions, HTTP responses |
| `test/integration/` | `ActionDispatch::IntegrationTest` | Multi-controller workflows |
| `test/system/` | `ActionDispatch::SystemTestCase` | Full browser tests (Capybara) |
| `test/helpers/` | `ActionView::TestCase` | View helper methods |
| `test/mailers/` | `ActionMailer::TestCase` | Email generation and content |
| `test/jobs/` | `ActiveJob::TestCase` | Background job behavior |
| `test/channels/` | `ActionCable::Channel::TestCase` | WebSocket connections |

### What to Test Where

**Model tests** (`test/models/`):
- Custom methods (e.g., `User#full_name`, `Order#total`)
- POROs and service objects
- Complex scopes with business logic
- State machines and transitions
- Callbacks with side effects

**Controller tests** (`test/controllers/`):
- HTTP response codes and redirects
- Authentication/authorization checks
- Parameter handling and strong params
- Flash messages and session state

**System tests** (`test/system/`) - use sparingly:
- Critical user paths (signup, checkout, login)
- JavaScript-dependent features
- Multi-step workflows requiring browser state

**Mailer tests** (`test/mailers/`):
- Email subject, recipients, and headers
- Email body content and dynamic values
- Attachments
- Conditional delivery logic

**Job tests** (`test/jobs/`):
- Job arguments and enqueueing
- Job execution logic
- Retries and error handling
- Side effects (database changes, API calls)

**Skip tests for** (covered implicitly):
- `validates :name, presence: true` - framework behavior
- Simple `has_many`/`belongs_to` - framework behavior
- Delegations - framework behavior

### Decision Matrix

| Change Type | Models | Controllers | System | Mailers | Jobs |
|-------------|--------|-------------|--------|---------|------|
| Custom model method | ✓ | - | - | - | - |
| PORO/service object | ✓ | - | - | - | - |
| Controller action | - | ✓ | - | - | - |
| API endpoint | - | ✓ | - | - | - |
| User-facing feature | - | ✓ | critical paths | - | - |
| JS-dependent feature | - | - | ✓ | - | - |
| Multi-step workflow | - | - | ✓ | - | - |
| Background job | - | - | - | - | ✓ |
| Mailer | - | - | - | ✓ | - |
| Bug fix | where bug lives | + regression | - | - | - |
