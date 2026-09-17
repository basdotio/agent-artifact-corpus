---
name: laravel-tyro
description: Complete knowledge and operation guide for Tyro - the Laravel authentication, authorization, and role-based access control package. Use this skill when working with Laravel projects that use Tyro, when setting up authentication/authorization, managing roles/privileges, using Tyro commands, middleware, Blade directives, or REST API endpoints. Trigger for any mention of Tyro, Laravel auth, RBAC, role management, privilege management, user suspension, or Laravel Sanctum integration with permissions.
---

# Laravel Tyro Skill

This skill provides complete knowledge of **Tyro** - a comprehensive authentication, authorization, and role-based access control (RBAC) solution for Laravel 12 and 13.

## When to Use This Skill

Use this skill when:
- Setting up Tyro in a Laravel project
- Managing users, roles, or privileges
- Using Tyro's CLI commands (40+ commands)
- Implementing route protection with middleware
- Using Blade directives for permission checks
- Working with Tyro's REST API
- Troubleshooting Tyro-related issues
- Auditing user actions and role changes

---

## Quick Overview

**Tyro** provides:
- Complete authentication with Laravel Sanctum
- Role-based access control (RBAC)
- Fine-grained privilege management
- User suspension workflows
- 40+ Artisan commands
- 7 Blade directives
- REST API endpoints
- Comprehensive audit trail
- Two-tier caching system

**Default seeded roles:**
- `super-admin` - Full system access
- `administrator` - Administrative access
- `editor` - Content management
- `user` - Standard registered user
- `customer` - Customer account
- `all` - Universal access (wildcard)

**Default credentials (after seeding):**
- Email: `admin@tyro.project`
- Password: `tyro`

---

## Installation & Setup

### One-Command Installation

```bash
composer require hasinhayder/tyro
php artisan tyro:sys-install
```

This single command:
1. Installs and configures Sanctum
2. Runs migrations
3. Prompts to seed roles/privileges/admin user
4. Prepares your User model

### Manual Installation Steps

If you need more control:

```bash
# Install package
composer require hasinhayder/tyro

# Publish assets (optional)
php artisan vendor:publish --tag=tyro-config
php artisan vendor:publish --tag=tyro-migrations

# Run migrations
php artisan migrate

# Seed roles and privileges
php artisan tyro:seed-all --force

# Prepare User model
php artisan tyro:user-prepare
```

### User Model Requirements

Your User model (default: `App\Models\User`) must use the `HasTyroRoles` trait:

```php
<?php

namespace App\Models;

use Illuminate\Foundation\Auth\User as Authenticatable;
use Laravel\Sanctum\HasApiTokens;
use HasinHayder\Tyro\Concerns\HasTyroRoles;

class User extends Authenticatable
{
    use HasApiTokens, HasTyroRoles;
}
```

The trait provides ALL role/privilege methods. No other code changes needed.

---

## CLI Commands Reference

### System Commands

```bash
# Full installation
php artisan tyro:sys-install

# Prepare User model with trait
php artisan tyro:user-prepare

# Show version
php artisan tyro:sys-version

# Show package info
php artisan tyro:sys-about

# Open documentation
php artisan tyro:sys-doc

# Open GitHub repo
php artisan tyro:sys-star

# Get Postman collection
php artisan tyro:sys-postman
```

### User Management

```bash
# Create user with default role
php artisan tyro:user-create

# List all users
php artisan tyro:user-list

# List users with roles
php artisan tyro:user-list-with-roles

# Update user
php artisan tyro:user-update --user=1 --name="New Name"

# Delete user (prevents deleting last admin)
php artisan tyro:user-delete --user=1

# Suspend user (revokes all tokens)
php artisan tyro:user-suspend --user=admin@example.com --reason="Policy violation"

# Unsuspend user
php artisan tyro:user-unsuspend --user=admin@example.com

# List suspended users
php artisan tyro:user-suspended

# Show user's roles and privileges
php artisan tyro:user-roles --user=1
```

### Role Management

```bash
# List all roles
php artisan tyro:role-list

# List roles with privileges
php artisan tyro:role-list-with-privileges

# Create new role
php artisan tyro:role-create --name="Content Manager" --slug="content-manager"

# Update role
php artisan tyro:role-update --role="content-manager" --name="Content Editor"

# Delete role (protected roles cannot be deleted)
php artisan tyro:role-delete --role="content-manager"

# Assign role to user
php artisan tyro:role-assign --user=5 --role="editor"

# Remove role from user
php artisan tyro:role-remove --user=5 --role="editor"

# List users with specific role
php artisan tyro:role-users --role="editor"
```

### Privilege Management

```bash
# List all privileges
php artisan tyro:privilege-list

# Create privilege
php artisan tyro:privilege-create --name="Delete Articles" --slug="articles.delete"

# Update privilege
php artisan tyro:privilege-update --privilege="articles.delete" --name="Remove Articles"

# Delete privilege
php artisan tyro:privilege-delete --privilege="articles.delete"

# Attach privilege to role
php artisan tyro:privilege-attach --role="editor" --privilege="articles.publish"

# Detach privilege from role
php artisan tyro:privilege-detach --role="editor" --privilege="articles.publish"

# Show user's privileges
php artisan tyro:user-privileges --user=1
```

### Authentication & Token Management

```bash
# Login (mint token)
php artisan tyro:auth-login --email=admin@tyro.project

# Create token without password
php artisan tyro:user-token --user=1

# Revoke specific token
php artisan tyro:auth-logout --token=xyz

# Revoke all user tokens
php artisan tyro:auth-logout-all --user=1

# Emergency: revoke ALL tokens
php artisan tyro:auth-logout-all-users --force

# Inspect token
php artisan tyro:auth-me --token=xyz
```

### Seeding Commands

```bash
# Seed everything (roles, privileges, admin user)
php artisan tyro:seed-all --force

# Seed only roles
php artisan tyro:seed-roles --force

# Seed only privileges
php artisan tyro:seed-privileges --force

# Purge all roles
php artisan tyro:role-purge --force

# Purge all privileges
php artisan tyro:privilege-purge --force
```

### Audit Commands

```bash
# List audit logs
php artisan tyro:audit-list --limit=50

# Filter by event type
php artisan tyro:audit-list --event=role.assigned

# Purge old logs (respects retention_days config)
php artisan tyro:audit-purge --days=30
```

---

## Middleware Reference

### Available Middleware

| Middleware | Alias | Behavior |
|------------|-------|----------|
| `EnsureTyroRole` | `role` | User must have **ALL** specified roles |
| `EnsureAnyTyroRole` | `roles` | User must have **ANY** of the specified roles |
| `EnsureTyroPrivilege` | `privilege` | User must have **ALL** specified privileges |
| `EnsureAnyTyroPrivilege` | `privileges` | User must have **ANY** of the specified privileges |
| `TyroLog` | `tyro.log` | Logs request/response for debugging |

### Route Protection Examples

```php
use Illuminate\Support\Facades\Route;

// Require admin role only
Route::middleware(['auth:sanctum', 'role:admin'])
    ->get('admin/dashboard', [AdminDashboardController::class, 'index']);

// Require both admin AND super-admin
Route::middleware(['auth:sanctum', 'role:admin,super-admin'])
    ->delete('users/{user}', [UserController::class, 'destroy']);

// Allow editor OR admin
Route::middleware(['auth:sanctum', 'roles:editor,admin'])
    ->post('articles/publish', [ArticleController::class, 'publish']);

// Require specific privilege
Route::middleware(['auth:sanctum', 'privilege:reports.run'])
    ->get('reports', [ReportController::class, 'index']);

// Allow any of multiple privileges
Route::middleware(['auth:sanctum', 'privileges:billing.view,reports.run'])
    ->get('dashboard', [DashboardController::class, 'index']);

// Combine multiple middleware
Route::middleware(['auth:sanctum', 'role:admin', 'privilege:users.delete'])
    ->delete('users/{user}', [UserController::class, 'destroy']);

// Audit sensitive routes
Route::middleware(['auth:sanctum', 'role:admin', 'tyro.log'])
    ->post('roles', [RoleController::class, 'store']);
```

---

## Blade Directives Reference

### All Directives

| Directive | Purpose |
|-----------|---------|
| `@userCan('ability')` | Check if user has role OR privilege |
| `@hasRole('slug')` | Check if user has specific role |
| `@hasAnyRole('slug1','slug2')` | Check if user has ANY listed roles |
| `@hasAllRoles('slug1','slug2')` | Check if user has ALL listed roles |
| `@hasPrivilege('slug')` | Check if user has specific privilege |
| `@hasAnyPrivilege('slug1','slug2')` | Check if user has ANY listed privileges |
| `@hasAllPrivileges('slug1','slug2')` | Check if user has ALL listed privileges |

All directives return `false` if no user is authenticated.

### Usage Examples

```blade
@hasRole('admin')
    <div class="admin-panel">
        <h2>Admin Dashboard</h2>
    </div>
@endhasRole

@hasAnyRole('editor', 'author')
    <div class="content-tools">
        <a href="/articles/create">New Article</a>
    </div>
@endhasAnyRole

@hasAllRoles('admin', 'super-admin')
    <button class="btn-danger">Delete User</button>
@endhasAllRoles

@hasPrivilege('articles.publish')
    <button class="btn-success">Publish</button>
@endhasPrivilege

@hasAnyPrivilege('articles.edit', 'articles.delete')
    <div class="article-actions">
        @hasPrivilege('articles.edit')
            <button>Edit</button>
        @endhasPrivilege
        @hasPrivilege('articles.delete')
            <button>Delete</button>
        @endhasPrivilege
    </div>
@endhasAnyPrivilege

@userCan('admin')
    <!-- Checks both role 'admin' and privilege 'admin' -->
    <div>Admin content</div>
@enduserCan

@hasRole('subscriber')
    <div class="premium-content">
        {{ $article->premium_content }}
    </div>
@else
    <p>This is premium content. <a href="/subscribe">Subscribe now</a></p>
@endhasRole
```

---

## REST API Reference

### Base URL

All routes are prefixed by `config('tyro.route_prefix')` (default: `api`)

### Authentication

Include Bearer token in headers:
```
Authorization: Bearer {token}
```

### Public Endpoints

```
GET    /api/tyro              # Package information
GET    /api/tyro/version      # Version number
POST   /api/login             # Authenticate, receive token
POST   /api/users             # Register new user
```

### Authenticated Endpoints

```
GET    /api/me                # Current user info
PUT    /api/users/{user}      # Update self
POST   /api/users/{user}      # Update self
DELETE /api/users/{user}      # Delete own account
```

### Admin Endpoints (require admin role)

**User Management:**
```
GET    /api/users             # List all users
GET    /api/users/{user}      # Get user details
DELETE /api/users/{user}      # Delete user (admin)
POST   /api/users/{user}/roles        # Assign role
DELETE /api/users/{user}/roles/{role} # Remove role
POST   /api/users/{user}/suspend      # Suspend user
DELETE /api/users/{user}/suspend      # Unsuspend user
```

**Role Management:**
```
GET    /api/roles             # List roles
POST   /api/roles             # Create role
GET    /api/roles/{role}      # Get role details
PUT    /api/roles/{role}      # Update role
DELETE /api/roles/{role}      # Delete role
GET    /api/roles/{role}/users      # Users with role
GET    /api/roles/{role}/privileges  # Role privileges
POST   /api/roles/{role}/privileges  # Attach privilege
DELETE /api/roles/{role}/privileges/{privilege} # Detach
```

**Privilege Management:**
```
GET    /api/privileges        # List privileges
POST   /api/privileges        # Create privilege
GET    /api/privileges/{privilege} # Get details
PUT    /api/privileges/{privilege} # Update
DELETE /api/privileges/{privilege} # Delete
```

**Audit Logs:**
```
GET    /api/audit-logs        # List audit logs
```

### API Usage Examples

```bash
# Login
curl -X POST http://localhost/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@tyro.project","password":"tyro"}'

# Register
curl -X POST http://localhost/api/users \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","email":"john@example.com","password":"password123","password_confirmation":"password123"}'

# Get roles (authenticated)
curl http://localhost/api/roles \
  -H "Authorization: Bearer YOUR_TOKEN"

# Assign role to user
curl -X POST http://localhost/api/users/5/roles \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role_id":4}'
```

---

## HasTyroRoles Trait API

### Role Methods

```php
$user->roles(): BelongsToMany
// Eloquent relationship to roles

$user->assignRole(Role $role): void
// Attach a role to user

$user->removeRole(Role $role): void
// Detach a role from user

$user->hasRole(string $role): bool
// Check if user has role (supports wildcard '*')

$user->hasRoles(array $roles): bool
// Check if user has ALL roles

$user->tyroRoleSlugs(): array
// Get all role slugs as array (cached)
// Returns: ['admin', 'editor']
```

### Privilege Methods

```php
$user->privileges(): Collection
// Get all unique privileges from user's roles

$user->hasPrivilege(string $privilege): bool
// Check if user has specific privilege

$user->hasPrivileges(array $privileges): bool
// Check if user has ALL privileges

$user->tyroPrivilegeSlugs(): array
// Get all privilege slugs as array (cached)
// Returns: ['articles.create', 'articles.publish']
```

### Authorization

```php
$user->can($ability, $arguments = []): bool
// Unified permission check:
// 1. Checks privileges first (exact match)
// 2. Then checks roles
// 3. Falls back to Laravel Gate
```

### Suspension Methods

```php
$user->suspend(?string $reason = null): void
// Suspend user, store reason, revoke all tokens

$user->unsuspend(): void
// Remove suspension

$user->isSuspended(): bool
// Check if user is suspended

$user->getSuspensionReason(): ?string
// Get suspension reason
```

---

## Configuration

### Publishing Config

```bash
php artisan tyro:publish-config --force
```

### Key Config Options

Edit `config/tyro.php`:

```php
return [
    // Models
    'models' => [
        'user' => App\Models\User::class,
        'privilege' => HasinHayder\Tyro\Models\Privilege::class,
    ],

    // Table names
    'tables' => [
        'users' => 'users',
        'roles' => 'roles',
        'pivot' => 'user_roles',
        'privileges' => 'privileges',
        'role_privilege' => 'privilege_role',
    ],

    // Route configuration
    'route_prefix' => 'api',
    'guard' => 'sanctum',
    'disable_api' => env('TYRO_DISABLE_API', false),

    // Default role for new users
    'default_user_role_slug' => 'user',

    // Protected roles (cannot be deleted)
    'protected_role_slugs' => ['super-admin', 'administrator', 'all'],

    // Single session login
    'delete_previous_access_tokens_on_login' => false,

    // Cache configuration
    'cache' => [
        'enabled' => true,
        'store' => null, // null = default cache store
        'ttl' => 300,    // seconds, null = indefinite
    ],

    // Audit trail
    'audit' => [
        'enabled' => true,
        'retention_days' => 30,
    ],
];
```

### Environment Variables

```env
# Disable CLI commands
TYRO_DISABLE_COMMANDS=true

# Disable REST API
TYRO_DISABLE_API=true

# Password validation
TYRO_PASSWORD_MIN_LENGTH=8
TYRO_PASSWORD_MAX_LENGTH=64
TYRO_PASSWORD_REQUIRE_NUMBERS=true
TYRO_PASSWORD_REQUIRE_UPPERCASE=true
TYRO_PASSWORD_REQUIRE_LOWERCASE=true
TYRO_PASSWORD_REQUIRE_SPECIAL_CHARS=true
TYRO_PASSWORD_REQUIRE_CONFIRMATION=true
TYRO_PASSWORD_CHECK_COMMON=true
TYRO_PASSWORD_DISALLOW_USER_INFO=true
```

---

## Database Schema

### Tables

**roles:**
- `id` - Primary key
- `name` - Display name
- `slug` - Unique identifier
- `created_at`, `updated_at`

**privileges:**
- `id` - Primary key
- `name` - Display name
- `slug` - Unique identifier
- `description` - Optional description
- `created_at`, `updated_at`

**user_roles** (pivot):
- `id` - Primary key
- `user_id` - Foreign key to users
- `role_id` - Foreign key to roles
- `unique(user_id, role_id)`
- `created_at`, `updated_at`

**privilege_role** (pivot):
- `id` - Primary key
- `privilege_id` - Foreign key to privileges
- `role_id` - Foreign key to roles
- `unique(privilege_id, role_id)`
- `created_at`, `updated_at`

**tyro_audit_logs:**
- `id` - Primary key
- `user_id` - Actor (nullable)
- `event` - Event name
- `auditable_type` - Target model type
- `auditable_id` - Target model ID
- `old_values` - JSON (before state)
- `new_values` - JSON (after state)
- `metadata` - JSON (context)
- `created_at`

**users** (extended):
- `suspended_at` - Timestamp or null
- `suspension_reason` - VARCHAR or null

---

## Caching System

Tyro uses a two-tier caching system:

### 1. Persistent Cache
- Uses Laravel's cache store (Redis, Memcached, File)
- Key patterns:
  - `tyro:user:{user_id}:roles`
  - `tyro:user:{user_id}:privileges`
- Configurable TTL (default: 5 minutes)

### 2. Runtime Cache
- In-memory cache per request
- Version-based invalidation
- Prevents repeated database queries

### Cache Invalidation

Automatic on:
- Role assigned/removed from user
- Privilege attached/detached from role
- Role deleted

Manual:
```php
$user->clearTyroCache(); // Clear for specific user
```

---

## Audit Trail

### Tracked Events

| Category | Events |
|----------|--------|
| User | `role.assigned`, `role.removed`, `suspended`, `unsuspended` |
| Role | `created`, `updated`, `deleted` |
| Privilege | `created`, `updated`, `deleted`, `attached`, `detached` |

### Viewing Audit Logs

```bash
# CLI
php artisan tyro:audit-list --limit=100 --event=role.assigned

# API
GET /api/audit-logs?limit=100&event=role.assigned
```

---

## Common Workflows

### Setting Up a Blog with Roles

```bash
# Create blog-specific roles
php artisan tyro:role-create --name="Author" --slug="author"
php artisan tyro:role-create --name="Reviewer" --slug="reviewer"

# Create privileges
php artisan tyro:privilege-create --name="Create Articles" --slug="articles.create"
php artisan tyro:privilege-create --name="Edit Own Articles" --slug="articles.edit.own"
php artisan tyro:privilege-create --name="Edit Any Article" --slug="articles.edit.any"
php artisan tyro:privilege-create --name="Publish Articles" --slug="articles.publish"
php artisan tyro:privilege-create --name="Delete Articles" --slug="articles.delete"

# Attach to author
php artisan tyro:privilege-attach --role="author" --privilege="articles.create"
php artisan tyro:privilege-attach --role="author" --privilege="articles.edit.own"

# Attach to reviewer
php artisan tyro:privilege-attach --role="reviewer" --privilege="articles.edit.any"
php artisan tyro:privilege-attach --role="reviewer" --privilege="articles.publish"
```

### Protecting Blog Routes

```php
// Authors can create
Route::post('articles', [ArticleController::class, 'store'])
    ->middleware(['auth:sanctum', 'privilege:articles.create']);

// Reviewers can publish
Route::post('articles/{article}/publish', [ArticleController::class, 'publish'])
    ->middleware(['auth:sanctum', 'privilege:articles.publish']);
```

---

## Troubleshooting

### Commands Not Found

```bash
# Check if commands are disabled
grep TYRO_DISABLE_COMMANDS .env

# Re-enable by removing or setting to false
TYRO_DISABLE_COMMANDS=false
```

### API Routes Not Working

```bash
# Check if API is disabled
grep TYRO_DISABLE_API .env

# Re-enable
TYRO_DISABLE_API=false

# Check route list
php artisan route:list --path=tyro
```

### Cache Issues

```bash
# Clear application cache
php artisan cache:clear

# Clear specific Tyro cache
php artisan tyro:cache-clear
```

### User Can't Login

```bash
# Check if suspended
php artisan tyro:user-suspended

# Unsuspend if needed
php artisan tyro:user-unsuspend --user=user@example.com
```

### Migration Issues

```bash
# Re-run migrations
php artisan migrate:fresh --seed

# Or just Tyro migrations
php artisan migrate --path=vendor/hasinhayder/tyro/database/migrations
```

---

## Key Gotchas

1. **Protected Roles** - `super-admin`, `administrator`, `all` cannot be deleted
2. **Last Admin** - Cannot delete the last admin user
3. **Suspension Revokes Tokens** - Suspending a user immediately revokes all their tokens
4. **Wildcard Role** - Role slug `*` grants universal access
5. **Cache Invalidation** - Changes to roles/privileges automatically invalidate cache for affected users
6. **Seeding is Optional** - But highly recommended for first-time setup

---

## For More Information

- GitHub: https://github.com/hasinhayder/tyro
- Tyro Labs: https://tyrolabs.dev/
- Related: tyro-login, tyro-dashboard
