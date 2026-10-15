# 💡 Claude Thread Continuity Examples

This directory contains practical examples of how to use the Claude Thread Continuity MCP server.

## Example 1: Starting a New Web Development Project

```
save_project_state: project_name="my-react-app", current_focus="Setting up React TypeScript project", technical_decisions=["Using Vite for build tool", "TypeScript for type safety", "Tailwind CSS for styling"], files_modified=["package.json", "vite.config.ts", "src/App.tsx"], next_actions=["Create routing structure", "Set up authentication", "Design component library"]
```

## Example 2: Continuing After Token Limit

When your thread hits the token limit, start a new conversation and restore context:

```
load_project_state: project_name="my-react-app"
```

This will output:
```
📂 **Project: my-react-app**

🎯 **Current Focus:** Setting up React TypeScript project

🔧 **Technical Decisions:**
  • Using Vite for build tool
  • TypeScript for type safety
  • Tailwind CSS for styling

📁 **Files Modified:**
  • package.json
  • vite.config.ts
  • src/App.tsx

✅ **Next Actions:**
  • Create routing structure
  • Set up authentication
  • Design component library

🕒 **Last Updated:** 2025-06-07T10:30:00Z
```

## Example 3: Managing Multiple Projects

```bash
# Work on different projects
save_project_state: project_name="mobile-app", current_focus="Flutter UI development"
save_project_state: project_name="api-backend", current_focus="Database schema design"

# List all active projects
list_active_projects

# Get quick summary of specific project
get_project_summary: project_name="mobile-app"
```

## Example 4: Learning and Research Project

```
save_project_state: project_name="rust-learning", current_focus="Understanding ownership and borrowing", technical_decisions=["Starting with small CLI tools", "Using Cargo for project management"], files_modified=["main.rs", "Cargo.toml"], next_actions=["Complete ownership exercises", "Build a simple file processor", "Learn about lifetimes"], conversation_summary="Learning Rust fundamentals, currently working through ownership concepts with practical examples"
```

## Example 5: Complex Debugging Session

```
save_project_state: project_name="payment-bug-fix", current_focus="Investigating transaction timeout issues", technical_decisions=["Added detailed logging to payment service", "Implemented circuit breaker pattern"], files_modified=["payment_service.py", "config.yaml", "requirements.txt"], next_actions=["Test with load testing tool", "Review database connection pooling", "Deploy to staging environment"], conversation_summary="Payment service experiencing timeouts under load. Identified connection pool exhaustion as likely cause. Implementing fixes and monitoring improvements."
```

## Example 6: Writing Project

```
save_project_state: project_name="novel-draft", current_focus="Character development for protagonist", technical_decisions=["First person narrative", "Present tense", "Three-act structure"], files_modified=["chapter-1.md", "character-notes.md", "plot-outline.md"], next_actions=["Develop antagonist backstory", "Write dialogue scenes", "Review pacing of chapter 2"], conversation_summary="Working on a science fiction novel. Protagonist is a space engineer dealing with AI consciousness themes. Currently building emotional depth and relationships."
```

## Automatic Triggers

The server automatically saves state when these patterns are detected:

- **File Operations:** "I created/modified/updated [filename]"
- **Technical Decisions:** "I decided to use/chose/selected [technology/approach]"
- **Milestones:** "Completed/finished/implemented [feature/task]"
- **Message Count:** Every 10 messages as a fallback

## Best Practices

1. **Use Consistent Project Names:** Stick to kebab-case like "my-web-app" or "python-ml-project"

2. **Keep Focus Clear:** Make current_focus actionable and specific
   - ✅ "Implementing user authentication with JWT"
   - ❌ "Working on backend stuff"

3. **Document Technical Decisions:** Include the reasoning
   - ✅ "Using PostgreSQL for ACID compliance and complex queries"
   - ❌ "Using PostgreSQL"

4. **Actionable Next Steps:** Be specific about what to do next
   - ✅ "Add input validation to user registration form"
   - ❌ "Fix bugs"

5. **Rich Context Summary:** Help future-you understand the situation
   - ✅ "Building an e-commerce API. Currently implementing payment processing with Stripe. Discovered webhook validation issues that need addressing before production deployment."
   - ❌ "API work"

## Advanced Usage

### Updating Project State

```
# Load existing state
load_project_state: project_name="my-project"

# Continue working...

# Update with new progress
save_project_state: project_name="my-project", current_focus="New focus area", technical_decisions=["Previous decisions", "New decision"], files_modified=["existing files", "new-file.js"], next_actions=["Updated action list"]
```

### Project Handoffs

When collaborating or switching team members:

```
save_project_state: project_name="team-project", current_focus="API documentation review", conversation_summary="John was working on user authentication endpoints. All core functionality complete but needs API documentation review before client integration. Main challenge is ensuring consistent error handling across all endpoints. Next developer should focus on OpenAPI spec completion."
```

This creates a comprehensive handoff document that any team member can load and understand immediately.
