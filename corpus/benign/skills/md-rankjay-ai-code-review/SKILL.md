---
name: code-review
description: "Invoke when AI needs to evaluate code quality during ANY task - not just during explicit /review. Provides the thinking framework for detecting AI-slop and assessing maintainability."
---

# Code Review Skill

Provides the thinking framework for evaluating code quality. This skill guides HOW to assess code, while the `/review` command defines WHAT to output.

## Relationship to /review Command

- **This skill**: Guides AI thinking when evaluating code (detection patterns, assessment criteria)
- **`/review` command**: User-invoked workflow that runs the formal post-generation checklist

Use this skill whenever you need to assess code quality, even during implementation or exploration.

## When to Use

Automatically invoke when:

- AI is generating or modifying code and needs to self-assess
- Evaluating whether existing code follows good patterns
- Deciding if a proposed change introduces AI-slop
- User asks about code quality without explicit `/review`
- Making judgment calls about maintainability or architecture fit

## AI-Slop Indicators

Watch for these red flags:

### 1. Maintainability Issues

- Solutions that work but can't be modified easily
- Code that requires deep understanding to change
- Tight coupling between unrelated components
- God objects or functions doing too much

### 2. Architectural Misfit

- Patterns that function but don't fit the established architecture
- Inconsistent with patterns in ai-context.md
- Creates new patterns when existing ones should be used
- Violates service boundaries

### 3. Unexplainable Code

- Code that passes tests but can't be explained
- Complex logic without clear reasoning
- Magic numbers or strings without documentation
- Unclear variable or function names

### 4. Unnecessary Complexity

- Accidental complexity masquerading as essential
- Over-engineered solutions to simple problems
- Premature optimization
- Abstractions that don't simplify

### 5. Architectural Drift

- **The OAuth.js + OAuth2.js + auth-utils.js pattern**
- Multiple files solving the same problem differently
- Duplicate logic with slight variations
- Sedimentary layers of abandoned approaches

### 6. Mixed Concerns

- Business logic mixed with infrastructure
- Auth logic mixed with business logic
- Presentation logic in data layer
- Multiple responsibilities in one component

## Review Process

### Step 1: Check Against ai-context.md

- [ ] Follows architectural principles?
- [ ] Uses established patterns?
- [ ] Avoids listed anti-patterns?
- [ ] Respects service boundaries?
- [ ] Consistent with naming conventions?

### Step 2: Verify Essential vs Accidental Complexity

- [ ] Is complexity justified by the problem?
- [ ] Could this be simpler?
- [ ] Are we preserving technical debt?
- [ ] Is this "easy" or "simple"?

### Step 3: Assess Maintainability

- [ ] Can someone else modify this in 6 months?
- [ ] Are dependencies clear?
- [ ] Is error handling complete?
- [ ] Are edge cases covered?

### Step 4: Check for "Easy" vs "Simple"

**Easy** = Adjacent, within reach, frictionless to add
**Simple** = One responsibility, no entanglement, understandable

- [ ] Did we choose simple over easy?
- [ ] Is this the simplest solution that works?
- [ ] Have we avoided premature complexity?

### Step 5: Ownership Test

Can the developer:

- [ ] Explain how it works to a junior engineer?
- [ ] Identify essential vs accidental complexity?
- [ ] Modify it confidently if requirements change?
- [ ] Debug it at 3am without internet?

If any answer is "no", they don't own the code yet.

## Output Format

For each concern found, provide:

```markdown
## [PASS/CONCERN/FAIL]: [Category]

**Location**: [file:line]

**Issue**: [specific problem]

**Why it matters**: [impact on maintainability/architecture]

**Recommendation**: [how to fix]

**Code snippet**:
[show the problematic code]

**Suggested fix**:
[show better approach]
```

## Severity Levels

**FAIL** - Must fix before shipping:

- Security vulnerabilities
- Violates critical architectural principles
- Creates unmaintainable code
- Significant architectural drift

**CONCERN** - Should fix, but can ship with plan:

- Minor pattern deviations
- Suboptimal but functional
- Technical debt that's acknowledged
- Could be refactored later

**PASS** - Good to ship:

- Follows all patterns
- Maintainable and clear
- Essential complexity only
- Well-tested and documented

## Integration with Workflow

This skill provides the **evaluation methodology** that supports:

- The `/review` command (explicit review workflow)
- Self-assessment during code generation
- Quality checks during any implementation task

**Key distinction**: This skill helps AI think about code quality. The `/review` command produces the formal checklist output.

## Recommendations

Based on findings, suggest:

### If all PASS

- Update ai-context.md if new patterns emerged
- Proceed to commit

### If CONCERN

- Document as technical debt
- Create follow-up task
- Add to ai-context.md "Common Pitfalls"
- Proceed to commit with acknowledgment

### If FAIL

- Stop before commit
- Refactor to address issues
- Re-run review after fixes
- Update plan if architectural changes needed

## Patterns to Add to ai-context.md

If you discover:

- New anti-patterns to avoid
- Successful patterns to replicate
- Architectural decisions worth documenting
- Common pitfalls to flag

Suggest adding them to `.ai/ai-context.md` for future reference.

## Why This Matters

"The code might work perfectly and still be AI-slop."

Slop isn't about bugs. It's about:

- Solutions that work but aren't maintainable
- Patterns that function but don't fit the architecture
- Code that passes tests but can't be explained
- Complexity that wasn't necessary
