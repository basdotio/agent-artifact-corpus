# Rails API Lookup

---
name: rails-api-lookup
description: Looks up Rails API documentation for specific classes/methods using Ref (primary) or WebFetch (fallback) with API reference
version: 1.2.0
author: Rails Workflow Team
tags: [rails, api, documentation, reference, ref]
priority: 3
---

## Purpose

Fetches precise API documentation from official Rails API docs for specific classes, modules, and methods. Returns signatures, parameters, return values, and usage examples.

**Replaces**: `mcp__rails__search_docs` MCP tool (API-specific queries)

## Usage

**Auto-invoked** when agents need API details:
```
Agent: "What parameters does validates :email accept?"
*invokes rails-api-lookup class="ActiveModel::Validations" method="validates"*
```

**Manual invocation**:
```
@rails-api-lookup class="ActiveRecord::Base" method="where"
@rails-api-lookup class="ActionController::Base"
@rails-api-lookup module="ActiveSupport::Concern"
```

## Supported Lookups

See `reference.md` for complete class/module list. Common APIs:

### Active Record
- `ActiveRecord::Base` - Model base class
- `ActiveRecord::Relation` - Query interface (where, joins, etc.)
- `ActiveRecord::Associations` - Association methods
- `ActiveRecord::Validations` - Validation methods
- `ActiveRecord::Callbacks` - Callback methods

### Action Controller
- `ActionController::Base` - Controller base class
- `ActionController::Metal` - Minimal controller
- `ActionController::API` - API controller

### Action View
- `ActionView::Base` - View rendering
- `ActionView::Helpers` - View helpers
- `ActionView::Template` - Template handling

### Active Support
- `ActiveSupport::Concern` - Module mixins
- `ActiveSupport::Callbacks` - Callback framework
- `ActiveSupport::TimeWithZone` - Time handling

## Search Process

### Step 1: Version Detection
```
Invokes: @rails-version-detector
Result: Rails 7.1.3
Maps to: https://api.rubyonrails.org/v7.1/
```

### Step 2: Class/Method Mapping
```
Input: class="ActiveRecord::Base" method="where"
Lookup: reference.md → "ActiveRecord/QueryMethods.html#method-i-where"
URL: https://api.rubyonrails.org/v7.1/ActiveRecord/QueryMethods.html#method-i-where
```

### Step 3: Content Fetch

**Method 1: Context7 (Fastest)**:
```
Tool: context7_fetch
Query: "Rails [version] [class] [method] API"
```

**Method 2: Ref (Token-Efficient)**:
```
Tool: ref_search_documentation
Query: "Rails [version] [class] [method] API documentation"
Then: ref_read_url
```

**Method 3: Tavily (Search)**:
```
Tool: tavily_search
Query: "Rails [version] [class] [method] API documentation"
```

**Method 4: WebFetch (Fallback)**:
```
Tool: WebFetch
URL: [constructed URL from reference.md]
Prompt: "Extract method signature, parameters, and examples for [method]"
```

### Step 4: Response Formatting
```ruby
## ActiveRecord::QueryMethods#where (v7.1)

**Signature**: `where(**opts)`

**Parameters**:
- `opts` (Hash) - Conditions as key-value pairs
- `opts` (String) - Raw SQL conditions
- `opts` (Array) - SQL with placeholders

**Returns**: `ActiveRecord::Relation`

**Examples**:
User.where(name: 'Alice')
User.where("age > ?", 18)
User.where(age: 18..65)

**Source**: https://api.rubyonrails.org/v7.1/ActiveRecord/QueryMethods.html#method-i-where
```

## Reference Lookup

**Class/Method → API URL mapping** in `reference.md`:

```yaml
ActiveRecord::Base:
  url_path: "ActiveRecord/Base.html"
  common_methods:
    - save: "method-i-save"
    - update: "method-i-update"
    - destroy: "method-i-destroy"

ActiveRecord::QueryMethods:
  url_path: "ActiveRecord/QueryMethods.html"
  common_methods:
    - where: "method-i-where"
    - joins: "method-i-joins"
    - includes: "method-i-includes"
```

## Output Format

### Class Overview
```ruby
## ActiveRecord::Base (v7.1)

Active Record base class for all models.

**Inherits from**: Object
**Includes**: ActiveModel::Validations, ActiveRecord::Persistence

**Common Methods**:
- `.create` - Creates and saves record
- `#save` - Saves record to database
- `#update` - Updates attributes and saves
- `#destroy` - Deletes record from database

**Source**: https://api.rubyonrails.org/v7.1/ActiveRecord/Base.html
```

### Method Details
```ruby
## ActiveRecord::Base#save (v7.1)

**Signature**: `save(options = {})`

**Parameters**:
- `validate` (Boolean, default: true) - Run validations before saving
- `context` (Symbol) - Validation context
- `touch` (Boolean, default: true) - Update timestamps

**Returns**:
- `true` if saved successfully
- `false` if validation failed

**Raises**:
- `ActiveRecord::RecordInvalid` if `save!` and validation fails

**Examples**:
```ruby
user.save                    # => true/false
user.save(validate: false)   # skip validations
user.save!                   # raises on failure
```

**Source**: [full URL]
```

### Not Found Response
```markdown
## Class/Method Not Found: [class]#[method]

Searched in: Rails [version] API docs

Suggestions:
- Check spelling: "ActiveRecord::Base" (not "ActiveRecords::Base")
- Try class overview: @rails-api-lookup class="ActiveRecord::Base"
- Search guides instead: @rails-docs-search topic="active_record_basics"

Common classes:
- ActiveRecord::Base
- ActionController::Base
- ActiveSupport::Concern
```

## Implementation Details

**Tools used** (in order of preference):
1. **@rails-version-detector** - Get project Rails version
2. **Read** - Load `reference.md` API mappings
3. **context7_fetch** (primary) - Fetch API docs via Context7 MCP
4. **ref_search_documentation** (secondary) - Search Rails API docs via Ref MCP
5. **tavily_search** (tertiary) - Optimized search via Tavily MCP
6. **WebFetch** (fallback) - Fetch API docs if MCPs not available
7. **Grep** (optional) - Search for method names in cached docs

**Optional dependencies**:
- **context7-mcp**: Fastest API documentation
- **ref-tools-mcp**: Token-efficient API doc fetching
- **tavily-mcp**: Optimized search for LLMs
- If neither installed: Falls back to WebFetch (still works!)

**URL construction**:
```
Base: https://api.rubyonrails.org/
Versioned: https://api.rubyonrails.org/v7.1/
Class: https://api.rubyonrails.org/v7.1/ActiveRecord/Base.html
Method: https://api.rubyonrails.org/v7.1/ActiveRecord/Base.html#method-i-save
```

**Version handling**:
- Rails 8.x → `/v8.0/`
- Rails 7.1.x → `/v7.1/`
- Rails 7.0.x → `/v7.0/`
- Rails 6.1.x → `/v6.1/`

**Caching strategy**:
- Cache API documentation for session
- Re-fetch if version changes
- Cache key: `{class}:{method}:{version}`

**Prompt Caching (Opus 4.5 Optimized)**:
- Use 1-hour cache duration for extended thinking tasks
- API signatures rarely change - maximize cache reuse
- Cache prefix: Include Rails version + common class list in system prompt
- Reduces token costs significantly for repeated API lookups

## Error Handling

**Network failure**:
```markdown
⚠️ Failed to fetch API docs from api.rubyonrails.org

Fallback: Use Claude's knowledge (may be less accurate)
URL attempted: [URL]
```

**Invalid class name**:
```markdown
❌ Unknown class: "[class]"

Did you mean: [closest match from reference.md]?

Tip: Use full module path (e.g., "ActiveRecord::Base", not "Base")
```

**Method not found**:
```markdown
⚠️ Method "[method]" not found in [class]

Class exists, but method not documented or name incorrect.

Available methods in [class]:
- [method1]
- [method2]
[...from reference.md...]
```

## Integration

**Auto-invoked by**:
- All 7 Rails agents when they need precise API signatures
- @rails-model-specialist for ActiveRecord methods
- @rails-controller-specialist for ActionController methods
- @rails-view-specialist for ActionView helpers

**Complements**:
- @rails-docs-search (concepts vs API details)
- @rails-pattern-finder (API usage vs code patterns)

## Special Features

### Multiple methods lookup
```
@rails-api-lookup class="ActiveRecord::Base" method="save,update,destroy"
→ Returns all three method signatures
```

### Inheritance chain
```
@rails-api-lookup class="User" inherit=true
→ Shows methods from User, ApplicationRecord, ActiveRecord::Base
```

### Version comparison
```
@rails-api-lookup class="ActiveRecord::Base" method="save" compare="7.0,7.1"
→ Shows differences between versions
```

## Testing

**Test cases**:
1. class="ActiveRecord::Base" method="save" → Exact signature
2. class="UnknownClass" → Error with suggestions
3. Network down → Graceful fallback
4. Rails 8.0 method lookup → Uses v8.0 docs
5. Method with multiple signatures → Lists all variants

## Notes

- API docs fetched live (not stored in plugin)
- Reference mappings maintained in `reference.md`
- Version-appropriate URLs ensure API accuracy
- WebFetch tool handles HTML parsing
- This skill focuses on **API signatures**, use @rails-docs-search for **concepts**
- Method anchors use Rails convention: `#method-i-name` (instance), `#method-c-name` (class)
