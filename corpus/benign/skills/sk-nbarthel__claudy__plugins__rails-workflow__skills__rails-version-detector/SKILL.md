# Rails Version Detector

---
name: rails-version-detector
description: Detects Rails version from project files (Gemfile.lock, Gemfile, or .ruby-version)
version: 1.1.0
author: Rails Workflow Team
tags: [rails, version, detection, helper]
priority: 2
---

## Purpose

Automatically detects the Rails version in the current project by inspecting:
1. `Gemfile.lock` (preferred - exact version)
2. `Gemfile` (fallback - version constraint)
3. `.ruby-version` or `.tool-versions` (Ruby version hint)

Returns version information for use by other skills and agents.

## Usage

This skill is **auto-invoked** by other Rails skills when they need version information.

**Manual invocation** (rarely needed):
```
@rails-version-detector
```

## Detection Strategy

### Priority 1: Gemfile.lock (Exact Version)
```ruby
# Searches for:
rails (7.1.3)
  actioncable (= 7.1.3)
  actionmailbox (= 7.1.3)
  ...
```

**Extraction logic**:
- Pattern: `rails \((\d+\.\d+\.\d+)\)`
- Returns: Exact version (e.g., "7.1.3")

### Priority 2: Gemfile (Version Constraint)
```ruby
# Searches for:
gem "rails", "~> 7.1.0"
gem 'rails', '>= 7.0.0', '< 8.0'
```

**Extraction logic**:
- Pattern: `gem ['"]rails['"],\s*['"]([^'"]+)['"]`
- Returns: Version constraint (e.g., "~> 7.1.0")
- Interprets: "~> 7.1.0" → "7.1.x"

### Priority 3: Ruby Version (Heuristic)
```ruby
# .ruby-version or .tool-versions
ruby 3.2.2
```

**Mapping**:
- Ruby 3.3.x → Rails 7.1+ or 8.0+
- Ruby 3.2.x → Rails 7.0+
- Ruby 3.1.x → Rails 7.0+
- Ruby 3.0.x → Rails 6.1+ or 7.0
- Ruby 2.7.x → Rails 6.0 or 6.1

**Returns**: Estimated range (e.g., "7.0 or 7.1")

## Output Format

### Success Response
```json
{
  "version": "7.1.3",
  "source": "Gemfile.lock",
  "confidence": "exact",
  "major": 7,
  "minor": 1,
  "patch": 3
}
```

### Constraint Response
```json
{
  "version": "~> 7.1.0",
  "source": "Gemfile",
  "confidence": "constraint",
  "interpreted_as": "7.1.x",
  "major": 7,
  "minor": 1
}
```

### Heuristic Response
```json
{
  "version": "7.0-7.1",
  "source": ".ruby-version",
  "confidence": "heuristic",
  "ruby_version": "3.2.2",
  "possible_rails": ["7.0", "7.1"]
}
```

### Not Found Response
```json
{
  "version": null,
  "source": null,
  "confidence": "none",
  "error": "No Rails version detected. Is this a Rails project?"
}
```

## Implementation

**Tool usage**:
- `Read` tool to read Gemfile.lock, Gemfile, .ruby-version
- `Grep` tool to search for version patterns
- Fallback to `Bash` if needed: `bundle show rails | grep 'rails-'`

**Caching**:
- Version detection results cached for session
- Re-check if Gemfile.lock modified (check mtime)

## Error Handling

**Gemfile.lock missing**:
- Fallback to Gemfile
- Warn: "Gemfile.lock not found. Run `bundle install` for exact version."

**No version found**:
- Return error response
- Suggest: "Ensure `gem 'rails'` in Gemfile"

**Multiple Rails versions**:
- Return first match (main Rails gem)
- Ignore: railties, actionpack (these are sub-gems)

## Integration

**Auto-invoked by**:
- @rails-docs-search (to fetch correct version docs)
- @rails-api-lookup (to search version-specific APIs)
- @rails-pattern-finder (to find version-appropriate patterns)
- All 7 Rails agents (to ensure version-compatible code generation)

**Manual use case**:
```
User: "What Rails version is this project using?"
Assistant: *invokes @rails-version-detector*
          "This project uses Rails 7.1.3 (detected from Gemfile.lock)"
```

## Testing

**Test cases**:
1. Rails 7.1.3 in Gemfile.lock → Exact version
2. `~> 7.1.0` in Gemfile → Interpreted as 7.1.x
3. Ruby 3.2.2 only → Heuristic: 7.0-7.1
4. No Rails → Error response
5. Rails 8.0.0 → Correct major version detection

## Notes

- This skill replaces the need for `mcp__rails__get_rails_info` MCP tool
- Version detection is fast (< 1 second)
- Results cached per session to avoid repeated file reads
- Confidence levels help downstream skills decide if they need clarification from user
