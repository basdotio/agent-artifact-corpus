# Verification Methods Decision Tree

This reference provides a systematic approach to choosing the appropriate verification method for documentation claims.

---

## Decision Tree

```
START: Have a claim to verify
│
├─ Step 1: Check for Canonical Sources
│  │
│  ├─ Is there an OpenAPI/Swagger spec? → Use Canonical Source
│  ├─ Is there a protobuf definition? → Use Canonical Source
│  ├─ Is there a GraphQL schema? → Use Canonical Source
│  ├─ Is there a config schema (JSON Schema, etc.)? → Use Canonical Source
│  ├─ Is there a Makefile/mise.toml for commands? → Use Canonical Source
│  │
│  └─ No canonical source available → Continue to Step 2
│
├─ Step 2: Assess Claim Complexity
│  │
│  ├─ Simple structural claim (type exists, method signature)?
│  │  → Use Symbolic Analysis
│  │
│  ├─ Simple behavioral claim (returns specific error, checks condition)?
│  │  → Use Symbolic Analysis
│  │
│  ├─ Configuration constant or environment variable?
│  │  → Use Symbolic Analysis
│  │
│  ├─ Complex behavioral claim (state machine, multi-step process)?
│  │  → Use Deep Investigation
│  │
│  ├─ Multi-component interaction or implicit protocol?
│  │  → Use Deep Investigation
│  │
│  └─ Performance or runtime-only behavior?
│     → Mark for Manual Testing
│
└─ Step 3: Record Verification
   │
   ├─ Evidence trail: files examined, symbols verified, method used
   ├─ Confidence level: certain → exploring
   ├─ Status: verified | contradicted | requires_review
   └─ Proposed change (if contradicted)
```

---

## Method 1: Canonical Source Verification

**Confidence**: `certain` to `very_high`

### When to Use

- API claims when OpenAPI/Swagger spec exists
- Message format claims when protobuf/GraphQL schema exists
- Configuration claims when JSON Schema exists
- Command claims when Makefile/mise.toml exists

### Process

1. **Find canonical source**:
   ```bash
   # Use Glob to find specification files
   Glob pattern: **/openapi.{yaml,json}
   Glob pattern: **/*.proto
   Glob pattern: **/*.graphql
   Glob pattern: **/schema.json
   ```

2. **Read specification**:
   - Use `Read` tool to load the spec file
   - Parse the relevant section

3. **Compare claim to spec**:
   - Does the claim match the canonical definition exactly?
   - Are all fields/parameters/methods mentioned?

4. **Record result**:
   - **Verified**: Claim matches spec exactly
   - **Contradicted**: Claim differs from spec
   - **Confidence**: `certain` (specs are authoritative)

### Example

**Claim**: "POST /api/sessions creates a new session and returns JSON with `session_id` and `status`"

**Process**:
```
1. Glob pattern: **/openapi.yaml
2. Found: api/openapi.yaml
3. Read: api/openapi.yaml
4. Check /api/sessions POST endpoint definition
5. Verify response schema has session_id and status fields
6. Result: Verified (confidence: certain)
```

---

## Method 2: Symbolic Analysis

**Confidence**: `high` to `certain`

### When to Use

- Structural claims (types, interfaces, packages)
- Simple behavioral claims (method signatures, error types)
- Configuration constants and defaults
- Direct dependencies between components

### Tools

- `mcp__serena__find_symbol`: Locate specific symbols by name
- `mcp__serena__get_symbols_overview`: Get file-level symbol overview
- `mcp__serena__find_referencing_symbols`: Find where a symbol is used
- `mcp__serena__search_for_pattern`: Search for patterns in code

### Process

#### For Structural Claims

1. **Locate the symbol**:
   ```
   mcp__serena__find_symbol(
     name_path="TypeName",
     relative_path="pkg/module/",  # if known
     include_body=false,  # just need existence
     depth=1  # include methods/fields
   )
   ```

2. **Verify structure**:
   - Check exported fields/methods match claim
   - Verify type hierarchy (implements interface, etc.)

3. **Record result**:
   - Confidence: `certain` (structure is definitive)

#### For Simple Behavioral Claims

1. **Locate the function/method**:
   ```
   mcp__serena__find_symbol(
     name_path="Class/Method",
     relative_path="pkg/module/file.go",
     include_body=true  # need to read implementation
   )
   ```

2. **Read implementation**:
   - Check logic matches documented behavior
   - Verify error handling, return values

3. **Record result**:
   - Confidence: `high` to `certain` depending on code clarity

#### For Configuration Claims

1. **Search for the constant**:
   ```
   mcp__serena__search_for_pattern(
     substring_pattern="ENVIRONMENT_VARIABLE_NAME",
     restrict_search_to_code_files=true
   )
   ```

2. **Verify default value**:
   - Check the assigned value in code
   - Look for fallback logic

3. **Record result**:
   - Confidence: `certain` (constants are definitive)

### Example

**Claim**: "The `Manager` type implements the `SessionProvider` interface"

**Process**:
```
1. find_symbol(name_path="Manager", include_body=false, depth=1)
   → Found: pkg/session/manager.go, line 45
   → Methods: Create, Delete, Get, List

2. find_symbol(name_path="SessionProvider", include_body=true)
   → Found: pkg/session/interfaces.go, line 12
   → Interface methods: Create, Delete, Get, List

3. Compare method signatures
   → All match

4. Result: Verified (confidence: certain)
```

---

## Method 3: Deep Investigation

**Confidence**: `medium` to `high`

### When to Use

- Complex behavioral claims (state machines, multi-step workflows)
- Multi-component interactions
- Implicit protocols or contracts
- Claims requiring understanding of system-wide behavior

### Tools

- `mcp__zen__analyze`: Comprehensive code analysis
- `mcp__zen__debug`: Root cause analysis for behavior
- `mcp__zen__thinkdeep`: Multi-stage investigation

### Process

1. **Initial symbolic analysis**:
   - Use serena tools to narrow down relevant files/symbols
   - Get a high-level understanding of components involved

2. **Choose zen tool**:
   - **analyze**: For understanding architecture and patterns
   - **debug**: For tracing specific behavior through call chains
   - **thinkdeep**: For complex hypothesis testing

3. **Execute investigation**:
   ```
   mcp__zen__analyze(
     step="Analyzing session state machine transitions",
     step_number=1,
     total_steps=3,
     next_step_required=true,
     findings="Initial findings...",
     model="gpt-5",
     analysis_type="architecture",
     relevant_files=[...],  # from symbolic analysis
     confidence="exploring"
   )
   ```

4. **Build evidence trail**:
   - Document each verification step
   - Record files examined and findings
   - Track confidence as investigation progresses

5. **Record result**:
   - Confidence: typically `high` (depends on code complexity)

### Example

**Claim**: "Sessions progress through states: CREATED → SPAWNING → ACTIVE → TERMINATING → CLEANED"

**Process**:
```
1. Symbolic analysis:
   - search_for_pattern(substring_pattern="CREATED.*SPAWNING")
   - Found state constants in pkg/session/states.go
   - find_referencing_symbols for each state

2. Deep investigation:
   - Use mcp__zen__analyze to trace state transitions
   - Step 1: Map all state transition code
   - Step 2: Verify each documented transition exists
   - Step 3: Check for undocumented transitions

3. Findings:
   - All documented transitions exist
   - Found additional FAILED state not mentioned
   - State machine matches claim with exception

4. Result: Contradicted (confidence: high)
   Proposed change: Add FAILED state to documentation
```

---

## Method 4: Manual Testing

**Confidence**: `low` to `medium`

### When to Use

- Runtime-only behavior (performance, resource usage)
- Integration with external services
- Flaky or timing-dependent behavior
- Claims requiring actual execution

### Process

1. **Mark claim for manual testing**:
   - Status: `requires_review`
   - Reason: "Requires runtime execution to verify"
   - Confidence: `low` (cannot verify statically)

2. **Provide testing guidance**:
   - Suggest specific tests to run
   - List preconditions and expected outcomes
   - Note any risks or dependencies

3. **Record result**:
   - User must perform manual verification
   - Update claim based on test results

### Example

**Claim**: "The service handles 10,000 requests per second"

**Process**:
```
1. Assessment: Performance claim, requires load testing
2. Status: requires_review
3. Guidance: "Run load test with 10k RPS using tool X"
4. Result: Manual testing required (confidence: low)
```

---

## Confidence Scoring Guidelines

After verification, assign confidence based on:

| Confidence | When to Use |
|-----------|-------------|
| `certain` | Canonical source verification, or simple symbolic verification with no ambiguity |
| `almost_certain` | Symbolic verification of clear code with minor uncertainty |
| `very_high` | Deep investigation with strong evidence, or symbolic analysis of moderately complex code |
| `high` | Deep investigation with good evidence, or symbolic analysis requiring interpretation |
| `medium` | Investigation with some gaps, or code requiring significant interpretation |
| `low` | Weak evidence, complex code with multiple interpretations, or partial verification |
| `exploring` | Just starting investigation, no findings yet |

---

## Evidence Trail Requirements

Every verification must document:

1. **Verification method**: canonical | symbolic | deep_investigation | manual
2. **Files examined**: Full paths to all files read
3. **Symbols verified**: Specific types, functions, methods checked
4. **Evidence spans**: Line ranges of relevant code
5. **Findings**: What was discovered during verification
6. **Confidence**: Score with justification

### Example Evidence Trail

```yaml
claim_id: "README-042"
doc_path: "README.md"
content: "Manager implements SessionProvider interface"
verification_method: "symbolic"
evidence:
  files:
    - "pkg/session/manager.go"
    - "pkg/session/interfaces.go"
  spans:
    - {file: "pkg/session/manager.go", line_start: 45, line_end: 120}
    - {file: "pkg/session/interfaces.go", line_start: 12, line_end: 25}
  symbols_verified:
    - "Manager"
    - "SessionProvider"
findings: "Manager type has all required methods with matching signatures. Verified: Create, Delete, Get, List."
status: "verified"
confidence: "certain"
risk_tier: "auto_fix"  # if any corrections needed
```

---

## Optimization Tips

1. **Batch related claims**: Verify all claims about a component together to share context
2. **Use symbolic analysis first**: Narrow scope before deep investigation
3. **Cache repository index**: Reuse Pass 0 results across multiple claims
4. **Prefer static verification**: Avoid manual testing when possible
5. **Group by verification method**: Process all canonical source verifications together
