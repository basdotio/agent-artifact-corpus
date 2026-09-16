# Rails Docs Search

---
name: rails-docs-search
description: Searches Rails Guides for conceptual documentation using Ref (primary) or WebFetch (fallback) with reference mappings
version: 1.2.0
author: Rails Workflow Team
tags: [rails, documentation, guides, search, ref]
priority: 3
---

## Purpose

Fetches conceptual documentation from official Rails Guides based on topics. Returns relevant guide sections with version-appropriate URLs.

**Replaces**: `mcp__rails__search_docs` MCP tool

## Usage

**Auto-invoked** when agents need Rails concepts:
```
Agent: "How do I implement Action Cable subscriptions?"
*invokes rails-docs-search topic="action_cable"*
```

**Manual invocation**:
```
@rails-docs-search topic="active_record_associations"
@rails-docs-search topic="routing"
```

## Supported Topics

See `reference.md` for complete topic list. Common topics:

### Core Concepts
- `getting_started` - Rails basics and first app
- `active_record_basics` - ORM fundamentals
- `routing` - URL patterns and routes
- `controllers` - Request/response handling
- `views` - Templates and rendering

### Advanced Features
- `active_record_associations` - Relationships (has_many, belongs_to)
- `active_record_validations` - Data validation
- `active_record_callbacks` - Lifecycle hooks
- `action_mailer` - Email sending
- `action_cable` - WebSockets

### Testing & Security
- `testing` - Rails testing guide
- `security` - Security best practices
- `debugging` - Debugging techniques

### Deployment & Configuration
- `configuring` - Application configuration
- `asset_pipeline` - Asset management
- `caching` - Performance caching

## Search Process

### Step 1: Version Detection
```
Invokes: @rails-version-detector
Result: Rails 7.1.3
Maps to: https://guides.rubyonrails.org/v7.1/
```

### Step 2: Topic Mapping
```
Input: topic="active_record_associations"
Lookup: reference.md → "association_basics.html"
URL: https://guides.rubyonrails.org/v7.1/association_basics.html
```

### Step 3: Content Fetch

**Method 1: Context7 (Fastest)**:
```
Tool: context7_fetch
Query: "Rails [version] [topic]"
```

**Method 2: Ref (Token-Efficient)**:
```
Tool: ref_search_documentation
Query: "Rails [version] [topic] documentation"
Then: ref_read_url
```

**Method 3: Tavily (Search)**:
```
Tool: tavily_search
Query: "Rails [version] [topic] guide"
```

**Method 4: WebFetch (Fallback)**:
```
Tool: WebFetch
URL: [constructed URL from reference.md]
Prompt: "Extract sections about [specific query]"

Note: WebFetch has a built-in 15-minute cache for faster responses
when repeatedly accessing the same URL within a session.
```

### Step 4: Response Formatting
```markdown
## Rails Guide: Active Record Associations (v7.1)

### belongs_to
A `belongs_to` association sets up a one-to-one connection...

### has_many
A `has_many` association indicates a one-to-many connection...

Source: https://guides.rubyonrails.org/v7.1/association_basics.html
```

## Reference Lookup

**Topic → Guide URL mapping** in `reference.md`:

```yaml
active_record_associations:
  title: "Active Record Associations"
  url_path: "association_basics.html"
  version_support: "all"
  keywords: [has_many, belongs_to, has_one, through]

routing:
  title: "Rails Routing"
  url_path: "routing.html"
  version_support: "all"
  keywords: [routes, resources, namespace]
```

## Output Format

### Success Response
```markdown
## Rails Guide: [Topic Title] (v[X.Y])

[Fetched content from guide...]

### Key Points
- [Summary point 1]
- [Summary point 2]

**Source**: [full URL]
**Version**: [Rails version]
```

### Not Found Response
```markdown
## Topic Not Found: [topic]

Available topics:
- getting_started
- active_record_basics
- routing
[...more topics...]

Try: @rails-docs-search topic="[one of above]"
```

### Version Mismatch Warning
```markdown
## Rails Guide: [Topic] (v7.1)

⚠️ **Note**: Guide is for Rails 7.1, but project uses Rails 6.1.
Some features may not be available in your version.

[Content...]
```

## Implementation Details

**Tools used** (in order of preference):
1. **@rails-version-detector** - Get project Rails version
2. **Read** - Load `reference.md` topic mappings
3. **context7_fetch** (primary) - Fetch curated docs via Context7 MCP
4. **ref_search_documentation** (secondary) - Search Rails docs via Ref MCP
5. **tavily_search** (tertiary) - Optimized search via Tavily MCP
6. **WebFetch** (fallback) - Fetch guide content if MCPs not available
7. **Grep** (optional) - Search local cached guides if available

**Optional dependencies**:
- **context7-mcp**: Fastest, curated documentation
- **ref-tools-mcp**: Token-efficient documentation search
- **tavily-mcp**: Optimized search for LLMs
- If neither installed: Falls back to WebFetch (still works!)

**URL construction**:
```
Base: https://guides.rubyonrails.org/
Versioned: https://guides.rubyonrails.org/v7.1/
Guide: https://guides.rubyonrails.org/v7.1/routing.html
```

**Version handling**:
- Rails 8.x → `/v8.0/` (or latest if 8.0 not published)
- Rails 7.1.x → `/v7.1/`
- Rails 7.0.x → `/v7.0/`
- Rails 6.1.x → `/v6.1/`

**Caching strategy**:
- Cache fetched guide content for session
- Re-fetch if version changes
- Cache key: `{topic}:{version}`

**Prompt Caching (Opus 4.5 Optimized)**:
- Use 1-hour cache duration for extended thinking tasks
- Documentation content is stable - leverage longer cache windows
- Cache prefix: Include Rails version in system prompt for cache reuse
- Reduces token costs significantly for repeated lookups

## Error Handling

**Network failure**:
```markdown
⚠️ Failed to fetch guide from rubyonrails.org

Fallback: Check local knowledge or ask user for clarification.
URL attempted: [URL]
```

**Invalid topic**:
```markdown
❌ Unknown topic: "[topic]"

Did you mean: [closest match from reference.md]?

See available topics: @rails-docs-search list
```

**Version not supported**:
```markdown
⚠️ Rails [version] guides not available.

Using closest version: [fallback version]
Some information may differ from your Rails version.
```

## Integration

**Auto-invoked by**:
- All 7 Rails agents when they need conceptual information
- @rails-architect for architecture decisions
- User questions about "How do I..." or "What is..."

**Complements**:
- @rails-api-lookup (this skill = concepts, that skill = API details)
- @rails-pattern-finder (this skill = theory, that skill = code examples)

## Special Features

### Multi-topic search
```
@rails-docs-search topic="routing,controllers"
→ Fetches both guides and combines relevant sections
```

### Keyword search within topic
```
@rails-docs-search topic="active_record_associations" keyword="polymorphic"
→ Focuses on polymorphic association sections only
```

### List available topics
```
@rails-docs-search list
→ Returns all available topics from reference.md
```

## Testing

**Test cases**:
1. Topic="routing" + Rails 7.1 → Fetches v7.1 routing guide
2. Topic="unknown" → Returns error with suggestions
3. Network down → Graceful fallback
4. Rails 8.0 (future) → Uses latest available version
5. Multiple topics → Combines results

## Notes

- Guides content fetched live (not stored in plugin)
- Reference mappings maintained in `reference.md`
- Version-appropriate URLs ensure accuracy
- WebFetch tool handles HTML → Markdown conversion
- This skill focuses on **concepts**, use @rails-api-lookup for **API signatures**
