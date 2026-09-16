# Cognitive Load Reference Guide

Detailed examples and principles for reducing cognitive load in software development.

## Working Memory Fundamentals

**Capacity**: ~4 chunks of information simultaneously
**Implication**: Code requiring >4 facts in working memory creates mental fatigue

**Types of Load:**
- **Intrinsic**: Inherent domain complexity (unavoidable)
- **Extraneous**: Poor design choices (reducible)

## Detailed Examples

### Complex Conditionals

**Problem:** Mental simulation required
```rust
// Requires holding 6+ boolean states mentally
if user.age > 18 &&
   (user.has_license || user.has_permit) &&
   (vehicle.is_available && !vehicle.is_reserved) &&
   rental_period.is_valid() {
    // approve rental
}
```

**Solution:** Externalize mental bookkeeping
```rust
let is_adult = user.age > 18;
let can_drive = user.has_license || user.has_permit;
let vehicle_ready = vehicle.is_available && !vehicle.is_reserved;
let valid_period = rental_period.is_valid();

if is_adult && can_drive && vehicle_ready && valid_period {
    // approve rental - now crystal clear
}
```

**Cognitive savings:** Reduced from 6 simultaneous facts to 4 named concepts

### Early Returns vs. Nested Flow

**Problem:** Accumulated context tracking
```rust
fn process_transaction(tx: Transaction) -> Result<Receipt> {
    if tx.is_valid() {
        if let Some(account) = tx.get_account() {
            if account.has_sufficient_funds(tx.amount) {
                if let Ok(receipt) = account.deduct(tx.amount) {
                    return Ok(receipt);
                } else {
                    return Err(Error::DeductionFailed);
                }
            } else {
                return Err(Error::InsufficientFunds);
            }
        } else {
            return Err(Error::AccountNotFound);
        }
    } else {
        return Err(Error::InvalidTransaction);
    }
}
```

**Cognitive load:** Must track 4 nested conditions simultaneously

**Solution:** Early returns focus on happy path
```rust
fn process_transaction(tx: Transaction) -> Result<Receipt> {
    if !tx.is_valid() {
        return Err(Error::InvalidTransaction);
    }

    let account = tx.get_account()
        .ok_or(Error::AccountNotFound)?;

    if !account.has_sufficient_funds(tx.amount) {
        return Err(Error::InsufficientFunds);
    }

    account.deduct(tx.amount)
        .map_err(|_| Error::DeductionFailed)
}
```

**Cognitive savings:** Linear flow, one precondition at a time

### Shallow vs. Deep Modules

**Shallow Module Problem:**
```rust
// Requires understanding 5+ components and their interactions
struct UserRepository;
struct UserValidator;
struct PasswordHasher;
struct SessionManager;
struct TokenGenerator;
struct EmailSender;

// Creating a user requires orchestrating all these pieces
let validator = UserValidator::new();
let hasher = PasswordHasher::with_bcrypt();
let repo = UserRepository::new(db_pool);
let session_mgr = SessionManager::new(redis);
let token_gen = TokenGenerator::with_jwt();
let email = EmailSender::new(smtp_config);

// Now coordinate them...
```

**Cognitive load:** 6 components, N² interaction possibilities

**Deep Module Solution:**
```rust
// Single entry point, complexity hidden
struct AuthService {
    // Internal components hidden from caller
}

impl AuthService {
    pub fn register_user(&self, email: &str, password: &str) -> Result<User> {
        // Internally handles:
        // - Validation
        // - Password hashing
        // - Database persistence
        // - Session creation
        // - Token generation
        // - Email confirmation

        // Caller only needs to understand one interface
    }
}
```

**Cognitive savings:** 1 interface vs. 6+ components to understand

### Abstraction Layer Explosion

**Problem:** Repository pattern for simple queries
```rust
// Domain layer
trait UserRepository {
    fn find_by_id(&self, id: UserId) -> Result<User>;
}

// Infrastructure layer
struct PostgresUserRepository {
    pool: PgPool,
}

impl UserRepository for PostgresUserRepository {
    fn find_by_id(&self, id: UserId) -> Result<User> {
        // Simple SQL query wrapped in 3 layers
    }
}

// Application layer
struct UserService {
    repo: Box<dyn UserRepository>,
}

// Usage requires understanding 3+ layers for single query
```

**Cognitive load:** 3 abstraction layers for `SELECT * FROM users WHERE id = ?`

**Pragmatic solution:**
```rust
// Direct query when abstraction provides no value
struct UserService {
    db: PgPool,
}

impl UserService {
    async fn get_user(&self, id: UserId) -> Result<User> {
        sqlx::query_as!(User, "SELECT * FROM users WHERE id = $1", id)
            .fetch_one(&self.db)
            .await
    }
}
```

**When to abstract:** Only when you have 2+ actual storage implementations (not theoretical)

### DRY Principle Misuse

**Problem:** Abstracting dissimilar code
```rust
// Order processing in e-commerce
fn process_order(order: Order) -> Result<()> {
    validate_inventory(order.items)?;
    charge_customer(order.payment)?;
    ship_items(order.items)?;
    Ok(())
}

// Return processing - seems similar!
fn process_return(return: Return) -> Result<()> {
    validate_items(return.items)?; // Different rules
    refund_customer(return.payment)?; // Different logic
    restock_items(return.items)?; // Different workflow
    Ok(())
}

// ❌ Premature abstraction attempts
fn process_transaction<T>(txn: T, validator: V, payment: P, items: I) -> Result<()> {
    // Now both order and return must fit this generic shape
    // Future changes require modifying shared abstraction
    // Tight coupling between unrelated domains
}
```

**Cognitive load:** Mental mapping of how Order and Return fit generic abstraction

**Solution:** Accept minor duplication
```rust
// Keep them separate - they serve different business purposes
// "A little copying is better than a little dependency"
```

**Rule:** Abstract after 3+ identical patterns emerge, not at 2

### Microservices Over-Granularity

**Problem:** Service per entity
```rust
// user-service: 200 LOC
// order-service: 180 LOC
// payment-service: 150 LOC
// notification-service: 100 LOC
// inventory-service: 220 LOC

// Simple "checkout" flow now requires:
// 1. user-service: validate user
// 2. inventory-service: check stock
// 3. order-service: create order
// 4. payment-service: charge card
// 5. inventory-service: decrement stock
// 6. notification-service: send confirmation

// Failure scenarios become combinatorial nightmares
```

**Cognitive load:** Must understand 6 services, network boundaries, failure modes, eventual consistency

**Solution:** Start with modules
```rust
// Single service with clear module boundaries
mod user;
mod inventory;
mod orders;
mod payments;
mod notifications;

// Checkout is local function calls
// Extract to services only when scaling demands it
// With clear bounded contexts already established
```

**Real case study:** 5 developers, 17 microservices → 10 months behind schedule

### Framework Magic

**Problem:** Hidden control flow
```rust
// Framework annotation magic
#[framework::route(GET, "/users/:id")]
#[framework::auth(Role::Admin)]
#[framework::cache(ttl = 300)]
#[framework::retry(attempts = 3)]
async fn get_user(ctx: FrameworkContext) -> FrameworkResponse {
    // What actually executes here?
    // Auth happens... somewhere?
    // Caching happens... somehow?
    // Retries happen... when?
    // Business logic intertwined with framework
}
```

**Cognitive load:** Must learn framework internals to understand execution flow

**Solution:** Explicit composition
```rust
// Business logic is pure, testable function
async fn get_user(user_id: UserId) -> Result<User> {
    // Just business logic, no framework coupling
}

// Framework adapter is explicit
async fn handle_get_user(req: Request) -> Response {
    let user_id = req.path_param("id")?;

    if !req.has_role(Role::Admin) {
        return Response::forbidden();
    }

    let cache_key = format!("user:{}", user_id);
    if let Some(cached) = cache.get(&cache_key).await {
        return Response::ok(cached);
    }

    let user = retry(3, || get_user(user_id)).await?;
    cache.set(&cache_key, &user, 300).await;

    Response::ok(user)
}
```

**Benefit:** New developers contribute to `get_user` on day 1, no framework knowledge required

### Self-Describing Values

**Problem:** Numeric codes require memorization
```rust
// HTTP status codes
match response.status {
    200 => { /* ok */ },
    401 => { /* unauthorized? */ },
    403 => { /* forbidden? */ },
    418 => { /* ??? */ },
    _ => { /* what else? */ }
}

// Custom error codes
if error_code == 1042 {
    // Must look up error code table
}
```

**Cognitive load:** Mental mapping of numbers to meanings

**Solution:** Self-describing types
```rust
enum AuthError {
    JwtExpired,
    InvalidSignature,
    MissingToken,
    InsufficientPermissions,
}

// Usage is self-documenting
match auth_result {
    Ok(user) => { /* proceed */ },
    Err(AuthError::JwtExpired) => { /* refresh token */ },
    Err(AuthError::InvalidSignature) => { /* security alert */ },
    // Clear without documentation lookup
}
```

## Measuring Cognitive Load

### Onboarding Test
**Metric:** Time for new developer to make first contribution

- **Excellent:** Hours (simple architecture)
- **Good:** 1-2 days
- **Warning:** 1+ weeks
- **Critical:** >40 minutes of continuous confusion

### Code Review Questions

Ask yourself:
1. How many facts must I hold in working memory?
2. Can I understand this without switching context?
3. Does this require memorizing mappings?
4. Would my explanation to a colleague exceed 2 minutes?
5. How many files must I open to understand one function?

**If >4 for any question:** Cognitive load reduction needed

## Refactoring Priorities

### High Impact, Low Effort
1. Extract intermediate variables from complex conditionals
2. Add early returns to reduce nesting
3. Rename cryptic variables/functions
4. Add "why" comments to non-obvious code

### Medium Impact
1. Merge shallow modules into deeper interfaces
2. Remove unused abstraction layers
3. Replace numeric codes with enums
4. Simplify error handling chains

### Strategic (High Effort)
1. Flatten microservices into modular monolith
2. Decouple business logic from framework
3. Remove inheritance hierarchies (prefer composition)
4. Redesign module boundaries

## Success Patterns

### Instagram Scale
- 14 million users
- 3 engineers
- Simple, focused architecture
- Deep modules with clear responsibilities

### Unix I/O
- 5 basic operations: open, close, read, write, seek
- Hides 100,000+ lines of complexity
- Decades of success as deep module design

### Raft Consensus
- Explicitly designed for understandability
- Chose simplicity over marginal performance gains
- Became widely adopted due to cognitive accessibility

## Anti-Pattern Recognition

### Naming Complexity
If the name is complex, the design probably is too:
- `MetricsProviderFactoryFactory`
- `AbstractSingletonProxyFactoryBean`
- `InternalLegacySynchronousMultithreadedTaskSchedulerImpl`

**Solution:** If you can't name it simply, redesign it

### Layered Architecture Warning Signs
- Changes require modifying 5+ files
- New feature touches all layers
- Debugging requires tracing through layers
- Layers exist "because architecture books say so"

**Solution:** Layers should emerge from necessity, not imposed preemptively

### SRP Misinterpretation
"Single Responsibility" ≠ "Does one small thing"

**Correct:** Responsible to one stakeholder/user
**Incorrect:** Creating 10 classes where 1 would suffice

### Premature Optimization
- "We might need to swap databases" → Repository pattern on day 1
- "We might scale" → Microservices for 1000 users
- "We might change" → Abstract everything

**Reality:** Most hypothetical flexibility is never needed
**Cost:** Cognitive overhead for theoretical benefit

## Project-Specific Integration

### Rust Best Practices (for this codebase)

```rust
// ✅ Use Result/Option explicitly (no exceptions)
fn parse_query(sql: &str) -> Result<Query, ParseError>

// ✅ Early returns with ?
let token = tokens.next()?;

// ✅ Pattern matching with clear arms
match token {
    Token::Select => { /* clear branch */ },
    Token::Insert => { /* clear branch */ },
    _ => return Err(ParseError::UnexpectedToken),
}

// ✅ Named intermediate results
let has_where_clause = tokens.peek() == Some(&Token::Where);
let has_group_by = tokens.contains(&Token::GroupBy);

if has_where_clause && !has_group_by {
    // Logic is self-documenting
}
```

### Cargo Workspace Guidelines

- Keep module boundaries clear (one crate = one responsibility)
- Prefer deep crates (rich internal complexity, simple public API)
- Don't create crates for hypothetical reuse
- Workspace dependencies prevent version conflicts (cognitive win)

## Remember

**Core principle:** Optimize for reading, not writing

Code is read 10x more than written. An extra 2 minutes writing clearer code saves 20 minutes across future readings.

**Cognitive budget:** You have ~4 chunks. Spend them on domain complexity, not accidental complexity.

**Validation:** If a newcomer can't contribute within 1-2 days, simplify your architecture.