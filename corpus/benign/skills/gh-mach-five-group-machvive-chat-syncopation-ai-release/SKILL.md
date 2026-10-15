---
name: release
description: 'Release a new version of this npm package. Use when: releasing, publishing to npm, bumping the version, cutting a tag, or when the user says release, publish, ship it, or bump version. Enforces the trusted-publishing (OIDC) flow — never uses an npm token.'
argument-hint: 'patch | minor | major'
---

# Release

Publish a new version of `@machfivetechchicago/machvive-chat-syncopation-ai` via GitHub Actions trusted publishing (OIDC). **There is no npm token and none may be created — never ask for one, never accept one pasted into chat.**

## Procedure

Run these steps in order. Stop at the first failure.

### 1. Review the staged diff

```bash
git status --short && git diff --cached --stat
```

Never `git add -A` unread — an unread stage once shipped a self-dependency to npm. Confirm no stray files and no `dependencies` block in [package.json](../../../package.json) or `package-lock.json` (an external `npmi` script re-adds `@machfivetechchicago/machvive-webmcp-ai`; remove it from both files if present — never relax the test).

### 2. Run the suite

```bash
npm test
```

`prepublishOnly` also runs it, but a failure here reads as a test failure, not a publish failure.

### 3. Documentation sweep — same commit, not later

Docs drift with no symptom. If the release added/changed a component or API, update in the same commit:

- [README.md](../../../README.md) — component table, feature list
- [design/wiki/](../../../design/wiki/) — then run `design/wiki/push-wiki.sh`
- [plugins/machvive-chat-syncopation/skills/](../../../plugins/machvive-chat-syncopation/skills/) — the Claude skill
- Any claim of absence ("no network requests", "no dependencies") must have a test asserting it.

### 4. Bump, tag, push

Use the version argument given (`patch` default if unclear — ask if the change surface suggests `minor`):

```bash
npm version <patch|minor|major>
git commit -am "release: v<x.y.z>" && git tag -a v<x.y.z> -m "v<x.y.z>"
git push origin main --follow-tags
```

The tag **must** match `package.json` `version` — [publish.yml](../../../.github/workflows/publish.yml) guards this and fails the run on mismatch.

### 5. Watch the workflow

```bash
gh run watch
```

If the tag push did not trigger it: `gh workflow run publish.yml --ref v<x.y.z>`.

### 6. Verify — expect propagation lag

Registry propagation lags a minute or more. Poll rather than assuming failure:

```bash
npm view @machfivetechchicago/machvive-chat-syncopation-ai version
```

A red "verify attestation" step immediately after a good publish means "not visible yet", not a bad release.

### 7. Smoke-test the published shape

A passing suite says nothing about whether the published shape resolves. In an empty temp project:

```bash
mkdir /tmp/mcs-smoke && cd /tmp/mcs-smoke && npm init -y
npm install @machfivetechchicago/machvive-chat-syncopation-ai@latest
```

Then import the entry points exercised by the release and confirm they resolve. If the release added an API, exercise it in a real page. Report the installed version and the import results.

## Never do

- Create, request, or accept an npm token (classic tokens were removed Nov 2025; OIDC is the mechanism).
- Rename [publish.yml](../../../.github/workflows/publish.yml) — the npmjs.com trusted-publisher config is bound to that filename; renaming breaks publishing until the npm config is updated.
- `npm publish` from a laptop for a real release.
- Relax [test/package.test.js](../../../test/package.test.js) to make a release pass.
