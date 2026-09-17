# skillmaxxer-3000

**Name**: skillmaxxer-3000
**Purpose**: Intelligently architect Claude Skills with appropriate structure based on purpose and requirements
**Type**: Meta-skill (builds other skills)
**Status**: Production Ready
**Version**: 4.0
**Archetype**: Complex/Interview (this skill uses its own framework)

---

## TABLE OF CONTENTS

**Quick Start (New Users Start Here):**
- [Quick Start Guide](#quick-start) - 8-step process to build a skill

**Core Workflow:**
- [Specification](#specification) - What this skill does and doesn't do
- [Input Schema](#input-schema) - What you need to provide
- [Output Schema](#output-schema) - What you'll receive
- [Process](#process) - Step-by-step workflow

**Quality & Validation:**
- [Guardrails](#guardrails) - Safety rules and failure modes
- [Scaffold Validation](#scaffold-validation) - Completeness checklist
- [Meta-Validation](#meta-validation-architecture-quality-rubric) - Score recommendations

**Reference:**
- [Examples](#examples) - 6 worked examples across archetypes
- [Advanced Patterns](#advanced-patterns-conditional) - Optional advanced structures
- [Self-Documentation](#meta-about-this-skill) - How this skill was built

---

## QUICK START

**IMPORTANT DISCLAIMER:**
By using this skill, you agree to use it at your own risk. Generated skills are templates requiring customization and review before production use. Always test thoroughly and validate outputs meet your quality standards.

---

**To use this skill:**

1. **Tell me what you want to build:** "I want a skill that [does X]"
2. **Choose mode:** Create new skill OR evaluate existing skill
3. **Answer 7-12 discovery questions** (7 core + up to 5 adaptive based on your answers)
4. **Review my recommendation** (I'll show JSON metadata + narrative explanation)
5. **Verify completeness** with validation checklist (all promised elements present?)
6. **Score my recommendation** with quality rubric (target: 8+/10)
7. **I'll generate working scaffold** with [CUSTOMIZE] markers
8. **Fill in domain knowledge** and test

**Example opening:**
- "I want to build a skill that takes blog posts and makes them conversational"
- "Help me design a skill for quarterly campaign planning"
- "Evaluate my existing content-humanizer skill"

**Ready? Tell me what skill you want to build or evaluate.**

---

## [SECTION: SPECIFICATION]

### Purpose

**What this skill is FOR:**
- Designing well-structured Claude Skills that match their purpose
- Evaluating existing skills and recommending improvements
- Recommending appropriate architecture (Simple/Complex/Lightweight) based on task requirements
- Generating working scaffolds with justified structural elements
- Encoding best practices from top-tier skill design patterns

**What this skill is NOT for:**
- Generating complete skill content (you provide domain knowledge)
- Writing prompts without structure or validation
- Creating one-size-fits-all templates

### Users

**Who uses this:**
- Anyone building Claude Skills for personal or team use
- Users who want structured, maintainable skills (not ad-hoc prompts)
- People transitioning from "clever prompts" to "production-ready workflows"

**User constraints:**
- May not know advanced skill patterns
- Want recommendations, not forced decisions
- Need working templates (not just theory)

### Canonical Workflow

This skill follows **The skillmaxxer Process™** (stable across all uses):

**Mode 1: Create New Skill**
1. **Discovery** - Interview user with 7-10 targeted questions
2. **Recommendation** - Analyze answers, recommend archetype + structural elements
3. **Justification** - Explain WHY each recommendation matters for THIS skill
4. **Generation** - Create working scaffold with templates + placeholders
5. **Handoff** - Mark customization points, user fills in domain knowledge

**Mode 2: Evaluate Existing Skill**
1. **Analysis** - Read existing skill, check structural completeness
2. **Diagnosis** - Identify missing elements, improvement opportunities
3. **Recommendation** - Suggest specific improvements with justification
4. **Generation** - Create improved version as `[skill-name]-v2/` (preserves original)
5. **Comparison** - Show what changed and why

**The workflow is fixed. The recommendations vary based on answers/analysis.**

### Dependencies

**Required knowledge:**
- Basic understanding of Claude Skills (what they are, how they're invoked)
- Clear idea of what task the skill should accomplish

**Optional references:**
- `references/templates/` - Archetype templates (Simple, Complex, Lightweight)
- `references/decision-logic.md` - Q&A → Structure mapping logic
- `references/examples/` - Example validation scripts (Python)
- Decision logic (Q&A → Structure mapping) - See Step 2 recommendation table

### Non-Goals

This skill will NOT:
- Write domain-specific content for you (you provide that)
- Force complex structure on simple tasks
- Create skills without user confirmation
- Generate proprietary/confidential examples (all examples are generalized)

---

## [SECTION: INPUT SCHEMA]

**Required:**
- User's intended skill purpose (1-2 sentence description)
- Answers to 7 core discovery questions

**Optional:**
- Additional context about organizational values, repeat-use patterns, high-stakes considerations
- Existing skill examples to reference

**Constraints:**
- Skill purpose must be specific enough to determine structure
- User must answer core questions (can skip optional context questions)

---

## [SECTION: OUTPUT SCHEMA]

**IMPORTANT PATTERN: Dual-Format Output**

All generated skills should include BOTH formats:
1. **Machine-Readable** (JSON block) - Structured data for automation/parsing
2. **Human-Readable** (Narrative) - Explanation and context

**Example pattern:**
```json
{
  "archetype": "Simple/Transformational",
  "score": "8/10",
  "status": "approved",
  "changes_made": ["removed hedging", "varied rhythm", "added connectors"],
  "facts_preserved": ["95%", "January 2025", "Claude Sonnet 4.5"]
}
```

**Narrative explanation:**
"I've transformed your content using the Simple archetype. Score improved from 5/10 to 8/10 by removing hedging language, varying sentence rhythm, and adding natural connectors. All facts preserved (including the 95% statistic, January 2025 date, and Claude Sonnet 4.5 reference)."

### skillmaxxer-3000 Outputs

**Narrative (Human-Readable):**
- Architecture recommendation with justification
- Directory structure visualization
- Explanation of each recommended element

**Machine-Readable #1 (Metadata JSON):**
```json
{
  "skill_name": "[user-provided]",
  "archetype": "Simple|Complex|Lightweight",
  "elements_included": [
    "PRD-style spec",
    "Schema",
    "Rubric",
    "etc."
  ],
  "elements_skipped": ["element", "reason"],
  "file_count": 5,
  "customization_points": 12
}
```

**Real-world example from actual recommendation:**
```json
{
  "skill_name": "blog-conversational-voice",
  "archetype": "Simple/Transformational",
  "confidence": "9/10",
  "elements_included": [
    "PRD-style spec",
    "Schema (JSON + narrative)",
    "8-criteria rubric",
    "Two-pass diagnostic/reconstruction system",
    "Transformation library",
    "Fact preservation rules"
  ],
  "elements_skipped": [
    {"element": "Scripts directory", "reason": "User declined automation (Q12=No)"},
    {"element": "Question bank", "reason": "Linear workflow, not multi-phase"}
  ],
  "files_to_generate": 5,
  "customization_points": 8,
  "trigger_logic": {
    "Q2": "Existing polished content",
    "Q3": "Ready-to-publish",
    "Q4": "Linear",
    "Q5": "Subjective",
    "Q6": "High variation"
  }
}
```

**Machine-Readable #2 (File System):**
```
.claude/skills/[skill-name]/
├── SKILL.md (generated template with [CUSTOMIZE] markers)
├── references/ (if recommended)
│   ├── rubric.md (if subjective quality)
│   ├── transformation-library.md (if transformation task)
│   ├── question-bank.md (if interview task)
│   └── examples.md
└── README.md (optional documentation)
```

**Required sections in generated SKILL.md:**
- Specification (Purpose, Users, Workflow, Dependencies, Non-goals)
- Input/Output Schema (with JSON + narrative pattern)
- Process (step-by-step)
- Guardrails (NEVER/ALWAYS rules + failure modes)
- Examples

**Schema Thinking Principle:**
Every skill generated should demonstrate the JSON + narrative pattern in its own output schema section, teaching by example.

---

## [SECTION: PROCESS]

### STEP 0: Mode Selection

**I will:**
Ask which mode you want to use:
1. **Create New Skill** - Build a skill from scratch
2. **Evaluate Existing Skill** - Analyze and improve an existing skill

**I show you:**
```
## Welcome to skillmaxxer-3000

What would you like to do?

1. **Create New Skill** - Design and build a new skill from scratch
   - Use when: You have a task/workflow in mind but no skill exists
   - You'll answer 7-12 discovery questions
   - I'll recommend structure and generate scaffold

2. **Evaluate Existing Skill** - Analyze an existing skill and generate improved version
   - Use when: You have a skill that's not working as expected
   - Use when: You want to add features or improve quality measurement
   - Use when: You suspect missing structural elements
   - I'll analyze completeness and recommend improvements

Choose mode (1 or 2)?
```

**If Mode 1 (Create New):** Proceed to Step 1 (Discovery Interview)

**If Mode 2 (Evaluate Existing):**

**Step 1: Get skill and improvement goals**
1. Ask for skill file path (`.claude/skills/[skill-name]/SKILL.md`)
2. **Ask: "What would you like to improve about this skill?"**

**Options:**
- [ ] **Specific concern** - "I want to improve [performance/clarity/quality measurement/specific aspect]"
- [ ] **Missing features** - "I think it needs [specific element]"
- [ ] **Full analysis** - "Analyze everything and suggest improvements"
- [ ] **Not sure** - "Help me identify what needs work"

**Step 2: Read and analyze (focused on user's goal)**

If **Specific concern**:
- Focus analysis on stated problem
- Check related structural elements
- Identify root cause
- Suggest targeted fixes

If **Missing features**:
- Verify if feature makes sense for this skill's purpose
- Recommend how to implement
- Show what changes are needed

If **Full analysis** or **Not sure**:
- Complete structural analysis:
  - Check for PRD-style spec (Purpose, Users, Non-goals)
  - Check for input/output schema (JSON + narrative)
  - Check for guardrails + failure modes
  - Score against structural completeness
  - Identify missing elements
- Prioritize improvements (critical → nice-to-have)

**Step 3: Show findings**

**I show you:**
```
## Evaluation Results

**Your goal:** [What you want to improve]

**Findings:**
🔴 Critical issues:
- [Issue 1 blocking your goal]
- [Issue 2 blocking your goal]

🟡 Recommended improvements:
- [Improvement 1 addressing your goal]
- [Improvement 2 addressing your goal]

🟢 Working well:
- [What's already good]

**Proposed changes:**
- [Specific change 1]
- [Specific change 2]

Generate improved version as `[skill-name]-v2/` (preserves original)?
```

**Step 4: Generate improvements**
- If approved → Create `[skill-name]-v2/` with improvements
- Show side-by-side comparison (what changed, why it helps your goal)
- Highlight customization points in new version

**CRITICAL SAFETY:** Evaluate mode ALWAYS creates new directory (`skill-name-v2/`), NEVER overwrites original.

---

### STEP 1: Discovery Interview

**I will:**
1. Ask 7 core questions about the skill being designed
2. Ask 0-4 adaptive questions if answers suggest advanced patterns needed
3. Capture answers and display summary for confirmation

**Core Questions (always ask):**

**Q1: Purpose**
"What should this skill do? (1-2 sentences)"

**Q2: Input Form**
"What does the user start with?"

**Options:**
- [ ] **Existing polished content** - Article, document, finished draft, clean data
  - *Example:* Blog post, published newsletter, structured dataset
- [ ] **Rough content** - Brain dump, messy first draft, scattered notes
  - *Example:* Voice memo transcript, bullet points, raw ideas
- [ ] **No content yet** - Pure creation from scratch
  - *Example:* Building strategy from zero, creating plan with no starting material
- [ ] **URL or external resource** - Website, API, external data source
  - *Example:* "Analyze this article URL", "Fetch from this API"
- [ ] **Mix of above**

**Q3: Output Form**
"What should the skill produce?"

**Options:**
- [ ] **Ready-to-publish content** - Final output, no further work needed
  - *Example:* Polished blog post, formatted email, final report
- [ ] **Structured draft** - Needs downstream processing or another skill
  - *Example:* Outline that becomes input to writer skill, structured data for formatter
- [ ] **System/tool/workflow** - Built infrastructure or automation
  - *Example:* API integration, test runner, deployment script
- [ ] **Research synthesis** - Analysis, findings, insights
  - *Example:* Competitive analysis, trend report, data summary
- [ ] **Decision/recommendation** - Actionable guidance
  - *Example:* "Use approach A because...", strategy recommendation

**Q4: Workflow Type**
"Is this a single workflow, or does it interview the user across multiple topics?"

**Options:**
- [ ] **Linear** - Single workflow from start to finish
  - *Example:* "Take blog post → make it conversational → output result"
  - *Example:* "Run tests → format results → report status"
  - User provides input, skill processes it, done

- [ ] **Multi-phase** - Interview user across multiple topics, each with approval
  - *Example:* "Phase 1: Ask about goals → Phase 2: Ask about audience → Phase 3: Ask about tactics → Assemble strategy"
  - *Example:* "Phase 1: Gather requirements → Phase 2: Design approach → Phase 3: Create implementation plan"
  - Skill asks questions, user answers, repeat per phase, then assemble final output

**Q5: Quality Measurement**
"How do you know if the output is good?"

**Options:**
- [ ] **Subjective** - Quality depends on feel, style, judgment
  - *Example:* "Does this sound conversational?" (needs scoring: 1-10 scale)
  - *Example:* "Is this engaging enough?" (needs rubric to measure)
  - *Example:* "Does this match our brand voice?" (subjective assessment)
  - → Requires scoring rubric (objective measurement for subjective quality)

- [ ] **Binary** - Quality is factual, pass/fail
  - *Example:* "Did the tests pass?" (yes or no, factual)
  - *Example:* "Does the code compile?" (works or doesn't)
  - *Example:* "Are all required fields present?" (checklist)
  - → Requires pass/fail checklist only

- [ ] **Both** - Some aspects subjective, some binary
  - *Example:* "Content must be accurate (binary) AND engaging (subjective)"
  - → Requires both rubric and checklist

**Q6: Output Variation**
"Will some outputs need iteration while others are one-and-done?"
- [ ] High variation (user needs approval gates and iteration loops)
- [ ] Low variation (consistent quality, streamlined validation)

**Q7: Reference Materials**
"Do you have examples, voice guides, rubrics, or other references this skill should use?"
- [ ] Yes (provide file paths or descriptions)
- [ ] No
- [ ] Will create them later

**Adaptive Questions (ask when relevant):**

**Q8: Repeat Use** (ask if skill seems reusable)
"Is this skill used repeatedly by the same person/team?"
- If yes → Recommend memory-aware patterns

**Q9: High Stakes** (ask if Q5 suggests risk)
"Does this involve high-stakes decisions (legal, financial, brand-sensitive)?"
- If yes → Recommend enhanced failure modes + fallback strategies

**Q10: Organizational Philosophy** (ask if skill is for team/company use)
"Are there organizational values or philosophy this should encode?"
- If yes → Recommend doctrine-encoded guardrails

**Q11: Self-Updating/Learning** (ask if skill improves with use)
"Should this skill adapt based on your feedback over time?"

**Options:**
- [ ] **Yes, learns from corrections** - Remember when you fix outputs and apply those fixes automatically next time
  - *Example:* "You change phrase A to phrase B → skill uses B automatically going forward"
  - → Recommend adaptive architecture with correction tracking

- [ ] **Yes, builds preference library** - Accumulate your specific style/quality preferences over time
  - *Example:* "You consistently prefer formal tone → skill defaults to formal automatically"
  - → Recommend configuration versioning with preference storage

- [ ] **No, static skill** - Works the same way every time, no evolution needed
  - → Standard skill structure, no adaptive components

**When to use self-updating (decision guide):**

✅ **Good candidates for self-updating:**
- Skills used 10+ times with same user
- Quality improves through accumulated corrections (voice, style, preferences)
- User makes same types of corrections repeatedly
- Output variation is high and learning reduces it over time
- Examples: voice transformation, content scoring, template generation

❌ **Poor candidates for self-updating:**
- One-off or infrequent use (< 5 times)
- Binary pass/fail quality (no learning opportunity)
- Requirements change frequently (learning becomes obsolete)
- Multiple users with conflicting preferences
- Examples: test runners, simple validation, data extraction

**If uncertain:** Start without self-updating. After 5+ uses, evaluate if adding it would reduce iteration time.

**If yes to Q11:** Recommend self-updating architecture
- `config/` or `corrections/` directory with JSON logs
- Mechanism to update rules/preferences based on user feedback
- Version tracking (changelog showing skill evolution)

**Q12: Automated Validation** (ask if Q5 = Subjective)
"Do you want optional Python scripts for automated quality checks?"

**Options:**
- [ ] **Yes, automated checks** - Scan for banned phrases, calculate metrics, verify facts
  - *Example:* "Run script before publishing to catch hedging language automatically"
  - *Example:* "Automatically calculate readability scores to verify improvement"
  - → Recommend scripts/ directory with validation tools (brand_voice_validator.py, readability_metrics.py, fact_preservation_check.py, rubric_scorer.py)

- [ ] **No, manual validation** - I'll check quality myself
  - *Example:* "I prefer to evaluate conversational tone manually"
  - → Skip scripts/ directory, keep manual validation process only

**If yes to Q12:** Recommend scripts/ directory in generated skill with:
- `brand_voice_validator.py` - Brand voice requirements validation
- `readability_metrics.py` - Calculate sentence variance, word count, metrics
- `fact_preservation_check.py` - Verify facts unchanged (if transformation task)
- `rubric_scorer.py` - Auto-calculate objective rubric criteria
- `README.md` - How to run scripts and interpret results

**Note:** Example scripts are in `references/examples/` (this skill), but generated skills put scripts in their own `scripts/` directory.

**I show you:**
```
## Discovery Summary

**Skill purpose**: [1-2 sentence description]

**Answers:**
- Input form: [existing/rough/none/URL/mix]
- Output form: [ready-to-publish/structured-draft/system/research/decision]
- Workflow type: [linear/multi-phase]
- Quality measurement: [subjective/binary/both]
- Output variation: [high/low]
- Reference materials: [yes/no/later]

[If answered:]
- Repeat use: [yes/no]
- High stakes: [yes/no]
- Organizational philosophy: [description]
- Self-updating: [yes/no]
- Automated validation: [yes/no]

Confirm these answers before I recommend structure?
```

---

### STEP 1.5: Skill-Splitting Detection (Adaptive)

**I will check:** Should this be ONE skill or TWO?

**Important: Default to single skills. Only split when there's a compelling reason.**

Skills can handle significant complexity - they're flexible prompts, not rigid code. Splitting creates operational overhead:
- User must run two skills sequentially
- Intermediate output must be managed
- More files to maintain

**When splitting IS justified:**
1. **Reusability across contexts** - Intermediate output used in multiple different workflows (not just this one)
2. **Different execution timing** - Phases happen hours/days/weeks apart
3. **Failure isolation critical** - One phase fails often, need to preserve work from other
4. **Multiple users/handoffs** - Different people run different phases
5. **Scale/token limits** - Combined skill would exceed context limits

**When splitting is NOT justified:**
1. Phases always run sequentially in same session - Keep as one multi-phase skill
2. "Clean architecture" without operational benefit - Over-engineering
3. Intermediate output only used once - No reusability gain
4. Combined skill is maintainable - Don't split for theoretical purity

**Split into TWO skills when:**
- Q4 = Multi-phase AND user describes complex transformation after discovery
- Q2 = "No content" (discovery phase) AND Q3 = "Ready-to-publish" (transformation phase)
- Skill purpose describes both "gather requirements" AND "transform output"

**Example patterns that suggest splitting:**

**Pattern 1: API Integration Builder**
- *As described:* "Interview user about API requirements, then generate integration code"
- *Should be TWO:*
  - Skill 1: `api-requirements-gatherer` (Complex/Interview) - Asks discovery questions, outputs structured spec
  - Skill 2: `api-code-generator` (Simple/Transformational) - Takes spec, generates code

**Pattern 2: Strategy Execution Plan**
- *As described:* "Ask about business goals across multiple areas, then create detailed action plan"
- *Should be TWO:*
  - Skill 1: `strategy-discovery` (Complex/Interview) - Multi-phase questions, outputs strategic framework
  - Skill 2: `action-plan-builder` (Simple/Transformational) - Takes framework, generates executable plan

**Pattern 3: Research-to-Content**
- *As described:* "Research topic systematically, then write polished article"
- *Should be TWO:*
  - Skill 1: `research-synthesizer` (Complex/Interview) - Gathers information across sources, outputs structured findings
  - Skill 2: `article-writer` (Simple/Transformational) - Takes findings, writes polished article

**Pattern 4: Data Collection → Automation (with different execution timing)**
- *As described:* "Interview user about complex form data, then fill out form with validation"
- *When to split:* Data collection happens in one session (user conversation), but form-filling happens later (automated batch process or after legal review)
- *Example scenario:* Compliance forms where legal team must review collected data before submission, or batch processing where you collect data from 10 clients then process all forms overnight
- *Should be TWO:*
  - Skill 1: `data-gatherer` (Complex/Interview) - Collects information systematically, outputs validated JSON
  - Skill 2: `form-processor` (Lightweight) - Takes JSON, fills form, handles errors
- *Why justified:* Different timing, different error recovery needs, data reusable for multiple forms
- *Counter-example (keep as ONE):* If you collect data and immediately fill form in same session → Complex skill with two phases is fine

**When NOT to split (keep as single multi-phase skill):**

❌ **"Multi-step approval workflow"** - "Gather requirements → generate draft → iterate based on feedback"
- Keep as ONE Complex skill with phases
- Intermediate requirements doc not reused elsewhere
- User wants seamless flow from questions to output
- Splitting creates unnecessary handoff overhead

❌ **"Research then decide"** - "Research solutions → build decision matrix"
- Keep as ONE Complex skill
- Research data only used for this decision
- No execution timing gap
- Combined skill is maintainable and logical

❌ **"Iterative refinement"** - "Diagnose issues → fix them"
- Keep as ONE Simple skill with two-pass system (diagnostic → reconstruction)
- This is standard two-pass pattern, not two skills
- Diagnostic step is intermediate, not final output
- User wants seamless improvement, not manual handoff

**Key insight:** Skills can handle multi-phase workflows, two-pass systems, and complex logic. Only split when there's operational benefit (reusability, timing, handoffs), not for architectural purity.

**If split detected, I show you:**
```
## Skill-Splitting Recommendation

Based on your description, this might work better as **TWO skills**:

**Skill 1: [discovery-skill-name]** (Complex/Interview)
- Purpose: [discovery/gathering phase]
- Output: Structured data/framework for next skill

**Skill 2: [transformation-skill-name]** (Simple/Transformational)
- Purpose: [transformation/creation phase]
- Input: Output from Skill 1
- Output: [final deliverable]

**Why split:**
- Each skill has single, clear purpose
- Skill 1 output can be reused with different transformations
- Skill 2 can work with manually created input (not just from Skill 1)
- Easier to maintain, test, and improve individually

**Options:**
1. Build TWO skills (recommended) - I'll generate both scaffolds
2. Build ONE combined skill - Proceed with original approach
3. Build just ONE of them - Choose which phase you need most

Which approach?
```

**If no split needed:** Proceed to Step 2 (Archetype Recommendation)

---

### STEP 2: Archetype Recommendation

**I will:**
1. Analyze answers using decision logic (see `references/decision-logic.md`)
2. Recommend archetype: Simple, Complex, or Lightweight
3. Recommend structural elements to include
4. Explain WHY each recommendation matters for THIS skill

**Archetype Selection Logic:**

**Simple/Transformational** (recommend when):
- Q4 = Linear workflow
- Q2 = Existing or rough content
- Q3 = Ready-to-publish or structured draft
- Q5 = Subjective or Both

**Use cases**: Content transformation, voice refinement, format conversion, quality improvement

**Complex/Interview** (recommend when):
- Q4 = Multi-phase discovery
- Q2 = No content or mix
- Q3 = Structured draft or decision
- Q6 = High variation

**Use cases**: Content creation from scratch, discovery-driven workflows, multi-section assembly

**Lightweight** (recommend when):
- Q4 = Linear
- Q5 = Binary only
- Q6 = Low variation
- Simple execution task

**Use cases**: Command execution, simple automation, binary validation tasks

**Structural Element Recommendations:**

| Condition | Recommend | Why |
|-----------|-----------|-----|
| **All skills** | PRD-style spec | Complete documentation, clear boundaries |
| **All skills** | Schema-defined inputs/outputs | Type safety, clear contracts (JSON + narrative pattern) |
| **All skills** | Organizational doctrine guardrails | Encode "how we do things here" |
| **All skills** | Failure mode detection + fallbacks | Graceful uncertainty handling |
| Q5 = Subjective | 8-criteria rubric + scoring | Objective measurement for variable quality |
| Q6 = High variation | Two-pass diagnostic/reconstruction | User needs iteration control |
| Q5 = Binary only | Pass/fail checklist | Don't over-engineer |
| Q2 = Existing + transformation | Fact preservation rules + transformation library | Protect source accuracy |
| Q4 = Multi-phase | Question bank + assembly structure | Systematic discovery |
| Q4 = Linear + complex | Decomposition-first pattern | Break down → confirm → execute |
| Q8 = Repeat use | Memory-aware patterns | Save agreements, name configs |
| Q7 = 3+ references | Organized references/ directory | Maintainable knowledge base |
| Q12 = Yes | scripts/ directory with validation tools | Automated quality checks |
| Q11 = Self-updating | learning/ or feedback/ directory with logs | Skill improves from user corrections |

---

**Self-Updating/Learning Architecture (Optional, Advanced)**

**When to recommend:**
- Q11 = Yes (skill should learn from repeated use)
- User mentions "evolving skill" or "adaptive workflow"
- Skill involves quality improvement based on user feedback

**Typical structure:**
```
.claude/skills/[skill-name]/
├── SKILL.md
├── config/                            # Evolving configuration
│   ├── preferences.json              # User-specific settings that change over time
│   └── rules.json                    # Quality rules (updated from corrections)
├── history/                           # Historical data
│   ├── corrections.json              # User corrections logged with timestamp
│   └── outcomes.json                 # What worked vs what didn't
└── updates/
    ├── changelog.md                  # Version history of rule changes
    └── update-logic.md               # How corrections become new rules
```

**Alternative structure (for detection-based skills):**
```
.claude/skills/[skill-name]/
├── SKILL.md
├── detection/                         # What to detect
│   ├── avoid-list.json               # Things to flag or remove
│   └── keep-list.json                # User-approved exceptions
├── corrections/                       # How to fix
│   ├── replacements.json             # Before → after pairs
│   └── examples.md                   # Worked corrections with context
└── evolution/
    ├── user-feedback.json            # Accumulated user corrections
    └── version.json                  # Tracks skill evolution over time
```

**How it works:**
1. User runs skill, identifies issue in output
2. User provides correction: "Change X to Y" or "This is wrong, use Z instead"
3. Skill logs correction with context
4. Next run: skill applies previous corrections automatically
5. Tracks evolution over time (what changed, when, why)

**Key principle:** Skill adapts to user's specific needs through repeated interaction.

**Example JSON Schemas:**

**`config/preferences.json` schema:**
```json
{
  "version": "1.0",
  "last_updated": "2026-01-15T10:30:00Z",
  "tone_preferences": {
    "formality": "conversational",
    "sentence_length": "varied",
    "avoid_phrases": ["Moreover", "Furthermore", "In conclusion"]
  },
  "structural_preferences": {
    "max_paragraph_length": 4,
    "use_bullet_points": true,
    "connector_density": "moderate"
  },
  "quality_thresholds": {
    "min_rubric_score": 8,
    "require_manual_review_below": 7
  }
}
```

**`corrections/replacements.json` schema:**
```json
{
  "version": "1.0",
  "replacements": [
    {
      "id": "001",
      "date": "2026-01-15T10:30:00Z",
      "pattern": "utilize",
      "replacement": "use",
      "context": "Formality reduction",
      "auto_apply": true
    },
    {
      "id": "002",
      "date": "2026-01-16T14:20:00Z",
      "pattern": "In order to",
      "replacement": "To",
      "context": "Wordiness reduction",
      "auto_apply": true
    }
  ]
}
```

**`history/corrections.json` schema:**
```json
{
  "version": "1.0",
  "corrections": [
    {
      "timestamp": "2026-01-15T10:30:00Z",
      "input_hash": "abc123",
      "correction_type": "phrase_replacement",
      "original": "In light of the fact that",
      "corrected": "Because",
      "user_feedback": "Too formal",
      "applied_to_rules": true
    }
  ]
}
```

**When NOT to recommend:**
- Static skills (same process every time)
- One-off use (not worth learning overhead)
- Binary tasks (nothing to learn from)

---

**Scripts/ Directory (Optional, for Automation)**

**When to recommend:**
- Q12 = Yes (user wants automated validation)
- Q5 = Subjective (quality requires measurement)
- Skill involves mechanical validation (banned phrases, fact checking, metrics)

**When NOT to recommend:**
- Lightweight skills (binary pass/fail)
- Pure conversation/guidance skills
- One-off use (not worth automation overhead)

**Typical scripts/ structure:**
```
.claude/skills/[skill-name]/
└── scripts/
    ├── brand_voice_validator.py   # Validate brand voice requirements
    ├── readability_metrics.py     # Calculate sentence variance, word count, etc.
    ├── fact_preservation_check.py # Verify facts unchanged (if transformation)
    ├── rubric_scorer.py           # Auto-calculate rubric scores
    └── README.md                  # How to run scripts
```

**Example script purposes:**
- **brand_voice_validator.py** - Validate content against brand voice requirements (terminology, tone markers, prohibited terms)
- **readability_metrics.py** - Calculate metrics (sentence length variance, connector density, specificity ratio)
- **fact_preservation_check.py** - Extract numbers/names from before/after, verify match
- **rubric_scorer.py** - Automate scoring for objective criteria (rhythm, punctuation variety)

**Example script implementations:**

**`brand_voice_validator.py` example:**
```python
#!/usr/bin/env python3
"""
Validate marketing content against brand voice requirements.
Business use case: Ensure AI-generated content maintains brand consistency.
"""

import sys
from collections import defaultdict

# Customize for your brand voice
BRAND_CONFIG = {
    "required_terms": {
        "product_mentions": ["YourProduct", "The Platform"],
        "value_props": ["efficiency", "streamlined", "automated"],
        "tone_markers": ["practical", "actionable", "proven"]
    },
    "prohibited_terms": [
        "game-changing", "revolutionary", "synergy", "leverage"
    ],
    "voice_attributes": {
        "conversational": ["we", "you", "let's"],
        "direct": ["here's", "simply", "just"],
        "expert": ["proven", "tested", "validated"]
    }
}

def analyze_content(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read().lower()

    findings = {"score": 0, "issues": []}

    # Check required terms (30 points)
    for category, terms in BRAND_CONFIG["required_terms"].items():
        found = [t for t in terms if t.lower() in content]
        findings["score"] += (len(found) / len(terms)) * 10

    # Check prohibited terms (30 points deduction)
    prohibited = [t for t in BRAND_CONFIG["prohibited_terms"] if t.lower() in content]
    if not prohibited:
        findings["score"] += 30
    else:
        findings["issues"].extend([f"Prohibited: {t}" for t in prohibited])

    # Check voice attributes (40 points)
    for attr, markers in BRAND_CONFIG["voice_attributes"].items():
        if any(m in content for m in markers):
            findings["score"] += 13.3

    return round(findings["score"], 1), findings["issues"]

if __name__ == '__main__':
    score, issues = analyze_content(sys.argv[1])
    print(f"Brand Voice Score: {score}/100")

    if score >= 80:
        print("✓ Strong brand alignment")
        sys.exit(0)
    elif score >= 60:
        print("⚠ Moderate alignment - review recommended")
        if issues:
            print("Issues:", ", ".join(issues))
        sys.exit(0)
    else:
        print("✗ Weak alignment - revision needed")
        if issues:
            print("Issues:", ", ".join(issues))
        sys.exit(1)
```

**`readability_metrics.py` example:**
```python
#!/usr/bin/env python3
"""Calculate readability metrics for content."""

import re
import sys
from collections import Counter

def calculate_metrics(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Split into sentences
    sentences = re.split(r'[.!?]+', content)
    sentences = [s.strip() for s in sentences if s.strip()]

    # Calculate sentence length variance
    word_counts = [len(s.split()) for s in sentences]
    avg_length = sum(word_counts) / len(word_counts) if word_counts else 0
    variance = sum((x - avg_length) ** 2 for x in word_counts) / len(word_counts)

    # Count connector words
    connectors = ['and', 'but', 'so', 'yet', 'because', 'however']
    connector_count = sum(content.lower().count(c) for c in connectors)

    return {
        'sentence_count': len(sentences),
        'avg_sentence_length': round(avg_length, 1),
        'sentence_variance': round(variance, 1),
        'connector_count': connector_count,
        'connector_density': round(connector_count / len(sentences), 2)
    }

if __name__ == '__main__':
    metrics = calculate_metrics(sys.argv[1])
    print("Readability Metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")
```

**Important:**
- Scripts are OPTIONAL automation, not core skill requirements
- Skill must work WITHOUT scripts (manual validation)
- Scripts speed up validation, don't replace human judgment
- Python is default (widely available, good for text processing)

---

**I show you:**

**Machine-Readable (Recommendation Metadata):**
```json
{
  "skill_name": "[user-provided]",
  "archetype_recommended": "Simple|Complex|Lightweight",
  "confidence": "8/10",
  "elements_included": [
    "PRD-style spec",
    "Schema (JSON + narrative)",
    "8-criteria rubric",
    "Two-pass system",
    "Transformation library"
  ],
  "elements_skipped": [
    {"element": "Scripts directory", "reason": "User declined automation"}
  ],
  "files_to_generate": 5,
  "customization_points": 12,
  "trigger_logic": {
    "Q4": "Linear",
    "Q5": "Subjective",
    "Q6": "High variation"
  }
}
```

**Narrative (Architecture Recommendation):**

```
## Skill Architecture Recommendation

**Archetype**: [Simple/Complex/Lightweight]

**Why this structure:**
- [Reasoning based on Q1-Q12 answers]
- [Example: "Linear workflow + existing content → transformed output = Simple archetype"]

**Recommended elements:**
✅ [Element 1] - [Why it matters for THIS skill]
✅ [Element 2] - [Why it matters for THIS skill]
❌ [Element skipped] - [Why not needed]

**Directory structure:**
```
.claude/skills/[skill-name]/
├── SKILL.md
├── references/
│   └── [recommended files]
```

**Options:**
1. **Use recommended structure** - Proceed with archetype above
2. **Override recommendation** - Tell me which archetype you prefer instead
3. **Custom process** - You have a specific workflow in mind (describe it)

Choose option (1/2/3)?
```

**If Option 3 (Custom Process) chosen:**

**I ask:**
"Describe your specific workflow step-by-step (e.g., 'Step 1: X, Step 2: Y, Step 3: Z')"

**I will:**
1. Listen to your custom process description
2. Create SKILL.md structure following YOUR steps (not forcing archetype)
3. Still add universal elements (PRD spec, schema, guardrails, failure modes)
4. Map your steps to "STEP 1", "STEP 2", etc. in SKILL.md
5. Recommend supporting elements based on your process complexity

**I show you:**
```
## Custom Process Scaffold

**Your workflow:**
1. [Your Step 1]
2. [Your Step 2]
3. [Your Step 3]
[etc.]

**I'll create SKILL.md with:**
- Your steps as the main process structure
- PRD-style spec (still needed for completeness)
- Input/output schema based on your first/last steps
- Guardrails tailored to your process
- [Recommended elements based on complexity]

**Recommended additions based on your process:**
✅ [Element if needed]
❌ [Element not needed]

Proceed with custom structure?
```

---

### STEP 3: Generate Scaffold

**PLAN MODE DETECTION:**
If in plan mode → Describe what I WOULD create without actually creating files:
- Show complete directory structure
- Describe each file's purpose and key sections
- Explain customization points
- Provide summary for user approval
- Wait for execution approval before creating files

**EXECUTION MODE (normal):**

**I will:**
1. Create directory structure based on recommendations
2. Generate SKILL.md from archetype template
3. Create reference file templates if recommended
4. Mark [CUSTOMIZE] sections where user adds domain knowledge
5. Include inline examples and patterns

**Generation process:**
- Load appropriate template from `references/templates/[archetype].md`
- Populate with skill-specific context from Q1-Q12
- Insert [CUSTOMIZE] markers for domain-specific content
- Add commented guidance where needed

**I show you:**
```
## Generated Scaffold

**Location**: `.claude/skills/[skill-name]/`

**Files created:**
- SKILL.md ([Simple/Complex/Lightweight] archetype template)
[If recommended:]
- references/rubric.md (8-criteria scoring template)
- references/transformation-library.md (before/after patterns)
- references/question-bank.md (discovery questions)
- references/examples.md (worked examples placeholder)
[If Q12 = Yes:]
- scripts/brand_voice_validator.py (brand voice validation)
- scripts/readability_metrics.py (metrics calculation)
- scripts/README.md (how to run scripts)

**Next: Customize these sections** (marked with [CUSTOMIZE]):
1. Line X: Add your specific [domain knowledge]
2. Line Y: Define your [validation criteria]
3. references/[file]: Write [specific content]

Scaffold ready. Would you like me to explain any section?
```

---

### STEP 4: Handoff & Customization Guidance

**I will:**
1. Highlight key customization points
2. Provide examples of what to fill in
3. Explain validation approach
4. Offer to answer questions about structure

**I show you:**
```
## Customization Checklist

**High-priority sections to fill in:**
- [ ] Purpose: Add 1-2 lines on what skill is FOR and NOT for
- [ ] Users: Describe who will use it, their constraints
- [ ] Process steps: Add domain-specific instructions
- [ ] Guardrails: Define NEVER/ALWAYS rules for your use case
- [ ] Examples: Add 2-3 worked examples showing transformation

[If subjective quality:]
- [ ] Rubric: Adapt 8 criteria to your specific quality measures

[If transformation task:]
- [ ] Transformation library: Document common before/after patterns

[If interview task:]
- [ ] Question bank: Write discovery questions for each phase

**Optional enhancements:**
- Add organizational philosophy to guardrails section
- Create presets if multiple output styles exist
- Document failure modes specific to your domain

**Testing your skill:**
1. Try running it with a real example
2. Verify output matches expectations
3. Iterate on unclear sections
4. Add examples as you use it

Skill scaffold complete!
```

---

## [SECTION: SCAFFOLD VALIDATION]

### Completeness Checklist

**Before customizing, verify you received:**

✅ **Universal elements (all skills):**
- [ ] SKILL.md with complete PRD spec (Purpose, Users, Workflow, Dependencies, Non-goals)
- [ ] Input/Output schema (JSON + narrative format demonstrated)
- [ ] Process with "I will"/"I show you" structure
- [ ] Guardrails (NEVER/ALWAYS/Failure Modes sections)
- [ ] Examples section (with placeholders if not yet filled)

✅ **Conditional elements (based on recommendation):**
- [ ] If Q5=Subjective → `references/rubric.md` exists
- [ ] If transformation task → `references/transformation-library.md` exists
- [ ] If Q4=Multi-phase → `references/question-bank.md` exists
- [ ] If Q7=3+ refs → `references/` directory organized with multiple files
- [ ] If Q12=Yes → `scripts/` directory with Python validation tools
- [ ] If Q11=Yes → `config/` or `corrections/` directory for learning
- [ ] All recommended files from Step 2 recommendation present

✅ **Usability:**
- [ ] [CUSTOMIZE] markers clearly identified in SKILL.md
- [ ] Inline guidance explains what to fill in for each marker
- [ ] File paths in recommendations match actual generated structure
- [ ] Reference files have template content or clear structure to fill in
- [ ] Directory structure matches the recommendation shown in Step 2

**Pass criteria:** All applicable boxes checked

**If incomplete:**
- Note which elements are missing
- Reference Step 2 recommendation to verify what was promised
- Request missing elements: "The recommendation included [X] but I don't see it in the scaffold"
- I'll generate the missing pieces

**Common issues:**
- Missing `references/` files that were recommended
- SKILL.md missing required sections (spec, schema, process, guardrails, examples)
- [CUSTOMIZE] markers present but no guidance on what to fill in
- Scripts recommended but `scripts/` directory not created

---

## [SECTION: GUARDRAILS]

### NEVER

**Don't force patterns:**
- Never recommend complex structure for simple tasks
- Never require scoring rubrics for binary quality tasks
- Never create heavyweight processes for one-shot execution
- Never include proprietary/confidential examples (all examples must be generalized)

**Don't skip fundamentals:**
- Never skip PRD-style specification (Purpose, Users, Non-goals)
- Never skip input/output schema definition (JSON + narrative pattern)
- Never skip failure mode consideration
- Never skip guardrails section
- Never generate skills without demonstrating dual-format output (machine + human readable)

**Don't hallucinate:**
- Never invent structural recommendations without justification
- Never claim a pattern is "best practice" without explaining why
- Never generate incomplete templates with TODO placeholders only

### ALWAYS

**Justify recommendations:**
- Always explain WHY each structural element for THIS skill
- Always tie recommendations to user's specific answers
- Always offer override options

**Provide working templates:**
- Always generate complete SKILL.md with structure
- Always mark [CUSTOMIZE] sections clearly
- Always include inline examples or guidance

**Default to simplicity:**
- When in doubt, recommend lighter structure
- When quality measurement unclear, start with binary (can upgrade later)
- When variation uncertain, start streamlined (can add iteration loops later)

**Make it shareable:**
- Always use generalized examples (not specific to one business)
- Always explain patterns in universal terms
- Always create skills others could adapt

**Respect plan mode:**
- If in plan mode: describe what WOULD be created, don't create files
- Wait for execution approval before file creation
- Show complete structure preview in plan mode

### FAILURE MODES

**When requirements underspecified:**
- Fallback: Ask clarifying questions before recommending structure
- Pattern: "I need to understand [X] before I can recommend whether to include [Y]"

**When user answers conflict:**

**Detection triggers:**
- Q5 = "Binary" BUT Q6 = "High variation" (contradiction: binary quality usually means low variation)
- Q2 = "Existing content" BUT Q4 = "Multi-phase discovery" (contradiction: discovery implies no content yet)
- Q5 = "Subjective" BUT user says "I just want pass/fail" (mixed signals on quality measurement)
- Q3 = "Ready-to-publish" BUT Q6 = "High variation" (if high variation, may not be ready-to-publish)

**Fallback:** Point out specific conflict, ask which is more accurate

**Pattern:**
"I see a potential contradiction in your answers:
- You said [answer A from Question X]
- But also said [answer B from Question Y]
- This affects whether I recommend [structural element Z]

Can you clarify which is more accurate for your use case?"

**Example 1:**
"You said quality measurement is binary (worked/didn't work), but also that output variation is high (some outputs need significant iteration). Binary quality usually means consistent, predictable results with low variation. This affects whether I recommend scoring rubrics vs simple pass/fail checklists. Which better describes your task:
1. Binary quality + low variation (simple pass/fail, streamlined)
2. Subjective quality + high variation (needs rubric + iteration loops)"

**Example 2:**
"You said input is existing polished content, but workflow is multi-phase discovery. Multi-phase discovery workflows typically start with NO content and build it through interviews. This affects the archetype recommendation. Which is more accurate:
1. You have existing content to transform (Simple/Transformational archetype)
2. You start from scratch with discovery questions (Complex/Interview archetype)"

**Example 3:**
"You said output should be ready-to-publish, but also that variation is high requiring iteration. 'Ready-to-publish' typically means consistent quality needing minimal review. High variation usually means 'structured draft' needing review/approval. Which matches your need:
1. Consistent, ready-to-publish output (streamlined validation)
2. Variable quality needing iteration (two-pass with approval gates)"

**When skill purpose too vague:**
- Example: "Make content better" (no clear definition)
- Fallback: Ask follow-up questions about what "better" means
- Pattern: "What specific aspect of content should improve? Voice/accuracy/engagement/structure?"

**When high-stakes detected:**
- Example: Legal advice, financial decisions, medical guidance
- Fallback: Add disclaimer guardrail to generated skill
- Pattern: Include "Always recommend consulting [professional] for [domain] decisions"

---

## [SECTION: META-VALIDATION - ARCHITECTURE QUALITY RUBRIC]

### How to Evaluate My Recommendations

**Use this to score whether I recommended the right structure for YOUR skill.**

**Target**: 8+ overall score = good architecture recommendation

**1. Fit to Purpose (1-10)**
- 10: Archetype perfectly matches task characteristics (Q1-Q7 answers)
- 7-9: Good fit with minor mismatches or edge cases
- 4-6: Works but feels over-engineered or under-specified
- 1-3: Wrong archetype for this task (Simple when needs Complex, etc.)

**Scoring guide:**
- Does workflow type match archetype? (Linear→Simple/Lightweight, Multi-phase→Complex)
- Does quality measurement match validation approach? (Subjective→rubric, Binary→checklist)
- Does variation match process structure? (High→two-pass, Low→streamlined)

**2. Element Justification (1-10)**
- 10: Every structural element clearly tied to specific Q&A answers with justification
- 7-9: Most elements justified, few unclear connections
- 4-6: Some elements seem arbitrary or not explained
- 1-3: No clear justification for choices, feels templated

**Scoring guide:**
- Can you trace each recommended element to a specific answer? (Q5=Subjective → rubric)
- Did I explain WHY each element matters for YOUR skill specifically?
- Are skipped elements justified? (why NOT included)

**3. Complexity Appropriateness (1-10)**
- 10: Right level of structure (not over/under-engineered for task complexity)
- 7-9: Slightly too complex or simple, but workable
- 4-6: Noticeably mismatched complexity (heavyweight for simple task or vice versa)
- 1-3: Way too heavy or light for task needs

**Scoring guide:**
- Simple task (pass/fail) → Lightweight (single file, 3-5 steps)
- Moderate task (transformation) → Simple (rubric + references)
- Complex task (discovery) → Complex (question banks + assembly)

**4. Usability of Scaffold (1-10)**
- 10: [CUSTOMIZE] markers clear, immediately usable, obvious what to fill in
- 7-9: Mostly clear, minor confusion about 1-2 sections
- 4-6: Some sections unclear what to fill in or where to start
- 1-3: Confusing, can't proceed without extensive clarification

**Scoring guide:**
- Are [CUSTOMIZE] markers paired with inline guidance?
- Do reference files have structure/examples showing what to add?
- Can you start customizing right away?

**5. Completeness (1-10)**
- 10: All promised files/sections present, matches Step 2 recommendation exactly
- 7-9: Minor elements missing (1 file or section)
- 4-6: Some expected sections absent (2-3 files or key sections)
- 1-3: Major gaps in scaffold (missing directories, incomplete SKILL.md)

**Scoring guide:**
- Check Step 2 recommendation against actual generated files
- Use Scaffold Validation Checklist (previous section)
- Verify all conditional elements present based on your Q&A answers

**6. Adherence to Answers (1-10)**
- 10: Recommendation directly follows decision logic from your Q&A answers
- 7-9: Mostly consistent with answers, minor deviations explained
- 4-6: Some contradictions between answers and recommendations
- 1-3: Doesn't match answers given (ignored Q&A logic)

**Scoring guide:**
- Q4=Linear + Q5=Subjective → Should recommend Simple, not Complex
- Q5=Binary only → Should NOT recommend rubric
- Q12=Yes → Should include scripts/ directory

**7. Actionability (1-10)**
- 10: Can immediately customize and use, clear next steps
- 7-9: Need minor clarification on 1-2 customization points
- 4-6: Significant work needed to make usable (unclear structure)
- 1-3: Can't use without major revision or re-generation

**Scoring guide:**
- Is the "Customization Checklist" (Step 4) clear and complete?
- Do you know exactly what to fill in next?
- Can you run the skill after customization?

**8. Shareability (1-10)**
- 10: Examples generalized, others can adapt, universal patterns
- 7-9: Mostly shareable, some business-specific elements
- 4-6: Too customized to one context, hard for others to adapt
- 1-3: Proprietary/confidential examples, not shareable

**Scoring guide:**
- Are examples universal (not tied to specific business)?
- Can someone outside your org understand and adapt it?
- Are patterns explained in general terms?

---

### Measurement

**Calculate your score:**
1. Score each criterion 1-10 based on guidelines above
2. Calculate average: (sum of 8 scores) / 8
3. Round to nearest 0.5

**Interpretation:**
- **8.0-10.0**: Approve recommendation, proceed with scaffold
- **6.0-7.5**: Request adjustments to specific criteria that scored low
- **Below 6.0**: Ask me to re-recommend with different approach

**If recommendation scores <8.0:**
Tell me which criteria failed (scored <7) and I'll revise:
- "Criterion 3 (Complexity) scored 5/10 - feels over-engineered for simple task"
- "Criterion 2 (Justification) scored 6/10 - unclear why rubric recommended"
- "Criterion 5 (Completeness) scored 4/10 - missing scripts/ directory that was promised"

**I will:**
- Address specific criteria that scored low
- Revise recommendation with justification
- Re-generate scaffold if needed

---

## [SECTION: MEMORY PATTERNS]

### For Repeat Users

**Configuration Naming Convention:**

Use this pattern: `[Output-Type]-[User-Identifier]-v[Version]`

**Examples:**
- `conversational-blog-acme-v1` - Conversational blog transformation for Acme Corp team
- `campaign-plan-enterprise-v2` - Campaign planning for enterprise marketing teams (2nd iteration)
- `code-review-backend-v1` - Backend code review skill for engineering team

**At end of skill generation:**

**I show you:**
```
## Working Agreements (Save for Future Use)

**Your preferences this session:**
- Preferred archetype: [Simple/Complex/Lightweight]
- Quality approach: [Subjective with rubrics / Binary with checklists]
- Tone: [Formal / Conversational / Technical]
- Length: [Concise / Standard / Comprehensive]
- Organizational philosophy: [Any values mentioned]

**Named configuration:**
"[Output-Type]-[User-Identifier]-v1"

**How to reuse this configuration:**

1. **Same skill, new input:**
   - Say: "Use [Config-Name] for [new input]"
   - I'll apply same preferences without re-asking questions

2. **Similar skill, different domain:**
   - Say: "Create skill like [Config-Name] but for [new purpose]"
   - I'll use same architecture, adapt domain

3. **Evolve configuration:**
   - After 3-5 uses, say: "Update [Config-Name] to v2"
   - I'll incorporate learned preferences into new version

**Save this as:**
- Text note in your workspace
- Memory/context for next session
- Team documentation if shared skill
```

---

## [SECTION: EXAMPLES]

### Example 1: Simple/Transformational Skill

**User request:**
"I want a skill that takes blog posts and makes them sound more conversational."

**Discovery answers:**
- Input: Existing polished content (blog posts)
- Output: Ready-to-publish content
- Workflow: Linear transformation
- Quality: Subjective (voice/style)
- Variation: High (some posts need more work)
- References: Voice guide exists

**Recommendation:**
- **Archetype**: Simple/Transformational
- **Why**: Linear workflow, transforming existing content, subjective quality → needs rubric + iteration
- **Elements**: PRD spec, schema, 8-criteria rubric, two-pass diagnostic/reconstruction, transformation library, fact preservation rules

**Generated scaffold:**
```
.claude/skills/blog-conversational-voice/
├── SKILL.md (Simple archetype with 2-pass system)
├── references/
│   ├── rubric.md (8 criteria: rhythm, connectors, specificity, voice, etc.)
│   ├── transformation-library.md (formal → conversational patterns)
│   ├── fact-preservation.md (what never changes)
│   └── voice-guide.md (link to existing guide)
```

---

### Example 2: Complex/Interview Skill

**User request:**
"I want a skill that helps me plan quarterly marketing campaigns by asking discovery questions."

**Discovery answers:**
- Input: No content (pure creation)
- Output: Structured draft (campaign plan)
- Workflow: Multi-phase discovery
- Quality: Both subjective and binary
- Variation: High (campaigns vary widely)
- References: None yet

**Recommendation:**
- **Archetype**: Complex/Interview
- **Why**: Multi-phase discovery, no starting content, needs systematic assembly → question-driven workflow
- **Elements**: PRD spec, schema, question bank (per phase), assembly structure, approval gates between phases, validation checklist

**Generated scaffold:**
```
.claude/skills/campaign-planner/
├── SKILL.md (Complex archetype with 4 phases)
├── references/
│   ├── question-bank.md (questions per phase: Goals, Audience, Tactics, Metrics)
│   ├── validation-checklist.md (campaign completeness criteria)
│   └── examples.md (placeholder for worked examples)
```

---

### Example 3: Lightweight Skill

**User request:**
"I want a skill that runs my test suite and formats the output nicely."

**Discovery answers:**
- Input: Existing system (test suite)
- Output: System execution (formatted results)
- Workflow: Linear
- Quality: Binary (tests pass/fail)
- Variation: Low (same process every time)
- References: None needed

**Recommendation:**
- **Archetype**: Lightweight
- **Why**: Binary execution, no quality variation, simple automation → don't over-engineer
- **Elements**: PRD spec (minimal), schema, pass/fail checklist only, failure modes for when tests don't run

**Generated scaffold:**
```
.claude/skills/test-runner/
└── SKILL.md (Lightweight archetype, single file, 3-5 steps)
```

---

### Example 4: API Integration Skill (Non-Content)

**User request:**
"I want a skill that helps me integrate third-party APIs by gathering requirements and generating configuration code."

**Discovery answers:**
- Input: No content (pure creation)
- Output: System/tool built (API integration code + config)
- Workflow: Multi-phase (requirements → design → code generation)
- Quality: Binary (code works or doesn't) + Subjective (code quality/style)
- Variation: High (APIs vary significantly)
- References: API best practices guide

**Skill-splitting recommendation detected:**
This should be TWO skills:
1. **api-requirements-gatherer** (Complex/Interview) - Asks about endpoints, auth, data models → outputs structured spec
2. **api-code-generator** (Simple/Transformational) - Takes spec → generates integration code

**Generated scaffolds:**
```
.claude/skills/api-requirements-gatherer/
├── SKILL.md (Complex archetype, 3 phases)
└── references/
    └── question-bank.md (Phase 1: Endpoints, Phase 2: Auth, Phase 3: Error handling)

.claude/skills/api-code-generator/
├── SKILL.md (Simple archetype)
└── references/
    ├── code-templates/ (Python, Node.js, etc.)
    └── examples.md (worked integrations)
```

---

### Example 5: Code Refactoring Skill (Non-Content)

**User request:**
"I want a skill that analyzes code and suggests refactoring improvements with rationale."

**Discovery answers:**
- Input: Existing polished content (code files)
- Output: Decision/recommendation (refactoring suggestions)
- Workflow: Linear (analyze → recommend)
- Quality: Subjective (code quality judgment)
- Variation: High (codebase complexity varies)
- References: Code style guide, architectural patterns

**Recommendation:**
- **Archetype**: Simple/Transformational
- **Why**: Linear analysis, existing code input, subjective quality assessment
- **Elements**: PRD spec, schema, 8-criteria rubric (adapted for code: complexity, readability, maintainability, testability, performance, security, documentation, adherence to patterns)

**Generated scaffold:**
```
.claude/skills/code-refactoring-advisor/
├── SKILL.md (Simple archetype with code-specific rubric)
└── references/
    ├── rubric.md (8 criteria for code quality)
    ├── refactoring-patterns.md (common improvements)
    ├── code-style-guide.md (organizational standards)
    └── examples.md (before/after refactorings)
```

---

### Example 6: Data Processing Pipeline (Non-Content)

**User request:**
"I want a skill that validates CSV data, transforms it according to rules, and outputs clean dataset."

**Discovery answers:**
- Input: Existing content (raw CSV data)
- Output: Ready-to-publish (clean dataset)
- Workflow: Linear (validate → transform → output)
- Quality: Binary (schema compliance) + Subjective (data quality thresholds)
- Variation: Low (same rules every time)
- References: Data schema, transformation rules

**Recommendation:**
- **Archetype**: Lightweight
- **Why**: Binary validation, consistent rules, low variation → streamlined process
- **Elements**: PRD spec (minimal), schema (explicit input/output data formats), pass/fail checklist, failure modes (malformed data, missing fields)

**Generated scaffold:**
```
.claude/skills/csv-data-pipeline/
├── SKILL.md (Lightweight archetype)
└── references/
    ├── data-schema.json (input/output schemas)
    └── transformation-rules.md (business logic)
```

---

## [SECTION: ADVANCED PATTERNS (CONDITIONAL)]

### Decomposition-First (for complex multi-step skills)

**When to include:** Q4 = Linear BUT task has 3+ major components

**Pattern:**
```markdown
## Process

### STEP 1: Decomposition

**I will:**
1. Break down your request into subtasks
2. Estimate difficulty/ambiguity for each
3. Show you the plan

**I show you:**
```
## Task Breakdown

1. [Subtask 1] - Difficulty: [Low/Medium/High], Ambiguity: [Low/Medium/High]
2. [Subtask 2] - Difficulty: [Low/Medium/High], Ambiguity: [Low/Medium/High]
3. [Subtask 3] - Difficulty: [Low/Medium/High], Ambiguity: [Low/Medium/High]

Approve plan or adjust?
```

### STEP 2-N: Execute Subtasks

[One section per subtask...]
```

### Memory-Aware (for repeat-use skills)

**When to include:** Q8 = Yes (repeat use expected)

**Pattern:**
```markdown
## Memory Patterns

### End of Session Summary

**I will:**
- Summarize "working agreements" (tone, length, common preferences)
- Suggest you save as notes or reuse as context next time
- Encourage naming this configuration

**I show you:**
```
## Save These Preferences

**Named configuration**: "[Skill output type] - [Your Name] v1"

**Working agreements:**
- Tone: [preference you expressed]
- Length: [preference you expressed]
- Format: [preference you expressed]

**Next session:**
- Say: "Use [Your Name] v1 configuration for [new input]"
- I'll apply same preferences without re-asking
```
```

---

## [SECTION: ADVANCED SKILL STRUCTURE]

**When all elements are recommended**, this is what a maximally advanced skill structure looks like:

```
.claude/skills/[skill-name]/
├── SKILL.md                           # Main workflow (always)
│
├── references/
│   ├── rubric.md                      # If Q5 = Subjective
│   ├── transformation-library.md     # If transformation task
│   ├── fact-preservation.md          # If transformation + accuracy critical
│   ├── question-bank.md              # If Q4 = Multi-phase
│   │
│   ├── presets/                       # If multiple output styles
│   │   ├── style-1.md                # Voice/format variation 1
│   │   ├── style-2.md                # Voice/format variation 2
│   │   └── style-3.md                # Voice/format variation 3
│   │
│   ├── examples/                      # Always recommended (2-3 minimum)
│   │   ├── success-case.md           # Clean successful transformation
│   │   ├── iteration-case.md         # Example requiring iteration
│   │   └── edge-case.md              # Challenging edge case
│   │
│   └── domain-knowledge/              # If organizational context exists
│       ├── audience-profile.md       # ICP or target user
│       ├── brand-guidelines.md       # Organizational constraints
│       └── terminology.md            # Domain-specific vocabulary
│
├── scripts/                           # If Q12 = Yes (user wants automation)
│   ├── brand_voice_validator.py      # Brand voice validation
│   ├── readability_metrics.py        # Objective metrics calculation
│   ├── fact_preservation_check.py    # Verify facts unchanged
│   ├── rubric_scorer.py              # Auto-score objective criteria
│   └── README.md                     # How to run scripts
│
├── assets/                            # If templates/images needed
│   └── output-template.md            # Structured output format
│
└── README.md                          # Optional skill documentation
```

### When Each Element Gets Included

**Always:**
- `SKILL.md` - Main workflow with PRD spec, schema, process, guardrails

**Conditional (based on Q&A):**
- `rubric.md` → Q5 = Subjective
- `transformation-library.md` → Transformation task
- `fact-preservation.md` → Transformation + accuracy critical
- `question-bank.md` → Q4 = Multi-phase
- `presets/` → User mentions "multiple styles/voices"
- `examples/` → Always (2-3 minimum)
- `domain-knowledge/` → Q8 = Repeat use + organizational context
- `scripts/` → Q12 = Yes (user wants automated validation)
- `assets/` → Templates or visual references needed

### Skill Complexity Spectrum

**Lightweight (minimal):**
```
skill-name/
└── SKILL.md
```

**Simple (moderate):**
```
skill-name/
├── SKILL.md
└── references/
    ├── rubric.md
    ├── transformation-library.md
    └── examples.md
```

**Advanced (maximum):**
```
skill-name/
├── SKILL.md
├── references/
│   ├── rubric.md
│   ├── transformation-library.md
│   ├── fact-preservation.md
│   ├── presets/ (3 files)
│   ├── examples/ (3 files)
│   └── domain-knowledge/ (3 files)
├── scripts/ (4-5 Python files)
└── README.md
```

**The structure scales with complexity. Don't over-engineer simple tasks.**

---

## [SECTION: VALIDATION & TESTING]

### How to Test Generated Skills

**Step 1: Run through process manually**
- Use the skill with a real example
- Follow each step as written
- Note any unclear instructions

**Step 2: Check for completeness (use Scaffold Validation Checklist)**

Run through this checklist systematically:

**Structure validation:**
- [ ] SKILL.md has all 5 core sections (Specification, Input/Output Schema, Process, Guardrails, Examples)
- [ ] Purpose statement includes both "FOR" and "NOT for" clauses
- [ ] Input schema defines required fields and constraints
- [ ] Output schema demonstrates JSON + narrative pattern
- [ ] Process uses "I will" / "I show you" structure consistently

**Conditional elements (based on archetype):**
- [ ] If Simple archetype → Has rubric OR checklist (based on Q5 answer)
- [ ] If Complex archetype → Has question bank OR interview structure
- [ ] If transformation task → Has transformation library or pattern examples
- [ ] If subjective quality → Has 8-criteria rubric with scoring
- [ ] If multi-phase → Has phase separation with approval gates

**Quality validation:**
- [ ] [CUSTOMIZE] markers paired with clear guidance on what to fill in
- [ ] Examples show complete before/after transformations (not just placeholders)
- [ ] Guardrails include NEVER, ALWAYS, and Failure Modes subsections
- [ ] Failure modes include specific detection triggers and fallback strategies

**Test scenarios:**
1. **Happy path test:** Run skill with ideal input, verify expected output structure
2. **Edge case test:** Try unclear/ambiguous input, verify failure mode handling
3. **Iteration test:** If two-pass system, verify diagnostic → reconstruction flow works
4. **Reference test:** If uses references/, verify skill correctly accesses and applies them

**Step 3: Verify structure matches intent**
- Does archetype fit the task? (Simple/Complex/Lightweight)
- Are structural elements justified?
- Is anything over-engineered or under-specified?
- Use Architecture Quality Rubric to score recommendation

**Step 4: Iterate**
- Fill in [CUSTOMIZE] sections with real domain knowledge
- Run skill again with another example
- Refine based on results

### Success Criteria

A successful skill scaffold:
- ✅ Clear purpose and boundaries (what it IS and ISN'T for)
- ✅ Schema-defined inputs and outputs
- ✅ Step-by-step process with "I will" / "I show you" format
- ✅ Guardrails appropriate to domain
- ✅ Failure modes addressed
- ✅ Working examples (or clear placeholders)
- ✅ [CUSTOMIZE] markers where user adds domain knowledge
- ✅ Can be used immediately after customization
- ✅ Scores 8+ on Architecture Quality Rubric
- ✅ Passes Scaffold Validation Checklist

---

## [SECTION: META - ABOUT THIS SKILL]

### Self-Documentation

**This skill's archetype:** Complex/Interview

**Why Complex/Interview:**
- Uses multi-phase discovery (7-12 questions with adaptive branching)
- Starts with no content (user describes skill idea, I gather requirements)
- Outputs structured draft (scaffold with [CUSTOMIZE] markers)
- High variation (every skill is different based on answers)
- Quality measurement is both (binary: completeness checklist + subjective: quality rubric)

**This skill follows its own framework:**
- PRD-style specification ✅
- Schema-defined inputs/outputs (JSON + narrative) ✅
- Multi-phase process (Mode selection → Discovery → Recommendation → Generation → Handoff) ✅
- Failure modes with fallback strategies ✅
- Validation tools (rubric + checklist) ✅
- Examples across archetypes ✅

**Patterns this skill embodies:**

1. **PRD-style specification** - Every skill is a product with clear purpose/users/non-goals
2. **Schema thinking** - Inputs and outputs are typed and explicit
3. **Organizational doctrine** - "How we do things" encoded in guardrails
4. **Failure modes** - Graceful degradation when uncertain
5. **Decomposition-first** - Break down complex tasks before executing
6. **Memory-aware** - Saves preferences for repeat use
7. **Adaptive recommendations** - Structure matches task, not forced templates
8. **Self-validation** - Provides rubric and checklist to verify quality

**Version**: 4.0
**Last updated**: February 2026
**Shareable**: Yes (all examples are generalized)

**What's new in v4.0:**
- **Restored companion files** - Combines v3's enhanced documentation with v2's practical reference files
- `references/templates/` - Actual template files for faster scaffold generation
- `references/decision-logic.md` - Standalone Q&A mapping reference
- `references/examples/` - Python validation scripts as usable files
- README.md - Quick reference for the skill itself
- All v3 enhancements preserved in SKILL.md
- Best of both worlds: complete inline docs + practical reference files

**What was new in v3.0:**
- Added Table of Contents for easier navigation
- Moved Quick Start to top for better first-time user experience
- Added Self-Documentation section (this section)
- Added real-world JSON output example in Output Schema
- Added section markers for easier navigation ([SECTION: X])
- **Enhanced with concrete examples:**
  - Added 3 JSON schema examples for self-updating architecture (preferences, replacements, corrections)
  - Added 2 Python script implementations inline (banned phrase scanner, readability metrics)
  - Added conservative skill-splitting philosophy with justification criteria
  - Added Pattern 4 + 3 counter-examples emphasizing skills can handle complexity
  - Expanded testing protocols with detailed validation checklists and 4 test scenarios
  - Expanded memory patterns with configuration naming conventions and reuse examples
  - Added Q11 decision guidance (when to use/avoid self-updating)
  - Added mode selection context (when to create vs evaluate)

**What was new in v2.0:**
- Added Q12: Automated Validation question to discovery interview
- Added Scaffold Validation Checklist (binary verification of completeness)
- Added Architecture Quality Rubric (8-criteria scoring for recommendations)
- Enhanced dual-format output with JSON metadata in Step 2
- Expanded conflict detection in Failure Modes with multiple examples
- Improved self-consistency (practices what it preaches)

---

## [SECTION: REFERENCE TEMPLATES]

This skill uses archetype templates from `references/templates/`:
- **Simple/Transformational** (`simple-transformational.md`) - For linear content transformation tasks
- **Complex/Interview** (`complex-interview.md`) - For multi-phase discovery workflows
- **Lightweight** (`lightweight.md`) - For simple binary execution tasks

These templates are read during scaffold generation (Step 3) and customized based on Q&A answers.

---

**Ready to build a skill? Tell me what you want to create.**
