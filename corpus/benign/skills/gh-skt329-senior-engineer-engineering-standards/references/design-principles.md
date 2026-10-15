# Design principles

Each principle comes with what it means in plain words, a short example, and when it is the wrong tool. Principles are means to readable, changeable code, not goals.

## Single responsibility
A module, class, or function should have one reason to change.

```python
# Before: one function validates, saves, and sends email. A change to any of them touches it.
def register(data): ...

# After: each part changes on its own.
class RegistrationService:
    def __init__(self, users: UserRepository, notifier: Notifier) -> None:
        self._users = users
        self._notifier = notifier

    def register(self, data: RegisterRequest) -> User:
        user = self._users.add(User.from_request(data))
        self._notifier.send_welcome(user.email)
        return user
```

## Open for extension, closed for modification
Add behavior by adding code, not by growing an if/else chain that every change must edit.

```python
PROVIDERS: dict[str, PaymentProvider] = {"stripe": StripeProvider(), "razorpay": RazorpayProvider()}

def charge(provider_name: str, amount: Money) -> Receipt:
    return PROVIDERS[provider_name].charge(amount)
```

## Liskov substitution
A subclass must keep its parent's promises: same inputs accepted, same kind of result, no surprise exceptions. If a subclass has to refuse a parent method, inheritance is the wrong relationship.

## Interface segregation
Keep interfaces small. A caller that only reads users should depend on a reader, not on a repository with twenty methods.

## Dependency inversion
Business logic depends on abstractions, and concrete implementations are passed in. This is what makes services testable without a database.

```python
from typing import Protocol

class UserRepository(Protocol):
    def get(self, user_id: int) -> User | None: ...
    def add(self, user: User) -> User: ...
```

In FastAPI, inject the implementation with `Depends`; on Android, with Hilt.

## Keep it simple, and you are not going to need it
Build what the task needs today. Every option, hook, or abstraction added "for later" has to be read, tested, and maintained now.

## Don't repeat yourself, with care
Duplicate once; abstract on the third occurrence, when you can see what actually varies. A wrong abstraction costs more than two similar functions.

## Composition over inheritance
Combine small objects that each do one thing instead of building deep class hierarchies. Inheritance is fine for true "is a" relationships with shared behavior, and rarely more than one level deep.

## Dependency direction
API and infrastructure depend on services, services depend on the domain, and the domain depends on nothing. A service that imports FastAPI's Request, or a model that imports an HTTP client, points the wrong way.

## Boundaries
Convert data at the edges: request schemas to domain objects at the API layer, ORM rows to domain objects in repositories. Never pass ORM objects or raw request dictionaries deep into the code.

## Fail fast
Validate inputs where they enter the system and raise a clear error immediately, instead of letting bad data travel and fail somewhere confusing.

## When these are the wrong lens
- Small scripts and one-off tools: straight-line code with a few clear functions is easier to read than classes and interfaces.
- Data pipelines: chains of pure transform functions beat object hierarchies.
- UI components: composition of components, props down and events up, and hooks for shared logic.
- Prototypes: get it working, then decide with the user whether it becomes production code.

In these cases the goal is the same (readable, testable, easy to change) and the techniques differ.
