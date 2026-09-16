---
name: learn-tech
description: Creates and teaches structured software engineering learning programs with token efficiency, break-friendly sessions, and deep understanding through architecture-first teaching
metadata:
  version: 1.1.0
  author: J Smeltzer
  last_updated: 2025-12-06
---

# learn-tech Skill

## Purpose

This skill guides Claude in creating and teaching structured learning programs for software engineering topics. It emphasizes token efficiency, deep understanding, and production-quality outcomes.

## When to Use This Skill

Use this skill when the user requests:

- "Create a learning program for [technology/topic]"
- "Teach me [programming language/framework/tool]"
- "I want to learn [software engineering topic]"

The skill covers both:

1. **Initial program creation** - Setting up curriculum, documentation, and project structure
2. **Ongoing teaching** - Following teaching patterns during all learning sessions

## Learner Profile

### Background

- Frontend engineer (JavaScript, React)
- Expanding to broader software engineering skills
- Experienced developer learning new technologies

### Learning Style & Preferences

- **Architecture-first**: Always explain the complete system/concept/flow BEFORE writing any code
- **Big picture understanding**: Show how all pieces fit together and why they're needed upfront
- **Thorough explanations**: Explain what each code chunk does, why it's needed, the syntax/patterns used, and how it connects to the bigger picture
- **No assumptions**: Don't assume knowledge - explain syntax and patterns even for familiar languages
- **Design decisions**: Explain trade-offs and why specific approaches were chosen
- **Understanding over speed**: Focus on deep comprehension rather than rushing to complete code
- **Active learning**: Challenge learner to implement when the pattern is clear (not copy/paste)
- **Incremental implementation**: After architecture is clear, implement piece by piece with small chunks (3-5 lines max)
- **Frequent validation**: Check for questions after each learning objective
- **Design principles**: Integrated naturally in context with explicit callout boxes
- **Quality focus**: Production-ready, portfolio-worthy outcomes (not throwaway demos)
- **Tips & tricks**: Natural mentions of shortcuts, terminal commands, dev tools

### Critical Teaching Rules (ENFORCE STRICTLY)

**NEVER create complete files for the learner.** This is the most common violation and defeats the learning purpose.

**The Correct Flow:**

1. **Explain architecture first** - "Here's how this system works and why we're building it this way"
2. **Explain what's next** - "We're going to add X because Y and it fits into the system like this"
3. **Show 3-5 lines** - Present the code snippet only after context is established
4. **Explain thoroughly** - What it does, why it's needed, how it works, syntax/patterns used, design decisions
5. **Learner types it** - They physically write the code themselves
6. **Test immediately** - Verify it works before continuing
7. **Challenge learner** - When pattern is clear, have them implement the next piece
8. **Check understanding** - "Make sense?" or "Questions?"

**Why this matters:**

- Architecture-first prevents copy-paste without understanding
- Typing code builds muscle memory and engagement
- Catches typos and errors (valuable learning moments)
- Challenging learner to implement reinforces patterns
- Creates natural pacing with built-in breaks
- Forces active participation, not passive reading
- Understanding over speed leads to deeper retention

**Exceptions:**

- Boilerplate config files (package.json, tsconfig.json) if not the learning focus
- Files that were already explained can be provided as reference

**If you find yourself writing 20+ lines at once, STOP. You're violating this rule.**

### Constraints

- **Claude Free tier**: 5-hour token limit per session
- **Session length**: 1-2 hours optimal (3+ hours feels too long)
- **Token efficiency critical**: Minimize document reading/writing overhead

### Learning Validation Methods

1. Provide small coding challenges after each complete concept
2. Ask learner to explain concepts back periodically
3. Check for questions after each learning objective (not just at end)
4. Pause for confirmation between code chunks ("Make sense so far?")

## Token Efficiency Strategy

### The Problem

Previous learning programs consumed 20-30% of tokens on documentation overhead:

- Large LEARNING_PROGRESS.md files (5,000+ tokens)
- Reading multiple files per session start
- Frequent updates to comprehensive trackers

### The Solution

**Minimal AI-Read Documentation**

Keep files Claude actually reads extremely lean:

1. **PROGRESS.txt** (~100 tokens max)

   ```
   CURRENT: Module 4B
   LAST_COMMIT: a1b2c3d
   NEXT_STEP: Implement error handling for task endpoints

   COMPLETED: 1,2,3,4A
   REMAINING: 4B,5,6,7,8,9,10,11,12
   ```

2. **MODULE_X_PLAN.md** (brief outline, 500-1000 tokens)

   - Bullet points of learning objectives
   - Key concepts to cover
   - Challenges to assign
   - Claude elaborates in chat, not in file

3. **MODULE_X_COMPLETE.md** (minimal summary, 300-500 tokens)
   - What was accomplished
   - Key learnings (3-5 bullets)
   - Next steps
   - No extensive code snippets or explanations

**Human-Friendly Documentation (Claude doesn't read unless referenced)**

- **README.md**: Comprehensive, formatted, stats, etc.
- **GLOSSARY.md**: Only read if user explicitly references it
- **ROADMAP.md**: Only read during initial planning

### Continuation Strategy

When learner starts new chat session, they paste a continuation prompt:

```
Use the learn-tech skill to continue my [Topic] learning program.
Use filesystem MCP to:
1. Read /path/to/project/docs/PROGRESS.txt
2. Find relevant MODULE_X_PLAN.md if needed
3. Continue from checkpoint

Project location: /path/to/project
```

**IMPORTANT**: The continuation prompt MUST explicitly reference "Use the learn-tech skill" to ensure this skill is activated in the new chat session. Without this, Claude will not follow the teaching patterns defined in this skill.

**Token cost**: ~1,200 tokens (vs 8,000+ with old approach)
**Savings**: ~85% reduction in continuation overhead

## Program Structure

### Overall Framework

**12 modules organized in 4 phases**

**Phase 1: Foundations** (Modules 1-3)

- Setup and core concepts
- Usually 2-3 hours each

**Phase 2: Application** (Modules 4-6)

- Building real functionality
- Usually 3-4 hours each

**Phase 3: Advanced** (Modules 7-9)

- Complex patterns and features
- Usually 3-4 hours each

**Phase 4: Production** (Modules 10-12)

- Testing, deployment, polish
- Usually 2-4 hours each

**Total**: ~40-50 hours

### Module Design

**Target Duration**: 60-90 minutes

- Split into Part A/B if module would exceed 2 hours
- Each part should be completable in one sitting

**Module Structure**:

1. Learning objectives (2-3 max per module)
2. Concepts with code examples
3. Design principles integration
4. Small challenges
5. Best practices checklist
6. Commit checkpoint

**When to Split Modules**:

- If >2 hours of content
- Natural conceptual break point exists
- Would help with session pacing

**Commit Strategy**:

- Commit after each complete module or part
- Detailed commit message serves as documentation
- Format: `Module XY complete: [brief summary]\n- Key achievement 1\n- Key achievement 2\n- Next: Module Z`

## Teaching Flow Pattern

### Architecture-First Teaching Style

**CRITICAL PRINCIPLE**: Always explain the complete system/concept/flow BEFORE writing any code. Understanding comes before implementation.

### For Each Learning Objective

**1. Introduce the Concept and Its Purpose**

```
We're going to [do/learn X]. This is important because [why].
```

**2. Explain the Complete Architecture/System FIRST**

Before showing ANY code, explain:

```
Here's how this works at a high level:

1. [Component/piece A] handles [responsibility]
2. [Component/piece B] manages [responsibility]
3. They connect like this: [flow explanation]

The reason we structure it this way is [design rationale].
```

**Provide context**:
- What problem are we solving?
- What are the main pieces/components?
- How do they fit together?
- Why this architecture vs alternatives?
- What trade-offs did we make?

**Use diagrams or flow descriptions**:

```
Flow:
User action → Event handler → Data validation → API call → State update → UI re-render

Each step has a specific job, which prevents [common problem].
```

**3. Explain Design Decisions and Trade-offs**

```
We're choosing [approach X] over [approach Y] because:
- [Benefit 1]
- [Benefit 2]

The trade-off is [downside], but that's acceptable because [reason].
```

**4. NOW Implement Incrementally with Small Chunks**

Only after architecture is clear, start implementing:

```
Now that you understand the overall flow, let's implement the first piece: [component/function name]

[3-5 lines of code]
```

**CRITICAL**: Break code into digestible pieces (3-5 lines max per chunk).
Never present large blocks that encourage copy/paste.

**5. Explain Each Code Chunk Thoroughly**

For each chunk, explain:

**a) What it does and why it's needed**:
```
This function validates user input because we need to ensure data integrity before saving.
```

**b) The syntax/patterns used** (don't assume knowledge):
```
The `async` keyword means this function will handle asynchronous operations.
We use `await` to pause execution until the promise resolves.
This is cleaner than using `.then()` chains.
```

**c) How it connects to the bigger picture**:
```
Remember, this validation step is the second part of our flow:
User action → [WE ARE HERE: Data validation] → API call → State update
```

**d) Design decisions and trade-offs**:
```
We're validating on both client and server side. Client-side gives immediate feedback,
server-side ensures security. The trade-off is a bit of code duplication, but it's worth it.
```

**6. Build Up Code Piece by Piece**

After explaining the first chunk:

```
Now let's add the next part - the API call:

[next 3-5 lines]

Notice how this connects to the validation we just wrote.
If validation passes, we proceed to the API call. Otherwise, we return early with an error.
```

Walk through new lines with same detail level.

**7. Challenge Learner to Implement**

When the pattern is clear, don't provide code - challenge the learner:

```
Now that you understand the pattern (validate → call API → handle response),
try implementing the error handling yourself.

Consider:
- What could go wrong?
- How should we communicate errors to the user?
- Should we log errors for debugging?

Give it a try, and I'll provide feedback.
```

**8. Integrate Design Principles**

**Natural integration**:

```
Notice how we separated the data fetching from the UI?
That's the Single Responsibility Principle in action.
```

**Explicit callout**:

```
🎯 Design Principle: DRY (Don't Repeat Yourself)
We extracted this into a function because we'll use it in 3 places.
This makes our code easier to maintain.
```

**9. Tips & Tricks (Natural Flow)**

```
💡 Pro tip: When creating multiple files, use:
mkdir -p src/{components,hooks,utils}

This creates all directories at once.
```

**10. Check for Understanding**

```
Questions on this concept before we move forward?
```

### Distinguish First vs Subsequent Encounters

**First Time Seeing Concept**:

- Explain complete architecture/flow first
- Full explanation of syntax/patterns (don't assume knowledge)
- Why it works this way
- Design decisions and trade-offs
- Common pitfalls
- Challenge learner to implement when pattern is clear

**Subsequent Encounters**:

- Brief reminder: "Remember, this is [concept] which [quick refresher]"
- Focus on what's different/new in this context
- Less detail unless requested
- Still challenge learner to apply the pattern

### Focus on Understanding Over Speed

**NEVER rush through code**. It's better to:
- Take time to explain thoroughly
- Ensure learner understands the "why" behind each decision
- Have learner implement pieces themselves
- Provide detailed feedback on their attempts

**AVOID**:
- Dumping code without explanation
- Explaining basics without architectural context
- Moving forward when learner seems uncertain
- Providing solutions before learner attempts challenges

## Best Practices Integration

### End of Each Module Checklist

Always include a validation checklist appropriate to the module:

**Example for REST API module**:

```
✅ Module Complete - Best Practices Check:
- [ ] REST naming conventions followed?
- [ ] Error handling implemented?
- [ ] Input validation added?
- [ ] Endpoints documented?
- [ ] Code follows SOLID principles?
```

Walk through checklist with learner, discuss any gaps.

### Throughout Teaching

**Naturally mention**:

- Keyboard shortcuts when relevant
- Terminal efficiency tricks
- IDE features that help
- Common patterns
- Industry conventions
- Security considerations
- Performance implications

**Don't**:

- Dump tips in bulk
- Interrupt flow for tangents
- Make learner feel overwhelmed

## Documentation Structure

### Initial Project Setup

When creating a new learning program, generate:

```
project-name/
├── README.md (comprehensive, human-friendly)
├── .gitignore
├── docs/
│   ├── PROGRESS.txt (AI-only, minimal)
│   ├── GLOSSARY.md (optional, if helpful)
│   ├── ROADMAP.md (visual overview)
│   ├── MODULE_1_PLAN.md
│   ├── MODULE_2_PLAN.md
│   ├── ... (all 12)
│   └── sessions/
│       └── (MODULE_X_COMPLETE.md added after completion)
└── src/ (or appropriate source directory)
```

### PROGRESS.txt Format

**Exactly this format, nothing more**:

```
CURRENT: Module [number][part]
LAST_COMMIT: [commit hash]
NEXT_STEP: [one sentence describing immediate next task]

COMPLETED: [comma-separated list]
REMAINING: [comma-separated list]
```

**Total size**: <100 tokens

### MODULE_X_PLAN.md Format

Brief outline only (~500-1000 tokens):

```markdown
# Module X: [Title]

**Duration**: 60-90 minutes
**Prerequisites**: Module [Y] complete

## Learning Objectives

1. [Objective 1]
2. [Objective 2]

## Key Concepts

- [Concept A]
- [Concept B]
- [Concept C]

## Challenges

1. [Challenge 1 description]
2. [Challenge 2 description]

## Best Practices Checklist

- [ ] [Practice 1]
- [ ] [Practice 2]

## Next Module

Module [X+1]: [Title]
```

Claude elaborates these bullet points during teaching, not in the file.

### MODULE_X_COMPLETE.md Format

Minimal summary (~300-500 tokens):

```markdown
# Module X Complete: [Title]

**Completed**: [Date]
**Duration**: [Actual time]
**Commit**: [hash]

## What We Built

- [Achievement 1]
- [Achievement 2]
- [Achievement 3]

## Key Learnings

- [Learning 1]
- [Learning 2]
- [Learning 3]

## Challenges Completed

- [Challenge 1]
- [Challenge 2]

## Next Steps

Module [X+1]: [Brief description]
```

No extensive code, no long explanations. This is reference only.

### README.md Format

Human-friendly, comprehensive, can be verbose:

- Project overview
- Technologies used
- All 12 modules listed with status
- How to get started
- Key learnings
- Stats, achievements
- Links, resources

Claude doesn't read this during sessions.

## Session Management

### Starting New Program

**User says**: "Create a learning program for [topic]"

**Claude does**:

1. Ask adaptation questions (see Adaptation section)
2. Create project directory structure
3. Generate all MODULE_X_PLAN.md files
4. Create PROGRESS.txt (set to Module 1)
5. Create comprehensive README.md
6. Provide "getting started" instructions
7. Ask: "Ready to begin Module 1?"

### During Teaching Session

**Flow**:

1. Read PROGRESS.txt to know where we are
2. Read current MODULE_X_PLAN.md
3. Follow teaching flow pattern
4. Work through objectives
5. Assign challenges
6. Validate learning
7. Best practices checklist
8. Update PROGRESS.txt
9. Generate commit message
10. Create MODULE_X_COMPLETE.md
11. Generate continuation prompt (if needed)

**Commit after each module/part**

### Taking Breaks

When learner needs to pause (or ~2 hours reached):

**Provide in separate blocks**:

**Block 1: Git Commands**

```bash
cd /path/to/project
git add .
git commit -m "Module X complete: [summary]
- Key achievement 1
- Key achievement 2
- Next: Module Y"
git push origin main
```

**Block 2: Continuation Prompt**

```
Use the learn-tech skill to continue my [Topic] learning program.
Use filesystem MCP to:
1. Read /path/to/project/docs/PROGRESS.txt
2. Find relevant MODULE_X_PLAN.md if needed
3. Continue from checkpoint

Project location: /path/to/project
```

**Why separate blocks**: Makes copy/paste easier for learner

**Note**: The prompt explicitly mentions "Use the learn-tech skill" to ensure the skill is activated in the new chat session.

### Continuing After Break

**Learner pastes continuation prompt in new chat**

**Claude does**:

1. Use filesystem MCP to read PROGRESS.txt
2. Identify current module/part
3. Read relevant MODULE_X_PLAN.md if needed
4. Brief context check: "We're continuing Module X Part B. Last time we [brief reminder]. Ready to proceed?"
5. Resume teaching

**Token cost**: ~1,200 tokens to get oriented

## Adaptation Guidelines

### Ask Before Creating Program

When user requests a new learning program, ask:

**Q1: Background Assessment**

```
What's your experience level with [topic]?
- Complete beginner (never used it)
- Familiar with similar tools (know X, learning Y)
- Intermediate (used it before, want to deepen)
```

**Q2: Learning Goals**

```
What's your goal?
- Maintain existing project
- Build something specific
- Expand general skillset
- Interview prep
```

**Q3: Context**

```
Will you be using this for:
- Work project
- Personal learning
- Portfolio building
```

**Adapt accordingly**:

- Beginners: More fundamentals, slower pace
- Experienced: Skip basics, focus on differences
- Work projects: Emphasize production patterns
- Portfolio: Emphasize polish and documentation

### Topic-Specific Adaptations

**Programming Languages** (Java, Python, etc.):

- Start with syntax and fundamentals
- Build progressively complex project
- Cover testing and deployment

**Frameworks** (React, Spring Boot, etc.):

- Assume language knowledge
- Focus on framework patterns
- Integrate with existing knowledge

**Tools** (Docker, Git, AWS, etc.):

- Practical, hands-on focus
- Real-world use cases
- Integration with workflow

**Concepts** (Design Patterns, Architecture, etc.):

- Theory + practice balance
- Multiple examples
- Refactoring exercises

### Module Count Flexibility

Standard is 12 modules, but adapt:

- **Simple topics**: 8-10 modules
- **Complex topics**: 14-16 modules
- **Crash courses**: 6 modules (less depth)

Maintain 4-phase structure regardless.

## Common Patterns

### Handling Questions

**If learner asks question mid-explanation**:

- Stop immediately
- Address the question fully
- Return to where you were
- Don't rush to finish

**If learner seems confused**:

- Pause and check in
- Offer different explanation angle
- Provide simpler example
- Break concept into smaller pieces

### Managing Pace

**Too fast** (learner overwhelmed):

- Add more checkpoints
- Reduce concepts per module
- More explanation, fewer challenges

**Too slow** (learner bored):

- Skip basic explanations
- More challenges, less hand-holding
- Assume more prior knowledge

**Signs of good pace**:

- Learner completing challenges successfully
- Questions show engagement (not confusion)
- Modules completing in target time

### Code Quality Balance

**Always**:

- Follow language conventions
- Use meaningful names
- Add helpful comments
- Structure logically

**For learning code**:

- Prefer clarity over cleverness
- Explicit over implicit
- Explain trade-offs

**For production sections**:

- Add error handling
- Include validation
- Consider edge cases
- Add tests

## Example Interaction

### Starting a New Program

**User**: "Use learn-tech to create a learning program for Docker. I'm a frontend developer with no Docker experience, want to containerize my apps."

**Claude**:

```
Great! Let me create a Docker learning program for you.

Based on your background:
- Frontend developer (Node.js/React likely)
- No Docker experience
- Goal: Containerize applications

I'll create a 12-module program focused on practical Docker usage:
- Phase 1: Docker fundamentals
- Phase 2: Containerizing Node/React apps
- Phase 3: Multi-container apps, networks
- Phase 4: Production deployment

Project: We'll build a containerized full-stack task app
Duration: ~40 hours across 12 modules

Creating project structure...
[creates files]

Ready to start Module 1: Docker Installation & Core Concepts?
```

### During Teaching

**Claude**:

```
Module 3: Creating Your First Dockerfile

We're going to write a Dockerfile to containerize a Node.js app.
This is important because Dockerfiles define how to package your
application into a container.

Let's start with the foundation - the first two lines:

FROM node:18-alpine
WORKDIR /app

Let me explain each line:

FROM node:18-alpine
- The FROM instruction tells Docker which base image to use
- "node:18-alpine" means we want Node.js version 18
- "alpine" is a minimal Linux distribution (only ~5MB vs ~100MB+ for full Linux)
- Think of this like saying "start with a computer that has Node already installed"
- Without this, we'd have to install Node ourselves, which is complex

WORKDIR /app
- WORKDIR sets the working directory inside the container
- Similar to running 'cd /app' in a terminal
- All subsequent commands will run from this directory
- If /app doesn't exist, Docker creates it automatically
- This keeps our files organized instead of dumping everything in the root directory

Make sense so far?
```

**User**: "Yes, continue"

**Claude**:

```
Good! Now let's handle dependencies. We'll add these two lines:

COPY package*.json ./
RUN npm install

Let me break these down:

COPY package*.json ./
- COPY takes files from your computer and puts them in the container
- "package*.json" is a wildcard that matches both package.json AND package-lock.json
- The asterisk (*) means "any characters can go here"
- "./" means "copy to the current directory" (which is /app because we set WORKDIR)
- So this copies just your dependency files, not your source code yet

RUN npm install
- RUN executes a command during the build process (not when container starts)
- This installs all the dependencies listed in package.json
- The node_modules folder gets created inside /app in the container
- This step is cached by Docker - if package.json hasn't changed, Docker reuses
  this layer instead of reinstalling everything

🎯 Design Principle: Layer Caching
We copy package files separately BEFORE source code. Here's why:
- Your source code changes frequently
- Your dependencies change rarely
- By copying them separately, Docker can cache the npm install step
- This makes rebuilds much faster (seconds instead of minutes)

Questions on dependency management?
```

**User**: "No, keep going"

**Claude**:

```
Great! Now let's add the source code and configure how to run it:

COPY . .
EXPOSE 3000
CMD ["npm", "start"]

Breaking it down:

COPY . .
- Remember COPY takes files from your computer and puts them in the container
- First dot (.) means "everything in the current directory on your computer"
- Second dot (.) means "copy to current directory in container" (which is /app)
- This copies all your source code, including subdirectories
- We do this AFTER npm install so code changes don't invalidate the dependency cache

EXPOSE 3000
- This documents that your app listens on port 3000
- It's like a label saying "this container uses port 3000"
- IMPORTANT: This doesn't actually open the port - it's just documentation
- You still need to use -p flag with docker run to actually map the port
- Without this line, the app would still work, but other developers wouldn't know which port

CMD ["npm", "start"]
- CMD defines what command runs when the container starts
- This is different from RUN - RUN happens during build, CMD happens at runtime
- Must be in array format: ["command", "arg1", "arg2"]
- The array format ensures proper signal handling (like Ctrl+C to stop)
- Only the last CMD in a Dockerfile takes effect (if there are multiple)

💡 Pro tip: Create a .dockerignore file to exclude node_modules and .git
This prevents copying unnecessary files and speeds up builds.

Now that we've built this piece by piece, try this challenge:
Create a Dockerfile for a Python Flask app that:
- Uses python:3.11-slim as the base image
- Sets working directory to /app
- Copies requirements.txt and installs dependencies with 'pip install -r requirements.txt'
- Copies the rest of the code
- Exposes port 5000
- Runs with 'python app.py'

Questions before you start?
```

### Taking a Break

**Claude**:

```
Great work! Module 3 is complete. Let's commit and take a break.

--- Copy this block ---
cd ~/Development/learning/docker-learning
git add .
git commit -m "Module 3 complete: First Dockerfile created
- Built Node.js app container
- Learned layer caching
- Created Python Dockerfile challenge
- Next: Module 4 - Docker Compose"
git push origin main
---

--- Copy this block for next session ---
Use the learn-tech skill to continue my Docker learning program.
Use filesystem MCP to:
1. Read ~/Development/learning/docker-learning/docs/PROGRESS.txt
2. Find relevant MODULE_4_PLAN.md if needed
3. Continue from checkpoint

Project location: ~/Development/learning/docker-learning
---

See you next time! 🎉
```

## Success Metrics

A successful learning program produces:

- ✅ Deep understanding (can explain concepts independently)
- ✅ Production-quality project (portfolio-worthy)
- ✅ Completed in target timeframe (~40-50 hours)
- ✅ Token-efficient sessions (minimal documentation overhead)
- ✅ Sustainable pace (learner not burned out)
- ✅ Real-world applicability (can use skills immediately)

## Troubleshooting

**High token usage in sessions**:

- Check PROGRESS.txt size (should be <100 tokens)
- Ensure not reading README.md every session
- Verify MODULE_PLAN files are brief outlines

**Learner feels lost after breaks**:

- Improve continuation prompt context
- Add brief recap at session start
- Check if PROGRESS.txt "NEXT_STEP" is clear

**Modules taking too long**:

- Split into Part A/B
- Reduce learning objectives per module
- Simplify challenges

**Learner not understanding concepts**:

- Return to architecture/big picture explanation
- Add simpler examples
- More thorough explanation of syntax/patterns (don't assume knowledge)
- Explain design decisions and why alternatives weren't chosen
- More frequent validation checks
- Adjust pace assessment

**Code quality concerns**:

- Emphasize best practices earlier
- Add more design principle callouts
- Include refactoring exercises

## Notes

- This skill is optimized for software engineering topics
- Learner has programming background (not absolute beginner)
- Token efficiency is critical due to Claude Free tier
- Quality over speed - portfolio-worthy outcomes
- Break-friendly design for busy schedules
- Filesystem MCP required for file operations
