# Issue Tracker Integration (optional)

The skill works without any integration. When the session has an MCP server or tool for the team's issue tracker, it can also open the ticket.

## Flow
1. **Detect** — check whether a tracker tool is available (Jira/Atlassian, Azure DevOps, GitHub Issues, GitLab, Linear, YouTrack, ClickUp…). If none, skip this file.
2. **Collect target info** — project key / repository / team, issue type (usually *Bug*), and any required custom fields. Ask only for what the tool requires and you can't infer.
3. **Look for duplicates** — if the tool supports search, search open issues using the module + key words of the title. If likely duplicates exist, show them and ask whether to proceed, comment on the existing one, or stop.
4. **Confirm** — show the final report and the field mapping. Wait for an explicit "yes".
5. **Create** — create the issue, attach evidence if the tool supports attachments, and link related items (story, test case).
6. **Return** — reply with the ticket key and link. Offer to also save the Markdown file as a local record.

## Field mapping

| Report field | Jira | Azure DevOps | GitHub Issues | Linear |
|---|---|---|---|---|
| Title | Summary | Title | Title | Title |
| Body sections | Description | Repro Steps / Description | Body | Description |
| Severity | Severity (custom field) or label | Severity | Label `severity:*` | Label |
| Priority | Priority | Priority | Label `priority:*` | Priority |
| Module | Component | Area Path | Label | Team / Project |
| Environment | Environment | System Info | Body section | Body section |
| Labels | Labels | Tags | Labels | Labels |
| Related to | Issue links | Related links | Linked issues / mentions | Relations |

Field names vary by configuration — when unsure, put the value in the description instead of guessing a custom field.

## Safety rules
- Never create, edit or close tickets without explicit user confirmation.
- Never send unmasked sensitive data to the tracker.
- If creation fails, keep the report in chat and show the tool's error message.
