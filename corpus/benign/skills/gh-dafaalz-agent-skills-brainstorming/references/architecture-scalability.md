# Architecture scalability and state lifecycle

Evaluate data scaling, network efficiency, and state persistence when formulating technical approaches.

## 1. Data volume and pagination boundaries

When designing interfaces or endpoints handling list data, evaluate dataset growth:

| Anticipated record count | Architectural pattern | Avoid substituting |
|---|---|---|
| Less than 50 static items | Client-side memory sorting or array filtering | Heavy server roundtrips for trivial dropdown lists |
| 50 to 500 items | Simple server pagination with limit and offset query params | Dumping full record collections over wire |
| Greater than 500 items | Server-side datatables, cursor-based pagination, or chunked indexing | Client-side memory loading, unindexed table scans |

Key rules for server-side tables:
1. Push sorting, filtering, and pagination into the database query layer (using indexes on sort columns).
2. Transmit metadata including total count, per-page limit, and current page pointer in the response payload.
3. For asynchronous UI table updates, use AJAX or Inertia partial reloads without destroying page context.

## 2. Interactive state lifecycle and persistence

Prevent state desynchronization across client actions and page reloads:

1. Optimistic updates must include rollback logic. If an API request to toggle state fails or returns an unauthorized status, revert the local UI state immediately.
2. Verify authorization boundaries on both write and delete endpoints. Never assume the frontend user token is automatically trusted by state-altering backend routes.
3. Cold reload test. Always trace how the frontend reconstructs state after a full browser reload (`F5`). Persisted entities must rehydrate from authoritative backend storage, not transient memory or unverified local storage.

## 3. Safe document transformations

When designing automation scripts or data pipelines that update markdown, configuration files, or code:

1. Never use brittle regular expressions to parse nested or structured formats (such as HTML, Markdown note trees, or AST nodes).
2. Use dedicated structural parsers or append-only architectures (such as appending new notes with explicit flags or metadata prefixes) to prevent file corruption.
