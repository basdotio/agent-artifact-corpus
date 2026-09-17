---
name: enforcing-lgf
description: Enforces Logic Game Framework conventions for inkmon-godot GDScript code. Covers Actor lifecycle, shared Action/Condition/Cost statelessness, AbilitySet/AttributeSet access, PreEventConfig Intent returns, Resolvers, and event system patterns. Use when writing or modifying GDScript that touches Actor, AbilitySet, Action, Condition, Cost, Resolver, PreEventConfig, or the event system.
---

# Logic Game Framework Conventions

## Contents
- [When to use](#when-to-use)
- [Reference](#reference)
- [Coding Conventions](#coding-conventions)
  - [1. Attribute Access](#1-attribute-access)
  - [2. Actor Creation & Registration](#2-actor-creation--registration)
  - [3. Shared Object Statelessness (CRITICAL)](#3-shared-object-statelessness-critical)
  - [4. GameStateProvider](#4-gamestateprovider)
  - [5. Resolvers](#5-resolvers)
  - [6. PreEventConfig Handlers](#6-preeventconfig-handlers)
  - [7. GameWorld Dependency](#7-gameworld-dependency)
- [Standard Workflow](#standard-workflow)
- [Validation Checklist](#validation-checklist)

## When to use

Apply when writing or modifying GDScript that touches the Logic Game Framework: Actor creation, AbilitySet/AttributeSet access, Action/Condition/Cost implementation, PreEventConfig handlers, Resolvers, or the event system.

## Reference

- **Conventions (detailed)**: See [reference/conventions-detail.md](reference/conventions-detail.md) — Full examples, reference chain diagrams, architecture
- **Entity & World**: See [reference/entity.md](reference/entity.md) — Actor, System, GameWorld, GameplayInstance
- **Abilities**: See [reference/abilities.md](reference/abilities.md) — Ability, AbilitySet, AbilityConfig, Components, Builder API
- **Actions**: See [reference/actions.md](reference/actions.md) — Action, ExecutionContext, TargetSelector, Resolvers
- **Events**: See [reference/events.md](reference/events.md) — EventProcessor, MutableEvent, Intent, Modification
- **Attributes**: See [reference/attributes.md](reference/attributes.md) — RawAttributeSet, AttributeModifier, Calculator, TagContainer
- **Stdlib**: See [reference/stdlib.md](reference/stdlib.md) — StatModifier, TimeDuration, Stack, Projectile, Replay, Timeline
- **Example App**:
  - [reference/example-app-overview.md](reference/example-app-overview.md) — Three-layer architecture, Core Events, cross-layer data flow
  - [reference/example-app-game-logic.md](reference/example-app-game-logic.md) — Actor/Ability/Action patterns, AI strategy, config organization
  - [reference/example-app-presentation.md](reference/example-app-presentation.md) — Replay pipeline, Visualizers, extension guide

---

## Coding Conventions

### 1. Attribute Access

Direct access, no getter/setter wrappers. Methods with business logic are fine.

```gdscript
# DO
var hp := actor.attribute_set.hp
actor.attribute_set.hp -= damage

# DON'T
func get_hp() -> float:
    return attribute_set.hp

# OK - has logic beyond simple access
func is_alive() -> bool:
    return attribute_set.hp > 0
```

---

### 2. Actor Creation & Registration

Two-step: **construct** then **register**.

```gdscript
var actor := CharacterActor.new(char_class)
instance.add_actor(actor)  # Framework assigns ID, calls _on_id_assigned()
```

| Phase | Actor._id | Notes |
|-------|-----------|-------|
| After `.new()` | Empty string | Do NOT generate ID in `_init` |
| After `add_actor()` | `{instance_id}:{local_id}` | Auto-generated, triggers `_on_id_assigned()` |

Override `_on_id_assigned()` when components created in `_init` need the actor ID:

```gdscript
func _on_id_assigned() -> void:
    ability_set.owner_actor_id = get_id()
    attribute_set.actor_id = get_id()
```

`get_owner_gameplay_instance()` uses stored `_instance_id` + `GameWorld.get_instance_by_id()` to avoid RefCounted circular references.

---

### 3. Shared Object Statelessness (CRITICAL)

| Type | Ownership | Mutable State? |
|------|-----------|----------------|
| Ability / AbilityComponent | Per character | YES |
| **Action / Condition / Cost / TriggerConfig** | **SHARED via `static var`** | **NO** |

`static var` configs run `.new()` once at class load. All characters share the same Action/Condition/Cost instances by reference.

**RULE: `execute()` / `check()` / `pay()` MUST NOT modify `self`**

```gdscript
# WRONG: mutable state in shared Action
class BadAction extends Action.BaseAction:
    var _count := 0
    func execute(ctx: ExecutionContext) -> void:
        _count += 1  # FORBIDDEN - pollutes other characters

# CORRECT: state in external storage
class GoodAction extends Action.BaseAction:
    func execute(ctx: ExecutionContext) -> void:
        var ability_set := _get_owner_ability_set(ctx)
        var count: int = ability_set.tag_container.get_stacks("my_counter")
        ability_set.tag_container.apply_tag("my_counter", -1.0, count + 1)
```

**State Storage:**

| Scope | Location |
|-------|----------|
| Cross-ability | `AbilitySet.tag_container` |
| Single-ability cross-cast | `AbilitySet.tag_container` (Tag + Stacks) |
| Single-cast | Local variables in `execute()` |

Debug: `logic_game_framework/debug/action_state_check = true` in Project Settings.

---

### 4. GameStateProvider

`IGameStateProvider.get_game_state()` intentionally returns `Variant` — the ONLY acceptable Variant return in the framework.

---

### 5. Resolvers

Type-safe delayed evaluation for shared objects. Create via `Resolvers` factory, evaluate via `resolve(ctx)`.

| Resolver | Fixed | Dynamic |
|----------|-------|---------|
| `FloatResolver` | `Resolvers.float_val(v)` | `Resolvers.float_fn(fn)` |
| `IntResolver` | `Resolvers.int_val(v)` | `Resolvers.int_fn(fn)` |
| `StringResolver` | `Resolvers.str_val(v)` | `Resolvers.str_fn(fn)` |
| `DictResolver` | `Resolvers.dict_val(v)` | `Resolvers.dict_fn(fn)` |
| `Vector3Resolver` | `Resolvers.vec3_val(v)` | `Resolvers.vec3_fn(fn)` |

`ParamResolver.resolve_param(resolver: Variant, ctx)` accepting Variant is intentional. Prefer typed Resolvers in new code.

---

### 6. PreEventConfig Handlers

Signature: `func(MutableEvent, AbilityLifecycleContext) -> Intent`

**Every code path MUST return an Intent.** Missing return = null = runtime assertion failure.

| Intent | Factory | Use Case |
|--------|---------|----------|
| Pass through | `EventPhase.pass_intent()` | Condition not met |
| Modify | `EventPhase.modify_intent(id, [Modification])` | Damage reduction |
| Cancel | `EventPhase.cancel_intent(id, reason)` | Immunity, block |

```gdscript
# Correct: all branches return Intent
func(mutable: MutableEvent, ctx: AbilityLifecycleContext) -> Intent:
    if some_condition:
        return EventPhase.cancel_intent(ctx.ability.id, "immune")
    return EventPhase.pass_intent()

# WRONG: forgot return
func(mutable: MutableEvent, ctx: AbilityLifecycleContext) -> Intent:
    EventPhase.modify_intent(ctx.ability.id, [...])
    # Missing return!
```

Optional filter: `func(Dictionary, AbilityLifecycleContext) -> bool` — return `true` to process event.

---

### 7. GameWorld Dependency

Framework directly references `GameWorld` Autoload. This is intentional — do not attempt to decouple.

---

## Standard Workflow

When implementing new game logic that touches the framework, follow these steps:

1. **Identify scope** → Is this an Actor, Ability, Action, PreEvent, or System?
   - **New Actor**: Follow §2 (construct → register → `_on_id_assigned`)
   - **New Ability**: Use `AbilityConfig.builder()`, see [reference/abilities.md](reference/abilities.md)
   - **New Action**: Extend `Action.BaseAction`, ensure statelessness (§3)
   - **New PreEvent handler**: Follow §6 (every path returns Intent)
2. **Check shared vs owned** → Refer to §3 ownership table. If shared (`static var`), MUST NOT store mutable state in `self`.
3. **Use Resolvers for dynamic params** → If an Action needs runtime values, use `Resolvers` factory (§5) instead of storing state.
4. **Implement** → Write the code following conventions above.
5. **Validate** → Run the checklist below.

## Validation Checklist

Before considering implementation complete, verify:

- [ ] Actor IDs: NOT generated in `_init`; `_on_id_assigned()` syncs ID to components
- [ ] Shared objects (Action/Condition/Cost/TriggerConfig): `execute()`/`check()`/`pay()` do NOT modify `self`
- [ ] State storage: cross-ability → `tag_container`; single-cast → local variables
- [ ] Attribute access: direct `actor.attribute_set.x`, no trivial getter/setter wrappers
- [ ] PreEventConfig handlers: EVERY code path returns an `Intent` (pass/modify/cancel)
- [ ] Resolvers: dynamic values use `Resolvers.float_fn()` etc., not instance fields
- [ ] No attempts to decouple `GameWorld` Autoload dependency
- [ ] `IGameStateProvider.get_game_state()` returning `Variant` is intentional — do not "fix"
