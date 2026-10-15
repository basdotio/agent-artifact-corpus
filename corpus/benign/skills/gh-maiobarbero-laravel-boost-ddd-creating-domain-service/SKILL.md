---
name: creating-domain-service
description: Create or refactor business calculations and rules spanning multiple domain objects when no single entity or value object naturally owns the behavior. Use when assessing a growing service class.
---

# Domain services

First look for a model or Value Object that naturally owns the behavior. Create `App\Domain\<Capability>\Services` only when a cohesive business operation has no such owner.

For example, `OrderCancellationFee` may calculate a fee using an order and a cancellation policy. It computes a business result; `CancelOrder` authorizes, coordinates, saves, and handles follow-up work.

Avoid generic `OrderService`, `UserService`, or `PaymentService` containers. Do not extract a service merely because a method is long or used twice.

Domain services must not depend on Application, Infrastructure, or delivery code. If a business calculation genuinely needs an external capability, define its contract under `App\Domain\<Capability>\Contracts`, implement it in Infrastructure, and bind it in a Laravel service provider. Do not hide an adapter lookup behind a facade or container call.

Use domain exceptions for rejected rules. Leave persistence coordination and transactions to Application. Direct collaboration with models in other capabilities is allowed within the same bounded context.
