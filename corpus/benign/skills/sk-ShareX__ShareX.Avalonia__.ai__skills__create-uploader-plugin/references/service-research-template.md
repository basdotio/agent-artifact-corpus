# Service Research Template

Fill this out before implementation when the service is new, niche, or has multiple API choices.

## 1. Existing Repo Support

- Search terms used:
- Existing ShareX/XerahS support found:
- Legacy uploader files or docs:
- Keep, replace, or supersede:

## 2. Official Sources

- Auth/login docs:
- Upload/file API docs:
- Sharing/public-link docs:
- Explorer/listing docs:
- Rate-limit/error docs:
- SDK or API version notes:

Use official vendor docs first. Use third-party blog posts only to clarify gaps, not as the authority.

## 3. Auth Model

- API key / bearer token / OAuth / device flow / browser login / app password:
- Token refresh needed:
- Secret material to store:
- Can secrets live in `ISecretStore` cleanly:

## 4. Upload Model

- Single-request upload endpoint:
- Multipart or binary body:
- Chunked/resumable upload support:
- Required headers:
- Folder/path semantics:
- File overwrite behavior:

## 5. Share And URL Model

- Public URL available directly after upload:
- Separate share creation API required:
- Password or expiry supported:
- Canonical URL shape:

## 6. Explorer Capability

- Can list folders/files:
- Can create folders:
- Can delete:
- Can download/read metadata:
- Stable enough for `IUploaderExplorer`:

## 7. Native Vs Compatibility Decision

- Compatibility option considered:
- Native API option considered:
- Why native is better, or why compatibility is sufficient:
- Known gaps or tradeoffs:

Prefer native APIs when they improve:

- authentication safety or UX
- resumable uploads or large-file support
- public-link generation
- explorer fidelity
- capability detection
- policy handling

## 8. Proposed Plugin Shape

- Provider class:
- Uploader class:
- Config model fields:
- Secret names:
- Needs custom config UI:
- Needs `IUploaderExplorer`:
- Needs `IInstanceSecretMigrator`:

## 9. Verification Plan

- Small-file upload test:
- Large-file/chunked upload test:
- Public-link/share test:
- Explorer test:
- Failure-path test:
