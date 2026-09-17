---
name: spring-api-rules
description: Define controllers, services, repositories, entities, DTOs for Spring Boot REST API. Use when user mentions API, endpoint, controller, service, repository, entity, DTO, CRUD, domain, feature, function, or REST creation.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, LSP
---

# Spring API Development Rules

Standard rules for Spring Boot REST API development in this project.

## Package Structure

```
com.apiece.springboot_sns_sample
├── controller/              # REST API controllers
│   └── dto/                 # Request/Response DTOs
├── domain/                  # Domain packages
│   └── user/                # User domain
│       ├── User.java        # Entity
│       ├── UserRepository.java
│       ├── UserService.java
│       └── UserException.java
└── config/                  # Configuration classes
```

## Common Rules

- Constructor injection using `@RequiredArgsConstructor` where possible
- No field injection (`@Autowired` on fields)
- `@ConfigurationProperties` classes should be written as records
- Use Lombok `@Getter` actively for entities and classes (except DTOs which use records)

## Controller

- Use `@RestController`
- Do not use `@RequestMapping` at class level; write full endpoint path on each method
- Return type: `ResponseEntity<T>`
- Naming: `*Controller`

## DTO

- Only controller DTOs go in `controller/dto` package
- Use Java `record`
- Request: `toEntity()` method
- Response: `from(Entity)` static factory

## Domain

Each domain is organized under `domain/{domainName}/` package:

- `{Domain}.java` - Entity
- `{Domain}Repository.java` - Data access
- `{Domain}Service.java` - Business logic
- `{Domain}Exception.java` - Domain exception

### Entity

- `protected` default constructor
- `@GeneratedValue(strategy = GenerationType.IDENTITY)`
- Associations: `FetchType.LAZY` by default
- No FK constraints in database; use `@JoinColumn` without FK constraints

### Repository

- Extends `JpaRepository<Entity, ID>`
- Follow Spring Data JPA query method naming conventions

### Service

- Use `@Transactional` only when necessary:
    - Use when multiple write operations must be in a single transaction
    - Use when Dirty Checking is needed (entity modification without explicit save)
    - Do NOT use for single Repository operations (they handle transactions automatically)
    - Do NOT use for simple read operations

## Exception Handling

- Domain exceptions: `domain/{domainName}/{Domain}Exception.java`
- Global handling with `@RestControllerAdvice`

## API Shell Script

When creating a new API, create a shell script in `src/main/resources/http/`:

- File naming: lowercase with resource name (e.g., `post.sh`, `follow.sh`)
- Include curl commands for all endpoints (POST, GET, PUT, DELETE)
- Use `BASE_URL="http://localhost:8080"` variable
- Use `-b cookies.txt` for authenticated requests
- Add descriptive echo statements before each curl command
- Start with `#!/bin/bash` shebang
