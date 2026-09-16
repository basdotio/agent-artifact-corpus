# Rails Pattern Finder

---
name: rails-pattern-finder
description: Finds Rails code patterns and best practices using Ref (primary), Grep, and reference patterns with WebFetch fallback
version: 1.2.0
author: Rails Workflow Team
tags: [rails, patterns, best-practices, code-examples, ref]
priority: 3
---

## Purpose

Searches the current Rails codebase for existing patterns and provides best-practice code examples. Helps agents write code consistent with project conventions.

**Replaces**: Manual codebase exploration and pattern recognition

## Usage

**Auto-invoked** when agents need code examples:
```
Agent: "How is authentication implemented in this project?"
*invokes rails-pattern-finder pattern="authentication"*
```

**Manual invocation**:
```
@rails-pattern-finder pattern="service_objects"
@rails-pattern-finder pattern="api_serialization"
@rails-pattern-finder pattern="background_jobs"
```

## Supported Patterns

See `reference.md` for complete pattern list. Common patterns:

### Architectural Patterns
- `service_objects` - Service layer implementation
- `form_objects` - Form object pattern
- `query_objects` - Complex query encapsulation
- `decorators` - Decorator/presenter pattern
- `policies` - Authorization policies (Pundit)

### API Patterns
- `api_versioning` - API version management
- `api_serialization` - JSON response formatting
- `api_authentication` - Token/JWT authentication
- `api_error_handling` - Error response patterns

### Database Patterns
- `scopes` - Named scope usage
- `concerns` - Model concern organization
- `polymorphic_associations` - Polymorphic pattern
- `sti` - Single Table Inheritance
- `database_views` - Database view usage

### Testing Patterns
- `factory_usage` - FactoryBot patterns
- `request_specs` - API request testing
- `system_specs` - System/feature testing
- `shared_examples` - RSpec shared examples

## Search Process

### Step 1: Pattern Lookup
```
Input: pattern="service_objects"
Lookup: reference.md → search_paths, file_patterns, code_patterns
```

### Step 2: Codebase Search
```
Tool: Grep
Pattern: "class.*Service$"
Glob: "app/services/**/*.rb"
Output: List of matching files
```

### Step 3: Example Extraction
```
Tool: Read
Files: [top 3 matches by relevance]
Extract: Class structure, method signatures, usage patterns
```

### Step 4: Response Formatting
```ruby
## Pattern: Service Objects

### Found in Project (3 examples):

**1. UserRegistrationService** (app/services/user_registration_service.rb)
```ruby
class UserRegistrationService
  def initialize(params)
    @params = params
  end

  def call
    user = User.create!(@params)
    send_welcome_email(user)
    user
  end

  private

  def send_welcome_email(user)
    UserMailer.welcome(user).deliver_later
  end
end
```

**2. PaymentProcessingService** (app/services/payment_processing_service.rb)
[Example code...]

### Best Practice from Rails Community:
[Fetch from reference.md or WebSearch]

**Source**: Project codebase + Rails best practices
```

## Reference Lookup

**Pattern → Search Strategy mapping** in `reference.md`:

```yaml
service_objects:
  title: "Service Objects"
  search_paths: ["app/services/**/*.rb"]
  file_patterns: ["*_service.rb"]
  code_patterns:
    - "class \\w+Service"
    - "def call"
  best_practice_url: "https://example.com/rails-service-objects"
  keywords: [service, business logic, call method]

api_serialization:
  title: "API Serialization"
  search_paths: ["app/serializers/**/*.rb", "app/blueprints/**/*.rb"]
  file_patterns: ["*_serializer.rb", "*_blueprint.rb"]
  code_patterns:
    - "class \\w+Serializer"
    - "ActiveModel::Serializer"
    - "Blueprinter::Base"
  keywords: [json, serializer, blueprint, jbuilder]
```

## Output Format

### Pattern Found in Project
```markdown
## Pattern: [Pattern Name]

### Found in Project ([N] examples):

**File**: [path/to/file.rb]
**Purpose**: [What this implementation does]

```ruby
[Code example from project]
```

**Key characteristics**:
- [Feature 1]
- [Feature 2]

**Usage in project**:
[How this pattern is used - grep for usage examples]
```

### Pattern Not Found
```markdown
## Pattern: [Pattern Name] - Not found in project

**Searched**:
- app/services/**/*.rb
- app/lib/**/*.rb

**Best Practice Implementation**:

```ruby
[Example from reference.md or external source]
```

**To implement in this project**:
1. Create: app/services/[name]_service.rb
2. Follow structure above
3. Test in: spec/services/[name]_service_spec.rb

**Similar patterns in project**:
- [Alternative pattern found]
```

### Multiple Variants Found
```markdown
## Pattern: [Pattern Name] - Multiple variants found

This project uses [N] different approaches:

### Variant 1: [Approach Name] ([N] files)
[Example code...]

### Variant 2: [Approach Name] ([N] files)
[Example code...]

**Recommendation**: [Which variant to use for consistency]
```

## Implementation Details

**Tools used** (in order of preference):
1. **Read** - Load `reference.md` pattern definitions
2. **context7_fetch** (primary) - Fetch curated patterns via Context7 MCP
3. **ref_search_documentation** (secondary) - Search Rails pattern docs via Ref MCP
4. **ref_read_url** (secondary) - Fetch specific pattern guides via Ref MCP
5. **tavily_search** (tertiary) - Optimized search via Tavily MCP
6. **Grep** - Search codebase for pattern matches
7. **Read** - Extract code examples from matching files
8. **WebFetch** (fallback) - Fetch pattern docs if MCPs not available
9. **WebSearch** (optional) - Fetch external best practices
10. **Glob** - Find files matching pattern

**Optional dependencies**:
- **context7-mcp**: Fastest pattern documentation
- **ref-tools-mcp**: Token-efficient pattern search
- **tavily-mcp**: Optimized search for LLMs
- If neither installed: Falls back to WebFetch and local searches (still works!)

**Search strategies**:

**File-based search**:
```bash
# Find files matching naming convention
glob: "app/services/*_service.rb"
```

**Content-based search**:
```bash
# Find class definitions
grep: "class \\w+Service$"
path: "app/services"
```

**Usage search**:
```bash
# Find where pattern is used
grep: "UserRegistrationService\\.new"
path: "app/controllers"
```

**Relevance ranking**:
1. Most recently modified files (likely current patterns)
2. Files with most references (commonly used)
3. Files with comprehensive examples (best for learning)

## Error Handling

**Pattern not found**:
```markdown
⚠️ Pattern "[pattern]" not found in project

**Searched**:
- [paths searched]

**Options**:
1. View best practice example (from reference.md)
2. Search for similar pattern: [suggestions]
3. Implement from scratch using best practices
```

**Invalid pattern name**:
```markdown
❌ Unknown pattern: "[pattern]"

Available patterns:
- service_objects
- form_objects
- query_objects
[...from reference.md...]

Try: @rails-pattern-finder pattern="[one of above]"
```

**Ambiguous results**:
```markdown
⚠️ Multiple pattern variants found for "[pattern]"

Please review all variants and choose one for consistency.

[List all variants found...]
```

## Integration

**Auto-invoked by**:
- All 7 Rails agents when generating new code
- @rails-architect for architectural decisions
- Agents adapting to project conventions

**Workflow**:
1. Agent needs to generate code (e.g., new service)
2. Invokes @rails-pattern-finder pattern="service_objects"
3. Receives project-specific examples
4. Generates code matching project style

## Special Features

### Pattern comparison
```
@rails-pattern-finder pattern="service_objects" compare_with="form_objects"
→ Shows differences and use cases for each
```

### Project convention detection
```
@rails-pattern-finder detect_conventions
→ Analyzes codebase and reports common patterns
```

### Anti-pattern detection
```
@rails-pattern-finder anti_patterns
→ Searches for common Rails anti-patterns in codebase
```

### Test pattern search
```
@rails-pattern-finder pattern="service_objects" include_tests=true
→ Shows both implementation and test examples
```

## Pattern Categories

### Creation Patterns
- `service_objects` - Business logic encapsulation
- `form_objects` - Form handling
- `query_objects` - Query encapsulation
- `builder_pattern` - Object construction

### Structural Patterns
- `concerns` - Module organization
- `decorators` - Presentation logic
- `adapters` - External API integration
- `repositories` - Data access layer

### Behavioral Patterns
- `observers` - Event handling
- `state_machines` - State management
- `strategies` - Algorithm selection
- `commands` - Action encapsulation

### Rails-Specific
- `sti` - Single Table Inheritance
- `polymorphic_associations` - Flexible relationships
- `custom_validators` - Validation logic
- `background_jobs` - Async processing

## Testing

**Test cases**:
1. Pattern exists in project → Returns project examples
2. Pattern doesn't exist → Returns best practice example
3. Multiple variants → Lists all with recommendation
4. Invalid pattern → Error with suggestions
5. Empty project → All patterns return best practices

## Notes

- This skill searches **current project codebase**, not external repos
- Pattern definitions in `reference.md` include search strategies
- Results prioritize recent, commonly-used code
- Helps maintain consistency across large teams
- Adapts to project-specific conventions automatically
- Use with @rails-docs-search (theory) and @rails-api-lookup (APIs)
