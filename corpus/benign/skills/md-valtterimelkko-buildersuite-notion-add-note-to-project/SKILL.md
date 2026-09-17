---
name: notion-add-note-to-project
description: Add a note to a project by updating the Project relation. Use when the user wants to organize a note under a project, link notes to projects, or move notes from inbox to a specific project in the Ultimate Brain system.
---

# Add Note to Project in Notion

Add a note to a project by updating the note's Project relation. This appends to existing project relations, allowing notes to belong to multiple projects.


## Prerequisites

Set the `NOTION_TOKEN` environment variable:
```bash
export NOTION_TOKEN="your-notion-integration-token"
```
[Get your token →](https://www.notion.so/my-integrations)
## When to Use

Use this Skill when the user wants to:
- Add a note to a project
- Organize inbox notes under specific projects
- Link an existing note to a project
- Move notes to project folders

## How to Execute

### Add Note by Names

```bash
python3 ~/.claude/scripts/notion/add_note_to_project.py --note-name "My Note" --project-name "My Project"
```

### Add Note by IDs

```bash
python3 ~/.claude/scripts/notion/add_note_to_project.py --note-id "NOTE_ID" --project-id "PROJECT_ID"
```

### Mixed (Name and ID)

```bash
python3 ~/.claude/scripts/notion/add_note_to_project.py --note-name "My Note" --project-id "PROJECT_ID"
```

## Behavior

- **Appends to existing relations**: If the note already belongs to other projects, the new project is added alongside them
- **Idempotent**: If the note is already in the specified project, returns success without duplicating
- **Name resolution**: Searches for exact matches first, then partial matches

## Handling Results

- If `success` is `true` and `already_related` is `true`: Note was already in the project
- If `success` is `true` and `already_related` is absent: Note was successfully added to project
- If multiple notes/projects match: Error includes list of matches for clarification

## Example Interaction

User: "Add my API notes to the Backend project"

1. Execute add_note_to_project.py with note and project names
2. Confirm the note was added to the project
3. Report the current project count for the note

## Fallback: Find IDs First

If name matching fails, use these scripts to find exact IDs:

```bash
# Find note ID
python3 ~/.claude/scripts/notion/search_notes.py --query "API notes"

# Find project ID
python3 ~/.claude/scripts/notion/search_projects.py --name "Backend"

# Or list all projects
python3 ~/.claude/scripts/notion/list_projects.py
```

## Important Notes

- Notes can belong to multiple projects
- Use `notion-list-project-notes` to verify the note appears in the project
- Use `notion-create-project` first if the project doesn't exist
