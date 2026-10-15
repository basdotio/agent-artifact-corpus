# ClickUp API notes (v2)

Read this file only when something goes wrong or behaves in a surprising way.

## Endpoints used (all GET)

| Purpose | Endpoint |
|---|---|
| Token owner | `/user` |
| Workspaces + members | `/team` |
| Space names | `/team/{team_id}/space` |
| Folders / lists / sprints (`--discover`) | `/space/{id}/folder`, `/space/{id}/list` |
| Tags of a space (`--discover`) | `/space/{id}/tag` |
| Tasks of one sprint | `/list/{list_id}/task?assignees[]=…&include_closed=true` |
| Tasks of a list / folder / space / tag | `/team/{team_id}/task?list_ids[]=… \| project_ids[]=… \| space_ids[]=… \| tags[]=…` (a folder is a "project" in the API) |
| Tasks of a user | `/team/{team_id}/task?assignees[]={user_id}&subtasks=true&include_closed=…&page=N` |
| Task comments | `/task/{task_id}/comment` |

- Auth header: `Authorization: <personal token>` (no `Bearer` prefix for `pk_` tokens).
- Pages hold up to 100 tasks. The response has `last_page`.
- Dates are Unix **milliseconds** as strings. The scripts turn them into local dates.
- "team" in the API means the same thing as "workspace" in the UI.

## Status types → report buckets

| `status.type` | Bucket |
|---|---|
| `open` | todo |
| `custom` | in_progress |
| `done`, `closed` | done (only when closed inside the period) |

A workspace that uses custom names ("QA", "Review") still maps correctly, because
the mapping uses the status **type**, not the name.

## Common problems

| Symptom | Cause / fix |
|---|---|
| HTTP 401 | Token revoked or mistyped. If `CLICKUP_API_TOKEN` is set in the environment, it is used only when no token is saved, so an old variable cannot override a good saved token. |
| HTTP 429 | Rate limit (about 100 requests/min on most plans). The client waits and retries. Lower `--max-comment-tasks` for large accounts. |
| Tasks missing | The task is not *assigned* to the user (only watching does not count), it lives in an archived list, or it was closed outside the period. |
| Time tracked is 0 | The workspace does not use time tracking, or the time was logged by someone else. |
| Points are empty | Sprint points ClickApp is off. The report shows 0. |
