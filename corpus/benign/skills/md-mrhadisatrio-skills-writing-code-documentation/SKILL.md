---
name: writing-code-documentation
description: Conventions on writing code documentation for public APIs. Always use when writing new features or greenfield code. Always use, with-user-approval, when refactoring existing code.
---

# Code Documentation

Every public API gets documented in the language's mandated documentation format. Documentation describes the service a unit of code provides to its callers — not how it works internally.

## 1. Documentation Segments

Documentation consists of up to four ordered segments.

### Service Brief (required)

What service the code provides to callers. Max two lines. Written from the caller's perspective, answering "what do I get from this?"

For **types** (classes, interfaces, objects), open with an identity phrase — a noun describing what the type *is*: `"An [Event] signalling..."`, `"A repository for..."`. For **callables** (functions, methods), open with a verb describing what the caller *gets*: `"Persists a..."`, `"Returns the..."`.

### Nuance Extension (optional)

Additional context a caller needs: edge cases, threading guarantees, preconditions, error behavior, performance characteristics. Skip entirely if the brief says it all.

### Usage Snippet (optional, class-level only)

A short code example showing how to obtain the service described. Skip if usage is trivial or inferrable from the constructor/method signatures.

### Annotation Tags (non-optional where the language supports them)

- Apply any annotation relevant to the callable or type — `@param`, `@return`/`@returns`, `@throws`/`@exception`, `@deprecated`, `@see`, `@since`, and so on.
- One line per tag — never multi-paragraph.
- Only include tags that add caller-facing information not already clear from the signature.
- Prefer annotations that document behaviour over metadata annotations: `@since` is rarely useful (callers shouldn't need to know when something was added) and `@author` is noise in a version-controlled codebase — skip both unless the project explicitly requires them.

## 2. What NOT to Do

- Don't restate the declared name — "This class is a...", "This method does...", "A CompletionEvent that..."
- Don't use filler phrases — "This is used to...", "A helper that...", "Responsible for..."
- Don't document private/internal APIs unless their complexity warrants it
- Don't write implementation details (how) — write caller-facing contracts (what)
- Don't force optional segments — skip nuance if the brief is enough, skip usage if trivial
- Don't write multi-paragraph annotation tags — one line each
- Don't use `@author` (redundant with version control) or `@since` (callers shouldn't need release history) unless the project explicitly mandates them
- Don't document getters/properties unless semantics are non-obvious

## 3. Examples

### Types

Good:

```kotlin
/**
 * An [Event] signalling the successful completion of an operation.
 */
class CompletionEvent : Event()
```

Bad:

```kotlin
/**
 * Signals the successful completion of an operation.
 */
class CompletionEvent : Event()
```

### Callables

Good:

```kotlin
/**
 * Persists a [Moment] to the local filesystem, creating the backing
 * file if it doesn't exist.
 *
 * Writes are atomic — a partial failure won't corrupt existing data.
 * Thread-safe; concurrent writes to the same [Moment] are serialized.
 *
 * @param moment Moment to persist.
 * @return The persisted Moment with its updated timestamp.
 */
fun save(moment: Moment): Moment
```

Bad:

```kotlin
/**
 * This method saves a moment. It takes a moment and returns a moment.
 *
 * @param moment the moment
 * @return Moment
 */
fun save(moment: Moment): Moment
```

## 4. Language Format Reference

| Language        | Format             | Common annotation tags                                          |
|-----------------|--------------------|-----------------------------------------------------------------|
| Kotlin          | KDoc (`/** */`)    | `@param`, `@return`, `@throws`, `@see`, `@deprecated`           |
| Java            | Javadoc (`/** */`) | `@param`, `@return`, `@throws`, `@see`, `@deprecated`           |
| JavaScript / TS | JSDoc (`/** */`)   | `@param`, `@returns`, `@throws`, `@deprecated`, `@see`, `@type` |
| Python          | Docstrings (`"""`) | `:param`, `:return`, `:raises`, `:deprecated`                   |
| Rust            | `///`              | Inline prose sections: `# Errors`, `# Panics`, `# Examples`     |
| Swift           | `///`              | `- Parameter`, `- Returns`, `- Throws`, `- Note`, `- Warning`   |
| Go              | `//`               | Inline prose, `Deprecated:` prefix                              |

