---
name: empty-commit
description: Create an empty commit for testing purposes
params:
  - name: agf_id
    description: The unique identifier for this task (e.g., agf-001)
    required: true
  - name: prompt
    description: The task description to include in the commit message
    required: true
---

# Empty Commit

Create an empty commit to be used in testing or marking task milestones.

## Instructions

Extract parameters:
- `agf_id` - The unique task identifier
- `prompt` - The task description

1. **Validate Parameters**: If `agf_id` or `prompt` is not provided, stop and ask the user to provide them
2. **Truncate Prompt**: Create `truncated_prompt` by taking the first 5 to 10 words of `prompt`
   - Add three ellipses (...) if the truncated prompt does not contain all the words in `prompt`
3. **Create Empty Commit**: Create a single empty commit using:
   ```bash
   git commit --allow-empty -m "<truncated_prompt> (task: <agf_id>)"
   ```
   - **DO NOT** indicate co-authoring attributions in the commit
4. **Save Commit SHA**: Extract the short version of the commit SHA

## Output Format

IMPORTANT: Return a JSON object with this structure:

```json
{
  "commit_sha": "<short_commit_sha>",
  "commit_message": "<truncated_prompt> (task: <agf_id>)"
}
```

### Example Output

```json
{
  "commit_sha": "0acf3cf",
  "commit_message": "add create_github_pr wrapper method with... (task: agf-001)"
}
```
