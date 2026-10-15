# Demotion and promotion between layers

On-demand reference for the no-false-flags skill. How to move content down (or
up) the layers as it proves narrow, stale, or genuinely cross-cutting.

## The direction that matters: down

Most context systems only add. The missing discipline is moving content *down* as
it proves it does not earn the always-loaded slot:

```
global rule  ->  path-scoped rule  ->  on-demand reference  ->  archived
```

## Demotion steps

1. **Identify the file** (from the audit, or when it trips something / gets in the
   way). Find it by name and count, without reading it into the conversation: see
   "Measure without dumping" in [surface-audit.md](surface-audit.md).
2. **Decide the target layer by relevance** — use the decision tree in
   [loading-layers.md](loading-layers.md).
3. **Move the file** to the target location.
4. **Leave a short pointer** where it is still discoverable — a one-line "for X,
   read `references/...`". The pointer is short and can stay always loaded; the
   heavy content does not.
5. **Verify** that nothing which always loads still inlines the full content,
   with the same `grep -c` from the audit rather than reading the files back.

## The import caveat (important)

Pulling a file in with an `@path` import **organizes but does NOT save context**:
the imported content is loaded at load time just the same. So splitting a big
always-loaded file into imported pieces does not shrink what loads. To actually
reduce the loaded surface, the content must either move to a layer that is read on
demand (`references/`) or be **path-scoped** so it only loads for the relevant
directory.

## Promotion (rarer)

If something in one project's memory turns out to apply to every project and is
short and operational, promote it to a global rule. Promotion is the rare case;
demotion is the common need, because the pressure is always to add.
