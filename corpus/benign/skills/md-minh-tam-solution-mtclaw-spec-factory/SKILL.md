---
name: spec-factory
description: Generate structured specifications from natural language requirements. Governance Rail #1.
version: 1.0.0
---

# Spec Factory — Governance Rail #1

## When This Skill Activates

- User sends `/spec` command
- User asks to "create a spec", "write requirements", "generate a user story"
- PM SOUL receives a requirements-related request

## Output Format

Generate a JSON specification following this schema:

```json
{
  "spec_version": "1.0.0",
  "title": "Short descriptive title",
  "narrative": {
    "as_a": "role",
    "i_want": "feature/capability",
    "so_that": "business value"
  },
  "acceptance_criteria": [
    {
      "scenario": "Happy path",
      "given": "precondition",
      "when": "action",
      "then": "expected result"
    }
  ],
  "bdd_scenarios": [
    "Feature: Feature Name\n  Scenario: Scenario Name\n    Given precondition\n    When action\n    Then expected result"
  ],
  "risks": [
    {
      "description": "risk description",
      "probability": "low|medium|high",
      "impact": "low|medium|high",
      "mitigation": "mitigation plan"
    }
  ],
  "technical_requirements": ["requirement 1", "requirement 2"],
  "dependencies": [],
  "priority": "P0|P1|P2|P3",
  "estimated_effort": "S|M|L|XL"
}
```

## Process Steps

1. **Clarify** (if input is vague):
   - Ask 1-2 targeted questions maximum
   - Do NOT ask more than 2 questions — generate best-effort spec instead

2. **Generate**:
   - Create spec JSON following the schema above
   - Use Vietnamese for narrative if user wrote in Vietnamese
   - Use BDD format (GIVEN/WHEN/THEN) for acceptance criteria
   - Include at least 2 acceptance criteria (happy path + error case)
   - Include at least 1 risk assessment
   - Include technical requirements if the request implies technical constraints

3. **Present**:
   - Show formatted summary to user (not raw JSON)
   - Format: Title, Narrative, Acceptance Criteria list, Risks
   - Ask: "Approve, modify, or discard?"

4. **Record**:
   - On approval: Save spec as evidence (write_file to workspace)
   - Link to trace_id for audit trail
   - System assigns SPEC-YYYY-NNNN ID automatically

## BDD Format Reference

Follow SDLC 6.1.1 Specification Standard:

```gherkin
GIVEN [initial context]
  AND [additional context if needed]
WHEN [action or trigger]
  AND [additional action if needed]
THEN [expected outcome]
  AND [additional outcome if needed]
```

## Boundaries

- This skill generates SPECS only — not code, not designs, not test plans
- If user asks for implementation → delegate to @coder
- If user asks for architecture → delegate to @architect
- If user asks for test cases → delegate to @tester

## Vietnamese Support

- Input in Vietnamese → output in Vietnamese
- Input in English → output in English
- Mixed → follow user's primary language
