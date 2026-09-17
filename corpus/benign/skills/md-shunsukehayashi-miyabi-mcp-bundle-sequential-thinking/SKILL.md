---
name: sequential-thinking
description: Structured reasoning tools for complex problem analysis with observation, hypothesis, analysis, and conclusion steps. Use when analyzing complex problems, debugging difficult issues, or making important decisions.
allowed-tools: Read, Write
mcp_tools:
  - "think_step"
  - "think_branch"
  - "think_summarize"
---

# Sequential Thinking Skill

**Version**: 1.0.0
**Purpose**: Structured reasoning for complex problem analysis

---

## Triggers

| Trigger | Examples |
|---------|----------|
| Analyze | "analyze problem", "think through", "問題分析" |
| Debug | "debug this", "investigate issue", "調査" |
| Decide | "help me decide", "evaluate options", "判断支援" |
| Reason | "reason about", "think step by step", "段階的に考える" |

---

## Integrated MCP Tools

| Tool | Purpose |
|------|---------|
| `think_step` | Record a reasoning step |
| `think_branch` | Create alternative thinking branch |
| `think_summarize` | Summarize thinking session |

---

## Step Types

| Type | Purpose | Example |
|------|---------|---------|
| `observation` | Gather facts | "The error occurs at startup" |
| `hypothesis` | Form theory | "Configuration may be incorrect" |
| `analysis` | Evaluate | "Testing hypothesis against logs" |
| `conclusion` | Final result | "Root cause identified as X" |
| `question` | Open question | "What is the expected behavior?" |

---

## Workflow: Problem Analysis

### Phase 1: Observation

#### Step 1.1: Gather Facts
```
Use think_step with:
- thought: "Observed: [specific observation]"
- type: "observation"
- confidence: 0.9 (high certainty)
```

#### Step 1.2: Document Context
```
Multiple think_step calls for each fact:
- System state
- Error messages
- Recent changes
- User reports
```

### Phase 2: Hypothesis Formation

#### Step 2.1: Form Hypotheses
```
Use think_step with:
- thought: "Hypothesis: [potential cause]"
- type: "hypothesis"
- confidence: 0.5 (initial guess)
```

#### Step 2.2: Alternative Hypotheses
```
Use think_branch to explore:
- Different root causes
- Alternative explanations
- Edge cases
```

### Phase 3: Analysis

#### Step 3.1: Test Hypotheses
```
Use think_step with:
- thought: "Testing: [method and result]"
- type: "analysis"
- confidence: [adjusted based on evidence]
```

#### Step 3.2: Eliminate Options
```
Use analysis steps to:
- Confirm or refute each hypothesis
- Document evidence
- Adjust confidence levels
```

### Phase 4: Conclusion

#### Step 4.1: Draw Conclusions
```
Use think_step with:
- thought: "Conclusion: [final determination]"
- type: "conclusion"
- confidence: 0.9 (based on evidence)
```

#### Step 4.2: Summarize Session
```
Use think_summarize with:
- sessionId: Current session
- includeAlternatives: true
```

---

## Branching Strategy

### When to Branch
- Multiple valid hypotheses
- Need to explore alternatives
- Complex decision with trade-offs

### Branch Usage
```
Use think_branch with:
- sessionId: Current session
- branchName: "alternative-approach"
- fromStep: Step number to branch from
```

---

## Confidence Levels

| Level | Value | Meaning |
|-------|-------|---------|
| Certain | 0.9-1.0 | Strong evidence, verified |
| Likely | 0.7-0.9 | Good evidence, probable |
| Possible | 0.5-0.7 | Some evidence, uncertain |
| Unlikely | 0.3-0.5 | Weak evidence |
| Doubtful | 0.0-0.3 | Little to no evidence |

---

## Example Session

```
1. [observation] Error: "Connection refused" on port 5432
2. [observation] PostgreSQL service status: stopped
3. [hypothesis] Database service crashed
4. [hypothesis] Port conflict with another service
5. [analysis] Checking service logs... no crash, clean shutdown
6. [analysis] Checking port usage... no conflict
7. [conclusion] Service was manually stopped, needs restart
```

---

## Best Practices

✅ GOOD:
- Start with observations
- Form multiple hypotheses
- Document evidence for/against
- Update confidence as you learn

❌ BAD:
- Jump to conclusions
- Ignore contradicting evidence
- Single hypothesis bias
- Skip documentation

---

## Checklist

- [ ] Problem clearly stated
- [ ] Facts gathered (observations)
- [ ] Multiple hypotheses formed
- [ ] Evidence documented
- [ ] Alternatives explored (branches)
- [ ] Conclusion supported by evidence
