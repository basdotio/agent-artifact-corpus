# Speck Knowledge Reference

Detailed interpretation rules, file state classification, error formats, and artifact parsing guidelines.

**Referenced from**: SKILL.md

---

## Table of Contents

1. [Section Annotation Patterns](#section-annotation-patterns)
2. [File State Classification](#file-state-classification)
3. [Error Message Format](#error-message-format)
4. [Artifact-Specific Interpretation](#artifact-specific-interpretation)
   - [spec.md Interpretation](#specmd-interpretation)
   - [plan.md Interpretation](#planmd-interpretation)
   - [tasks.md Interpretation](#tasksmd-interpretation)
5. [Template Comparison Workflow](#template-comparison-workflow)
6. [Edge Case Handling](#edge-case-handling)

---

## Section Annotation Patterns

Templates and artifact files use inline annotations to indicate section requirements:

**Mandatory Sections**:
- Pattern: `## Section Name *(mandatory)*`
- Detection regex: `/\*\(mandatory\)\*/`
- Examples:
  - `## User Scenarios & Testing *(mandatory)*`
  - `## Requirements *(mandatory)*`
  - `## Success Criteria *(mandatory)*`

**Conditional Sections**:
- Pattern: `## Section Name *(include if...)*`
- Detection regex: `/\*(include if|OPTIONAL).*\*/`
- Example: `### Key Entities *(include if feature involves data)*`

**HTML Comments for Guidance**:
Templates include HTML comments with three types:

1. **ACTION REQUIRED** - User must fill this section:
   ```markdown
   <!--
     ACTION REQUIRED: Fill them out with the right requirements.
   -->
   ```

2. **IMPORTANT** - Critical guidance:
   ```markdown
   <!--
     IMPORTANT: User stories should be PRIORITIZED as user journeys.
   -->
   ```

3. **General purpose** - Section explanation:
   ```markdown
   <!--
     This section explains what the feature should accomplish.
   -->
   ```

**Extracting Section Purposes**:
When user asks "What goes in Requirements?":
1. Load relevant template ($PLUGIN_ROOT/templates/spec-template.md)
2. Find the Requirements section
3. Extract HTML comment immediately following the header
4. Parse first line as section purpose
5. Present to user with actionable guidance

---

## File State Classification

Every artifact file (spec.md, plan.md, tasks.md) can be in one of five states:

### State 1: MISSING
- **Detection**: File does not exist at expected path
- **Severity**: ERROR
- **Recovery Guidance**:
  - spec.md missing → "Run `/speck.specify 'Feature description'` to create spec"
  - plan.md missing → "Run `/speck.plan` to generate plan"
  - tasks.md missing → "Run `/speck.tasks` to generate tasks"

### State 2: EMPTY
- **Detection**: File exists but has no content (size 0 bytes or only whitespace)
- **Severity**: ERROR
- **Recovery Guidance**: Same as MISSING

### State 3: MALFORMED
- **Detection**: File has content but cannot be parsed (invalid markdown, corrupted structure)
- **Severity**: WARNING
- **Behavior**: Extract whatever partial information is available
- **Recovery Guidance**: "File structure is invalid. Manually fix markdown or regenerate with appropriate `/speck.*` command"

### State 4: INCOMPLETE
- **Detection**: Valid structure but missing mandatory sections
- **Severity**: WARNING
- **Behavior**: Parse available sections, warn about missing mandatory sections
- **Recovery Guidance**:
  - spec.md incomplete → "Run `/speck.clarify` to add missing sections"
  - plan.md incomplete → "Run `/speck.clarify` for missing research, or continue filling manually"
  - tasks.md incomplete → "Complete tasks or regenerate with `/speck.tasks`"
- **Report**: List missing mandatory sections, calculate completeness percentage

### State 5: VALID
- **Detection**: All mandatory sections present, proper structure
- **Severity**: SUCCESS
- **Behavior**: Extract and return all data

**Graceful Degradation**:
For MALFORMED and INCOMPLETE states:
1. Extract maximum possible information from available sections
2. Return completeness score (0-100%)
3. List warnings with specific missing/broken sections
4. Provide actionable recovery guidance
5. Continue answering user's question with partial data + warnings

**Common Malformation Patterns**:
- Missing H1 title
- Unclosed code blocks
- Broken cross-file references
- Invalid subsection formats (e.g., acceptance scenarios missing Given/When/Then)
- Inconsistent heading levels (H2 → H4 skip)

---

## Error Message Format

When reporting issues with files, use this structured format:

```
[SEVERITY]: Brief Title
┌─────────────────────────────────────────┐
│ Descriptive explanation of issue        │
├─────────────────────────────────────────┤
│ Context: What's missing/wrong           │
├─────────────────────────────────────────┤
│ Recovery: Specific command or action    │
└─────────────────────────────────────────┘

[Optional: Available data summary]
[Optional: Completeness percentage]
```

**Severity Levels**:
- **ERROR**: Blocking issue (file missing, empty, cannot parse)
- **WARNING**: Non-blocking issue (missing optional sections, malformed subsections)
- **INFO**: Informational (unresolved [NEEDS CLARIFICATION] markers)

**Example Error Messages**:

**Missing File**:
```
ERROR: Spec Not Found
┌──────────────────────────────────────────────────┐
│ spec.md not found at specs/006-feature/          │
├──────────────────────────────────────────────────┤
│ Recovery: Run /speck.specify "Feature desc"      │
└──────────────────────────────────────────────────┘
```

**Incomplete Spec**:
```
WARNING: Incomplete Specification
┌──────────────────────────────────────────────────┐
│ spec.md is missing mandatory sections            │
├──────────────────────────────────────────────────┤
│ Missing:                                         │
│ - Success Criteria (mandatory)                   │
│ - User Scenarios & Testing (mandatory)           │
├──────────────────────────────────────────────────┤
│ Recovery: Run /speck.clarify to fill sections    │
└──────────────────────────────────────────────────┘

Found: 5 functional requirements, 2 key entities
Completeness: 40% (2/5 mandatory sections)
```

---

## Artifact-Specific Interpretation

### spec.md Interpretation

**H1 Title Format**:
- Pattern: `# Feature Specification: [FEATURE NAME]`
- Extract feature name from H1

**Metadata Block**:
Located immediately after H1, typically:
```
**Feature Branch**: 005-speck-skill
**Created**: YYYY-MM-DD
**Status**: Draft/Reviewed/Approved
**Input**: Natural language feature description
```

**Multi-Repo Metadata** (optional, only in child repos):
```
**Parent Spec**: [007-multi-repo-monorepo-support](link)
```
- Indicates this feature builds on or extends a parent feature
- Used in multi-repo child repositories to reference shared parent spec
- Link typically points to spec in shared specs/ directory

**Mandatory Sections**:

#### User Scenarios & Testing
- Section header: `## User Scenarios & Testing *(mandatory)*`
- Contains H3 subsections following pattern: `### User Story N - [Title] (Priority: PN)`
- Priority values: P1 (highest) through P4 (lowest)
- Each user story includes:
  - Independent test description
  - Acceptance scenarios (Given/When/Then format)
- Edge cases subsection: `### Edge Cases`

#### Requirements
- Section header: `## Requirements *(mandatory)*`
- Subsection: `### Functional Requirements`
  - Format: `**FR-XXX**: Description`
  - Numbering: FR-001, FR-002, etc.
- Conditional subsection: `### Key Entities *(include if feature involves data)*`
  - Lists data entities with fields and relationships

#### Success Criteria
- Section header: `## Success Criteria *(mandatory)*`
- Subsection: `### Measurable Outcomes`
  - Format: `**SC-XXX**: Metric/measurement`
  - Must be measurable (percentages, counts, yes/no)
  - Technology-agnostic (no implementation details)

**Optional Sections**:
- `## Clarifications`: Q&A from `/speck.clarify` sessions
- `## Assumptions`: Project assumptions
- `## Edge Cases`: Already mentioned in User Scenarios

**[NEEDS CLARIFICATION] Markers**:
- Pattern: `[NEEDS CLARIFICATION]` or `[NEEDS CLARIFICATION: specific question]`
- Indicates unresolved questions in spec
- Guidance: "Run `/speck.clarify` to resolve clarifications before planning"

**Handling Missing/Incomplete spec.md**:
- **MISSING**: "Spec not found. Run `/speck.specify 'Feature description'`"
- **EMPTY**: Same as MISSING
- **MALFORMED**: Extract partial sections, warn about structure issues
- **INCOMPLETE**: List missing mandatory sections with completeness percentage

**Graceful Degradation Example**:
If spec.md has Requirements but missing Success Criteria:
- Return available FR-XXX items
- Warn: "Missing Success Criteria (mandatory) - 66% complete"
- Suggest: "Run `/speck.clarify` to add Success Criteria"

---

### plan.md Interpretation

**H1 Title Format**:
- Pattern: `# Implementation Plan: [FEATURE]`

**Metadata Block**:
```
**Branch**: feature-branch-name
**Date**: YYYY-MM-DD
**Spec**: [spec.md](spec.md)
**Input**: Feature specification from /specs/NNN-feature/spec.md
```

**Mandatory Sections**:

#### Summary
- Section header: `## Summary`
- Concise description of primary requirement + technical approach
- Typically 2-3 sentences

#### Technical Context
- Section header: `## Technical Context`
- Fields (in table or list format):
  - **Language/Version**: Programming language and version
  - **Primary Dependencies**: Key libraries/frameworks
  - **Storage**: Database or file-based storage approach
  - **Testing**: Testing strategy
  - **Target Platform**: Runtime environment
  - **Performance Goals**: Latency, throughput, etc.
  - **Constraints**: Technical limitations
  - **Scale/Scope**: Expected size/complexity

**Explaining Scope Boundaries**:
When user asks "What's in scope?" or "What's out of scope?":
- Extract `## In Scope` and `## Out of Scope` sections (if present)
- If missing, extract from Summary or Technical Context constraints
- Explain decision rationale

#### Constitution Check
- Section header: `## Constitution Check`
- References constitutional principles from `$PLUGIN_ROOT/memory/constitution.md`
- Format per principle:
  ```
  ### Principle N: [Name]
   **PASS/VIOLATION** - Explanation
  ```
- If violations exist, must have justification in Complexity Tracking section

#### Project Structure
- Section header: `## Project Structure`
- Two subsections:
  - `### Documentation (this feature)`: Shows specs/NNN-feature/ structure
  - `### Source Code (repository root)`: Shows actual implementation file structure

**Optional Sections**:

#### Phase 0: Research & Unknowns
- Contains research tasks with `[NEEDS CLARIFICATION]` markers
- Output artifact: research.md

#### Phase 1: Design & Contracts
- Prerequisites: research.md complete
- Subsections:
  - `### Data Model (data-model.md)`
  - `### API Contracts (contracts/)`
  - `### Quickstart Guide (quickstart.md)`

#### Complexity Tracking
- Only present if Constitution Check has violations
- Justifies complexity with decision rationale

**Parsing Constitution Check**:
Extract principle references:
- Principle number and name
- PASS/VIOLATION status
- Justification text

**Handling Missing/Incomplete plan.md**:
- **MISSING**: "Plan not found. Run `/speck.plan` to generate implementation plan"
- **INCOMPLETE**: Detect missing phases or [NEEDS CLARIFICATION] markers
  - If Phase 0 incomplete: "Run `/speck.clarify` to resolve research unknowns"
  - If Phase 1 incomplete: "Continue filling design artifacts or run `/speck.clarify`"

---

### tasks.md Interpretation

**YAML Frontmatter**:
Located at top of file:
```yaml
---
description: "Task list for [Feature Name] implementation"
---
```

**H1 Title Format**:
- Pattern: `# Tasks: [FEATURE NAME]`

**Header Block**:
Immediately after H1:
```
**Input**: Design documents from /specs/NNN-feature/
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/
```

**Format Explanation Section**:
- Section header: `## Format: [ID] [P?] [Story] Description`
- Explains task ID format:
  - `[ID]`: Task identifier (T001, T002, IMPL-001, etc.)
  - `[P]`: Optional parallelizable marker (can run concurrently)
  - `[Story]`: User story label (US1, US2, etc.)
  - Description with exact file paths

**Task Format Parsing**:
Each task follows checkbox format:
```markdown
- [ ] T001 [P] [US1] Description of task with file path
```

**Task Status Detection**:
- Unchecked `- [ ]`: **pending**
- Checked `- [x]` or `- [X]`: **completed**
- Text marker "in_progress": **in_progress** (if explicitly marked)

**Phase Structure**:
Tasks are grouped into phases:
- `## Phase 1: Setup` (or Phase N: Purpose Name)
- Each phase ends with **Checkpoint**: marker explaining completion criteria

**Common Phases**:
1. **Phase 1: Setup** - Project initialization
2. **Phase 2: Foundational** - Blocking prerequisites
3. **Phase 3+: User Stories** - One phase per user story (US1, US2, etc.)
4. **Final Phase: Polish** - Cross-cutting concerns, validation

**Task Dependencies**:
- Section: `## Dependencies & Execution Order`
- Explains:
  - Phase dependencies (which phases must complete before others)
  - User story dependencies (which stories are independent)
  - Within-story task order
  - Parallel opportunities ([P] tasks)

**Identifying Available Work**:
When user asks "What can I work on next?":
1. Find current phase (first phase with pending tasks)
2. Check dependencies are satisfied
3. List pending tasks with satisfied dependencies
4. If task marked [P], note it can run in parallel with other [P] tasks

**Example Task Counting**:
User: "How many tasks are completed?"
- Count all lines matching `- [x]` or `- [X]`
- Count total tasks (all lines matching `- [ ]` or `- [x]`)
- Calculate percentage: completed / total

**Handling Missing/Incomplete tasks.md**:
- **MISSING**: "Tasks not found. Run `/speck.tasks` to generate task breakdown"
- **INCOMPLETE**: Count pending vs completed tasks, identify current phase

---

## Template Comparison Workflow

When user asks to compare files against templates (e.g., "Does my spec follow the template?"):

### Step 1: Load Both Files
1. Identify file type from user query (spec/plan/tasks)
2. Load template: `$PLUGIN_ROOT/templates/{type}-template.md`
3. Load actual file: `specs/NNN-feature/{type}.md`

### Step 2: Extract Sections
Parse both files to extract:
- Section headers (H2, H3)
- Section annotations (mandatory/optional markers)
- Section order (sequence of headers)

**Section Extraction Pattern**:
- Use regex: `/^(#{1,6})\s+(.+?)\s*(\*\(.*?\))?$/`
- Capture: heading level, title, annotation

### Step 3: Structural Comparison
Compare extracted sections:

**Check for Missing Mandatory Sections**:
- For each template section with `*(mandatory)*` annotation
- Verify actual file has matching H2/H3 header
- If missing, mark as ERROR

**Check for Out-of-Order Sections**:
- Compare section sequence between template and actual
- If major sections (H2) are reordered, mark as WARNING
- Minor reordering of H3 subsections is acceptable

**Check for Wrong Heading Levels**:
- Verify H2 sections in template remain H2 in actual
- Verify H3 subsections remain H3
- If levels mismatch (H2 → H3 or vice versa), mark as WARNING

### Step 4: Content Completeness
Check section content:

**Detect Empty Sections**:
- Section header present but no content between header and next header
- Mark as WARNING: "Section [name] is empty"

**Detect Placeholder Markers**:
- Search for: `[FEATURE]`, `[DATE]`, `TODO`, `[NEEDS CLARIFICATION]`
- Mark as INFO or WARNING depending on marker type

### Step 5: Extract Section Purposes
For each section in template:
- Find HTML comment immediately after header or within section
- Parse comment for ACTION REQUIRED, IMPORTANT keywords
- Extract first line as section purpose
- Store purpose for explanation if user asks

### Step 6: Generate Comparison Report

**Report Format**:
```
Template Comparison: specs/NNN-feature/spec.md vs spec-template.md
┌──────────────────────────────────────────────────────────────┐
│ Structure: [% match]                                         │
├──────────────────────────────────────────────────────────────┤
│ ✅ Present: User Scenarios & Testing, Requirements           │
│ ❌ Missing: Success Criteria (mandatory)                     │
│ ⚠️  Empty: Assumptions (optional, but header present)        │
│ ⚠️  Out of order: Edge Cases (expected after Requirements)   │
├──────────────────────────────────────────────────────────────┤
│ Completeness: 80% (4/5 mandatory sections)                  │
├──────────────────────────────────────────────────────────────┤
│ Recommendations:                                             │
│ 1. Add ## Success Criteria *(mandatory)* section            │
│ 2. Fill Assumptions section or remove empty header          │
│ 3. Move Edge Cases after Requirements                       │
└──────────────────────────────────────────────────────────────┘
```

**Calculate Completeness Percentage**:
- Count mandatory sections present in actual file
- Divide by total mandatory sections in template
- Multiply by 100

**Specific Fix Suggestions**:
For each issue:
- **Missing mandatory section**: "Add ## [Section Name] *(mandatory)* section"
- **Empty section**: "Fill [Section Name] with content or remove header"
- **Wrong order**: "Move [Section Name] to appear after [Previous Section]"
- **Placeholder markers**: "Replace [FEATURE] with actual feature name"

### Step 7: Explain Section Purposes
If user asks "What should go in [Section Name]?":
1. Load template for file type
2. Find the section header
3. Extract HTML comment
4. Present purpose and guidelines:
   ```
   Purpose of Success Criteria section:
   "Define measurable outcomes that indicate feature completion. Each criterion should have a specific metric (SC-001, SC-002, etc.) and be technology-agnostic."

   Guidelines:
   - Use format: **SC-XXX**: Description
   - Must be measurable (percentages, counts, yes/no)
   - No implementation details
   ```

### Template Version Tolerance
When comparing files to templates:
- **Ignore**: Minor formatting differences (extra whitespace, comment style variations)
- **Focus on**: Structural completeness (mandatory sections present)
- **Warn but don't error**: If template has new sections not in user's file (template may have been updated)
- Explain: "Template includes new optional section [Name]. Consider adding if relevant."

---

## Edge Case Handling

### Non-Existent Feature References
User references feature that doesn't exist:
1. List all available features in `specs/` directory
2. Use Levenshtein distance to suggest similar features (typo tolerance):
   - Distance ≤ 2: "Did you mean [feature]?"
   - Distance > 2: List all features
3. Explain matching rules: "Use full name (005-speck-skill), number (005), or partial name (skill)"

**Example**:
```
User: "Tell me about feature 006"
Response:
  Feature "006" not found in specs/

  Did you mean:
  - 005-speck-skill (Speck Workflow Skill)

  Available features:
    001-speck-core-project
    002-claude-plugin-packaging
    005-speck-skill

  Tip: Use full name (e.g., "005-speck-skill") or just number ("005").
```

### Invalid File Type Requests
User asks about file type that doesn't exist:
```
User: "Show me the architecture.md for feature 005"
Response:
  File type "architecture.md" is not a standard Speck artifact.

  Valid file types:
  - spec.md: Feature specification
  - plan.md: Implementation plan
  - tasks.md: Task breakdown
  - research.md: Phase 0 research (if exists)
  - data-model.md: Entity definitions (if exists)
  - contracts/: API specifications (if exists)

  Did you mean plan.md (contains architecture decisions)?
```

### Ambiguous Feature Names
Multiple features match partial name:
```
User: "What's in the auth spec?"
Response:
  Multiple features match "auth":
  - 003-user-auth: User Authentication System
  - 012-auth-tokens: OAuth Token Management

  Which one? Please specify by number (003 or 012) or full name.
```

### Multi-Feature Conversation Handling
User discusses multiple features in one session:
1. Track recently mentioned features (last 5)
2. When user asks question without explicit feature reference:
   - Check current context (most recent feature)
   - If context is clear, use it
   - If ambiguous (2+ features mentioned recently), ask for clarification

**Example**:
```
User: "Compare the requirements between 003 and 005"
[System stores both features in context]

User: "What about the success criteria?"
Response: "Which feature? You recently mentioned 003-user-auth and 005-speck-skill."
```

### Malformed File Graceful Degradation
File exists but has parsing issues:
1. Attempt to extract partial information:
   - Parse individual sections independently
   - Skip unparseable sections but continue with others
2. Report what was successfully extracted
3. Warn about issues:
   ```
   ⚠️ WARNING: File Partially Malformed
   ┌──────────────────────────────────────────────────┐
   │ specs/004-feature/spec.md has structural issues  │
   ├──────────────────────────────────────────────────┤
   │ Successfully extracted:                          │
   │ - User Scenarios (2 stories)                     │
   │ - Requirements (5 functional requirements)       │
   │                                                  │
   │ Could not parse:                                 │
   │ - Success Criteria (unclosed code block)         │
   ├──────────────────────────────────────────────────┤
   │ Partial data follows. Fix markdown errors.       │
   └──────────────────────────────────────────────────┘

   Available Requirements:
   FR-001: ...
   FR-002: ...
   ```
