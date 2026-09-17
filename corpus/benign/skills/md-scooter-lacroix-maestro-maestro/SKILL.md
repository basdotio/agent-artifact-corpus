---
name: maestro
description: "Spec-driven development framework that integrates with OpenCode to provide structured project planning, track management, and implementation workflow. Use when you need to: (1) Initialize a new Maestro project with product definition, tech stack, and workflow configuration, (2) Create new tracks (features/bug fixes) with interactive specification generation, (3) Implement tracks with automatic agent selection based on task complexity, (4) View project status and progress across all tracks, (5) Revert work at track/phase/task level. This skill provides a complete TDD workflow with project memory, git-aware tracking, and multi-agent orchestration."
metadata:
  short-description: Maestro spec-driven development
---

# Maestro Skill

Maestro is a spec-driven development framework that provides structured project planning, track management, and implementation workflow with automatic agent selection.

## Quick Start

**Initialize a new project:**
```bash
/maestro setup
```

**Create a new track:**
```bash
/maestro newTrack "Add user authentication"
```

**Implement a track:**
```bash
/maestro implement <track_name_or_id>
```

**View project status:**
```bash
/maestro status
```

**Revert work:**
```bash
/maestro revert [track|phase|task]
```

## Core Concepts

### Tracks
A **track** is a feature, bug fix, or chore that goes through:
1. **Specification** (`spec.md`) - Interactive requirements gathering
2. **Planning** (`plan.md`) - Detailed task breakdown
3. **Implementation** - Automatic agent selection based on complexity

### Project Structure
```
maestro/
├── product.md           # Product vision and guidelines
├── tech-stack.md        # Technology stack choices
├── workflow.md          # Development workflow rules
├── tracks.md            # Track registry and overview
├── setup_state.json     # Setup progress tracking
└── tracks/
    └── <track_id>/
        ├── spec.md      # Track specification
        └── plan.md      # Implementation plan
```

### Agent Selection
Maestro automatically selects appropriate agents during implementation:
- **oracle**: Architecture, code review, strategy.
- **librarian**: Multi-repo analysis, doc lookup, implementation examples.
- **explore**: Fast codebase exploration and pattern matching.
- **frontend-ui-ux-engineer**: Designer turned developer. Builds gorgeous UIs.
- **document-writer**: Technical writing expert.
- **multimodal-looker**: Visual content specialist. Analyzes PDFs, images, diagrams.

## Commands Reference

### `/maestro setup`
Initialize the Maestro environment for a new or existing project.

**Process:**
1. Detects if project is greenfield (new) or brownfield (existing)
2. For brownfield: Analyzes existing code to understand tech stack
3. Interactive product definition (vision, guidelines, tech stack)
4. Workflow and code styleguide selection
5. Generates initial track

**When to use:** First time setting up Maestro in a project directory.

### `/maestro newTrack <description>`
Create a new track with interactive specification generation.

**Process:**
1. Loads project context from `maestro/` directory
2. Asks 3-5 clarifying questions based on track type
3. Generates comprehensive `spec.md` with:
   - Overview
   - Functional Requirements
   - Non-Functional Requirements
   - Acceptance Criteria
   - Out of Scope
4. Creates detailed `plan.md` with task breakdown
5. Registers track in `tracks.md`

**When to use:** Starting any new feature, bug fix, or chore.

### `/maestro implement <track_name_or_id>`
Execute the implementation plan for a specific track.

**Process:**
1. Loads track specification and plan
2. Identifies task complexity and requirements
3. Automatically selects appropriate agent for each task:
   - Architecture & Strategy → oracle
   - Codebase Analysis → librarian
   - UI/UX Implementation → frontend-ui-ux-engineer
   - Documentation → document-writer
4. Executes tasks with TDD workflow (test → implement → refactor)
5. Tracks progress in `plan.md`
6. Stores context to memory system

**When to use:** Implementing a track that has been planned.

### `/maestro status`
Display current progress across all tracks.

**Output includes:**
- Current phase and in-progress tasks
- Completion statistics (phases, tasks, percentage)
- Next pending actions
- Any blockers or dependencies
- Memory context timestamp

**When to use:** Checking project progress, identifying next actions.

### `/maestro revert [track|phase|task]`
Revert previous work at specified granularity.

**Options:**
- **track**: Revert entire track to pre-implementation state
- **phase**: Revert specific phase within current track
- **task**: Revert specific task (default if not specified)

**When to use:** Undoing implementation work, recovering from errors.

## Workflow

### Development Cycle
1. **Plan** - Use `/maestro newTrack` to create spec and plan
2. **Implement** - Use `/maestro implement` to execute with automatic agent selection
3. **Review** - Maestro includes built-in agent review for critical code
4. **Track** - Use `/maestro status` to monitor progress

### TDD Integration
Maestro enforces Test-Driven Development:
1. Write failing test first
2. Implement minimal code to pass
3. Refactor for quality
4. Commit with test coverage

## Integration with OpenCode

This skill integrates Maestro's workflow with OpenCode's agent system:

### Command Mappings
- `/maestro setup` → Loads `~/.config/opencode/commands/maestro:setup.md`
- `/maestro newTrack` → Loads `~/.config/opencode/commands/maestro:newTrack.md`
- `/maestro implement` → Loads `~/.config/opencode/commands/maestro:implement.md`
- `/maestro status` → Loads `~/.config/opencode/commands/maestro:status.md`
- `/maestro revert` → Loads `~/.config/opencode/commands/maestro:revert.md`

### Agent Delegation
Maestro commands automatically delegate to specialized agents:
- Code review & strategy → oracle
- Analysis & understanding → librarian
- UI/UX implementation → frontend-ui-ux-engineer
- Technical writing → document-writer

## Dependencies

### Required MCPs
- **nexus-memory**: Project context and memory storage
- **memori-memory-mcp**: Enhanced memory with categorization

### Required Skills
None - Maestro works standalone

### Compatible Agents
All OpenCode agents are compatible:
- oracle
- librarian
- explore
- frontend-ui-ux-engineer
- document-writer
- multimodal-looker

## Best Practices

1. **Always run setup first** - Ensures proper project context
2. **Be specific in track descriptions** - Better specs = better plans
3. **Let agent selection work automatically** - Trust the complexity analysis
4. **Check status regularly** - Stay aligned with progress
5. **Use revert carefully** - Can undo significant work

## Troubleshooting

**"Maestro is not set up"**
→ Run `/maestro setup` first

**"tracks.md not found"**
→ Run `/maestro setup` to initialize project structure

**Agent not found**
→ Ensure OpenCode agent is properly configured in `opencode.jsonc`

**Memory errors**
→ Check nexus-memory MCP is running and configured

## Advanced Features

### Prompt Enhancer Integration
Maestro integrates with prompt enhancer for context-aware question generation during spec creation.

### Git-Aware Tracking
Maestro tracks implementation progress alongside git commits for complete history.

### Multi-Project Support
Each project directory maintains its own Maestro state.

## Templates

Maestro uses templates for consistent project setup:
- `workflow.md` - Development workflow rules
- `code_styleguides/*` - Language-specific style guides
- Located in the installed OpenCode skill directory: `~/.config/opencode/skill/maestro/templates/`

## See Also

- [OpenCode Config](~/.config/opencode/opencode.json) - Command templates and MCP servers
- [OpenCode Skill](~/.config/opencode/skill/maestro/SKILL.md) - This skill definition (installed)
- [Maestro Command Files](~/.config/opencode/commands/) - Installed Maestro command implementations
