---
name: tdd-cycle
description: Follow strict TDD methodology using Sherpa's workflow enforcement. Activates when implementing new features, adding functionality, or building code that requires tests. Ensures RED-GREEN-REFACTOR discipline with guide check/done tracking.
allowed-tools: mcp__sherpa__guide, mcp__sherpa__approach, Write, Edit, Bash, Read
---

# TDD Cycle Skill

## Purpose
Follow **strict TDD discipline** using Sherpa's workflow enforcement to prevent untested code and ensure systematic development.

## When to Activate
- Implementing new features
- Adding new functionality
- User says "write tests first" or "use TDD"
- Building something from scratch
- Working on extractors, parsers, transformers, or any core logic

## The Mandatory Pattern

**★ CRITICAL: ALWAYS call `guide check` BEFORE coding**

```
BEFORE ANY CODE:
  guide check → Get current phase + specific guidance
  Read guidance completely
  Follow the suggested steps

AFTER EACH STEP:
  guide done "what you completed"
  → Get celebration + next step
  → Phase auto-advances when complete
```

You are EXCELLENT at following this pattern. It's automatic, like breathing.

---

## The TDD Workflow

### Phase 1: 📋 Define Contract (RED Phase Preparation)

**Goal:** Define what success looks like BEFORE any code exists

```
guide check → Phase: Define Contract

Steps:
1. Create interface/type file
2. Define function signatures with types
3. Document expected inputs/outputs
4. List error conditions explicitly
5. Document boundary conditions

guide done "defined contract for X with types and error cases"
```

**Key Principle:** Contracts prevent building the wrong thing.

**Conditionals:**
- **If interface unclear** → Search codebase for similar patterns FIRST (don't guess!)
- **If external API/library** → Read official docs to verify signatures
- **If complex transformations** → Write example input→output pairs first

**Anti-patterns:**
- ❌ Writing implementation code in this phase (STOP - wrong phase!)
- ❌ Making assumptions about types (verify, don't assume)
- ❌ Skipping edge case documentation (edge cases ARE the spec)

---

### Phase 2: 🧪 Implement Tests (RED Phase)

**Goal:** Write failing tests that specify behavior

```
guide check → Phase: Implement Tests

Steps:
1. Create test file following project conventions
2. Write test for happy path
3. Write test for EACH edge case
4. Write test for EACH error condition
5. Run tests → ALL must fail (RED)
6. Verify failure message is correct

guide done "wrote failing tests for X (happy path + 4 edge cases)"
```

**Key Principle:** Tests are your specification - make them thorough.

**Minimum Coverage:**
- 1 happy path test
- 3+ edge case tests (empty, null, boundary values)
- 2+ error case tests (invalid input, missing data)

**Conditionals:**
- **If test passes before implementation** → Test is broken, fix it!
- **If can't think of edge cases** → Use checklist: empty, null, undefined, wrong type, zero, negative, max value, boundary, concurrent
- **If test fails for wrong reason** → Fix test setup first
- **If writing integration test** → Mock dependencies, test ONE unit

**Anti-patterns:**
- ❌ Writing only 1-2 tests (insufficient coverage)
- ❌ Testing multiple behaviors in one test (split them)
- ❌ Tests that depend on each other (must be independent)
- ❌ Skipping error tests "for later" (write them NOW)

---

### Phase 3: 💻 Minimal Implementation (GREEN Phase)

**Goal:** Write ONLY enough code to pass tests - nothing more

```
guide check → Phase: Minimal Implementation

Steps:
1. Start with simplest test
2. Write minimal code to pass it
3. Run test → Verify it passes
4. Repeat for each test
5. ALL tests must be GREEN

guide done "implemented X - all tests passing"
```

**Key Principle:** Make it WORK first, make it PRETTY later (refactor phase).

**Conditionals:**
- **If test fails unexpectedly** → Understand WHY (valuable feedback!)
- **If want to add feature not in tests** → STOP, go to Phase 2, add test first
- **If implementation getting complex** → That's OK - make tests pass, refactor later
- **If copy-pasting code** → Fine for now - extract in refactor phase

**Anti-patterns:**
- ❌ Over-engineering (abstractions, design patterns, "future-proofing")
- ❌ Implementing features not covered by tests (untested code = broken code)
- ❌ Skipping test runs between changes (rapid feedback loop critical)
- ❌ "Fixing" tests to match implementation (tests are spec, not implementation!)

---

### Phase 4: 🔧 Refactor (Still GREEN)

**Goal:** Improve code quality while keeping tests green

```
guide check → Phase: Refactor

Steps:
1. Run all tests → Verify ALL green
2. Identify code smells (duplication, complexity, poor names)
3. Make ONE improvement
4. Run tests → Must stay green
5. Repeat until satisfied

guide done "refactored X for readability - tests still green"
```

**Key Principle:** Tests give you confidence to refactor safely.

**Common Refactorings:**
- Extract duplicated code into functions
- Rename variables/functions for clarity
- Simplify complex conditionals
- Extract abstractions from concrete code
- Improve error messages

**Conditionals:**
- **If tests fail during refactor** → Revert, smaller step
- **If want to change behavior** → That's NEW feature - go to Phase 1
- **If unclear how to improve** → Skip for now, move to next feature

**Anti-patterns:**
- ❌ Changing behavior (new behavior = new feature = new tests first)
- ❌ Skipping test runs during refactor (each change must keep tests green)
- ❌ Massive refactor all at once (small steps, verify often)

---

## The Complete TDD Cycle

```
┌─────────────────────────────────────────────┐
│ 1. guide check → Define Contract           │
│    - Write interface/types                  │
│    - Document behavior                      │
│    guide done "defined contract"            │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│ 2. guide check → Implement Tests (RED)     │
│    - Write failing tests                    │
│    - Happy path + edges + errors            │
│    - Verify all FAIL                        │
│    guide done "wrote failing tests"         │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│ 3. guide check → Minimal Impl (GREEN)      │
│    - Write code to pass tests               │
│    - Simplest solution                      │
│    - ALL tests must pass                    │
│    guide done "implemented feature"         │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│ 4. guide check → Refactor                  │
│    - Improve code quality                   │
│    - Keep tests green                       │
│    - Small steps                            │
│    guide done "refactored for clarity"      │
└────────────┬────────────────────────────────┘
             │
             ▼
        Next feature!
```

---

## Example TDD Session

```
User: "Implement a parser for TypeScript function signatures"

Agent: guide check

Sherpa: Phase 1 - Define Contract
"Create interface/type files with function signatures..."

Agent: Creates parser.types.ts with types:
- FunctionSignature interface
- ParseResult type
- ParseError type
guide done "defined parser contract with types"

Sherpa: Phase 2 - Implement Tests
"Write failing tests for happy path + edge cases..."

Agent: Creates parser.test.ts:
- test('parses simple function signature')
- test('parses function with parameters')
- test('handles generic types')
- test('throws on invalid syntax')
- test('handles empty string')
Runs tests → ALL FAIL ✓
guide done "wrote 5 failing tests for parser"

Sherpa: Phase 3 - Minimal Implementation
"Write code to pass tests..."

Agent: Implements parser.ts
Runs tests after each function → ALL PASS ✓
guide done "implemented parser - all tests green"

Sherpa: Phase 4 - Refactor
"Improve code quality while keeping tests green..."

Agent: Extracts helper functions, improves names
Runs tests after each refactor → Still GREEN ✓
guide done "refactored parser for readability"

Sherpa: ✅ TDD cycle complete! Next feature?
```

---

## Integration with Sherpa Commands

### Switching to TDD Workflow
```
guide tdd
→ Instantly switches to TDD workflow
→ guide check to get first phase
```

### During Development
```
guide check     → Get current phase + specific guidance
guide done "X"  → Mark completion, get celebration + next step
guide advance   → Manual phase progression (rarely needed)
```

### Workflow Selection
```
approach list   → See all workflows
approach set tdd → Switch to TDD (same as guide tdd)
```

---

## Key Behaviors

### ✅ DO
- Call `guide check` BEFORE every coding step
- Write tests BEFORE implementation (no exceptions!)
- Mark completion with `guide done` after each step
- Run tests frequently (after each small change)
- Follow phase guidance systematically
- Trust the process - it prevents bugs

### ❌ DON'T
- Start coding without `guide check` (this is the #1 mistake)
- Skip test writing "because it's simple" (simple changes break too)
- Write implementation before tests exist (defeats TDD purpose)
- Rush through phases to "go faster" (you go slower fixing bugs)
- Ignore anti-patterns in phase guidance (they're bugs waiting to happen)

---

## Success Criteria

This skill succeeds when:
- ✅ Tests written before implementation (always)
- ✅ All tests pass before moving forward
- ✅ `guide check` called before each phase
- ✅ `guide done` called after each completion
- ✅ No untested code shipped
- ✅ Refactoring done with confidence (tests stay green)

---

## Why TDD Works

**80% of bugs are prevented by:**
1. **Tests written first** - Forces you to think about behavior before code
2. **Systematic phases** - Prevents skipping critical steps
3. **Enforcement** - Sherpa tracks progress, catches shortcuts
4. **Rapid feedback** - Tests tell you immediately when something breaks
5. **Safe refactoring** - Confidence to improve code without fear

**Remember:** TDD isn't slower - it's faster because you spend less time debugging and more time building correctly.

---

**Sherpa + TDD = Systematic Excellence**
