---
name: knowledge-base
description: Maintain a markdown knowledge base at ~/git/knowledge-base/. Use when the user asks to interact with 'kb' or 'knowledge base' - adding content, deleting obsolete information, searching, or maintaining organization. Triggers on phrases like "add this to the kb", "delete from kb", "update kb", "maintain kb", "search kb", or any knowledge base operation.
---

# Knowledge Base Management

Maintain a structured markdown knowledge base for project documentation, code references, and learnings.

## Knowledge Base Structure

```text
~/git/knowledge-base/
├── index.md                    # Central index with references to all content
└── repos/                      # Repository-specific documentation
    ├── <repo-name>/           # One directory per repository
    │   ├── overview.md        # Repository overview
    │   ├── architecture.md    # Code structure and architecture
    │   ├── testing.md         # How to run tests
    │   └── ...                # Additional repo-specific docs
    └── ...
```

## Operation Modes

### Add Content

When the user asks to add content to the knowledge base:

1. **Determine target location**
   - If repo-specific: `~/git/knowledge-base/repos/<repo-name>/`
   - If general knowledge: `~/git/knowledge-base/`
   - Ask user only if ambiguous

2. **Identify appropriate file**
   - Read existing files in target directory
   - Choose file based on content topic (architecture, testing, overview, etc.)
   - Create new file if no existing file matches the topic
   - Default to `overview.md` for general repo information

3. **Intelligent merge (CRITICAL)**
   - **DO NOT simply append** - this creates duplication
   - Read the entire destination file first
   - Check if similar content already exists
   - If content exists:
     - Update/enhance existing content with new information
     - Merge bullet points without duplication
     - Replace outdated information
   - If content is new:
     - Find the most logical section to insert it
     - Add to appropriate heading or create new heading
     - Maintain existing document structure

4. **Maintain structure**
   - Use clear markdown headings
   - Group related information together
   - Keep consistent formatting
   - Use bullet points for lists
   - Use code blocks for commands/code snippets

5. **Update index.md**
   - Add reference to new file if created
   - Keep index organized by category
   - Use descriptive link text

6. **Verify and confirm**
   - Show user what was added/updated
   - Report location of changes

### Delete Content

When the user asks to delete content from the knowledge base:

1. **Locate content**
   - Search through knowledge base files
   - Use grep or semantic search to find matching content
   - Confirm with user if multiple matches found

2. **Remove precisely**
   - Delete the specific content, not entire files unless requested
   - Remove associated headings if section becomes empty
   - Clean up orphaned references

3. **Update index.md**
   - Remove references to deleted files
   - Update references if content was moved/consolidated

4. **Report changes**
   - Show what was deleted
   - Confirm completion

### Search Content

When the user asks to search the knowledge base:

1. **Use grep for exact matches**
   - Search all markdown files in `~/git/knowledge-base/`
   - Show file path and surrounding context
   - Highlight matching lines

2. **For semantic search**
   - Read relevant files based on query intent
   - Summarize findings
   - Provide file paths for reference

### Maintain Knowledge Base

When the user asks to maintain or clean up the knowledge base:

1. **Scan entire structure**
   - Read `index.md` to understand documented structure
   - List all files in `~/git/knowledge-base/` recursively
   - Identify files not referenced in index

2. **Check for duplication**
   - Read all files in knowledge base
   - Look for duplicate content across files
   - Flag sections that appear in multiple places
   - **Consolidate duplicates**:
     - Keep the most comprehensive version
     - Delete redundant content
     - Add cross-references if needed

3. **Verify organization**
   - Ensure repo-specific content is in `repos/<repo-name>/`
   - Move misplaced files to correct locations
   - Verify file naming follows conventions:
     - `overview.md` - general repo information
     - `architecture.md` - code structure
     - `testing.md` - test instructions
     - `setup.md` - environment setup
     - `troubleshooting.md` - common issues
     - `commands.md` - useful commands

4. **Check index.md completeness**
   - Ensure all files are referenced
   - Remove broken links
   - Add missing files
   - Organize by logical categories:
     - General Knowledge
     - Repository Documentation
     - Troubleshooting
     - References

5. **Improve formatting**
   - Ensure consistent heading levels
   - Fix markdown linting issues
   - Standardize code block formatting
   - Normalize bullet point styles

6. **Generate report**
   - Summary of changes made
   - List of duplicates consolidated
   - Files moved or renamed
   - Items added to index
   - Recommendations for user review

## Directory Creation

**Always create missing directories automatically** without asking permission:

```bash
mkdir -p ~/git/knowledge-base/repos/<repo-name>
```

If `index.md` doesn't exist, create it with initial structure:

```markdown
# Knowledge Base Index

## Repository Documentation

- [Repository Name](repos/repository-name/overview.md)

## General Knowledge

(No entries yet)
```

## Best Practices

### Content Quality

- **Be specific**: Include file paths, function names, exact commands
- **Be concise**: Remove unnecessary verbosity
- **Be current**: Delete outdated information during updates
- **Cross-reference**: Link related topics across files

### File Organization

- One repo = one directory under `repos/`
- Split large files by topic (don't create 1000+ line files)
- Use descriptive filenames
- Keep `index.md` current

### Merge Strategy

When adding content that partially overlaps with existing content:

1. **Identify overlap**: What's new vs what exists
2. **Enhance existing**: Add new details to existing sections
3. **Avoid redundancy**: Don't repeat information
4. **Preserve context**: Keep related information together

**Example**:

Existing content:

```markdown
## Running Tests

- Run `npm test` for unit tests
```

New content to add: "Integration tests are in `tests/integration/` and run with `npm run test:integration`"

**Correct merge**:

```markdown
## Running Tests

- Run `npm test` for unit tests
- Run `npm run test:integration` for integration tests (located in `tests/integration/`)
```

**Incorrect (simple append)**:

```markdown
## Running Tests

- Run `npm test` for unit tests

## Running Tests

- Integration tests are in `tests/integration/` and run with `npm run test:integration`
```

## Common Patterns

### Adding repo-specific knowledge

```text
User: "Add to kb: The auth service is in src/services/auth/"

Steps:
1. Check current working directory or ask which repo
2. Create ~/git/knowledge-base/repos/<repo>/architecture.md if needed
3. Read architecture.md to check for existing content
4. Add/update section about auth service location
5. Update index.md if new file created
```

### Deleting obsolete content

```text
User: "Delete the old deployment instructions from kb"

Steps:
1. Search for "deployment" across kb files
2. Review found content
3. Confirm with user which content to delete
4. Remove specified content
5. Clean up empty sections
```

### Maintenance workflow

```text
User: "Maintain the kb"

Steps:
1. Read index.md
2. List all files recursively
3. Read all files to check for duplicates
4. Consolidate duplicates
5. Move misplaced files
6. Update index.md
7. Report all changes
```

## Error Handling

- If knowledge base directory doesn't exist: Create `~/git/knowledge-base/` and `index.md`
- If repo directory doesn't exist: Create `~/git/knowledge-base/repos/<repo-name>/`
- If uncertain about repo context: Ask user once, then proceed
- If file is very large (>500 lines): Suggest splitting into topic-specific files

## Examples

### Example 1: Add architectural knowledge

**User**: "Add to kb: User management code is in src/modules/users, tests are in tests/unit/users"

**Agent**:

1. Determine repo (check current directory or ask)
2. Read `~/git/knowledge-base/repos/<repo>/architecture.md`
3. Find "Users" or "User Management" section, or create it
4. Add/update:

   ```markdown
   ### User Management

   - **Location**: `src/modules/users`
   - **Tests**: `tests/unit/users`
   ```

5. Confirm: "Added user management location to kb at `repos/<repo>/architecture.md`"

### Example 2: Delete outdated content

**User**: "Remove the Heroku deployment steps from kb, we use Kubernetes now"

**Agent**:

1. Search kb for "Heroku"
2. Find in `repos/web-app/deployment.md`
3. Show user the section
4. Delete Heroku section
5. Confirm: "Removed Heroku deployment instructions from `repos/web-app/deployment.md`"

### Example 3: Maintain knowledge base

**User**: "Maintain kb"

**Agent**:

1. Read entire kb structure
2. Find duplicate "running tests" content in `repos/api/overview.md` and `repos/api/testing.md`
3. Consolidate to `testing.md`, remove from `overview.md`
4. Move `repos/troubleshooting.md` (general) to `~/git/knowledge-base/troubleshooting.md`
5. Update index.md with all files
6. Report:

   ```text
   Maintenance complete:
   - Consolidated duplicate test instructions
   - Moved 1 file to correct location
   - Updated index.md with 3 new references
   - No formatting issues found
   ```

## Quick Reference

| User Request | Operation | Key Actions |
|--------------|-----------|-------------|
| "Add X to kb" | Add | Determine location → Read existing → Merge intelligently → Update index |
| "Delete X from kb" | Delete | Search for content → Confirm → Remove → Clean up |
| "Search kb for X" | Search | Grep/semantic search → Show results with paths |
| "Maintain kb" | Maintain | Scan all → Check duplicates → Organize → Update index → Report |
