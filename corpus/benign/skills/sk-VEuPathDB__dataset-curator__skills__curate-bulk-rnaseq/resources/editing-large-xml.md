# Editing Large XML Files

This guide covers efficient editing of large XML files (thousands to tens of thousands of lines) in the VEuPathDB repositories.

## Key Principle

**Do NOT read the entire file into context.** Large XML files should be edited by:
1. Getting the line count
2. Reading only the relevant section
3. Using the Edit tool with a unique anchor

## Ask the Curator: First or Last?

Before inserting a new XML element, **ask the curator** where they prefer new entries:

- **First**: Insert after the opening tag (e.g., after `<contacts>` or `<datasetPresenters>`)
- **Last**: Insert before the closing tag (e.g., before `</contacts>` or `</datasetPresenters>`)

Different teams may have different conventions. Don't assume.

## Insertion at End (before closing tag)

Use this when the curator prefers new entries at the end.

### Step 1: Get line count and read the end

```bash
wc -l path/to/file.xml
```

Then use the Read tool with offset/limit. For example, if the file has 40,716 lines:

```
Read(file_path="path/to/file.xml", offset=40666, limit=50)
```

### Step 2: Edit with unique anchor

Match the last existing element AND the closing tag to create a unique anchor:

```xml
  </lastElement>
</rootElement>
```

Insert your new element between them.

## Insertion at Start (after opening tag)

Use this when the curator prefers new entries at the beginning.

### Step 1: Read the beginning

```
Read(file_path="path/to/file.xml", limit=100)
```

### Step 2: Edit with unique anchor

Match the opening tag AND the first existing element:

```xml
<rootElement>
  <firstElement ...>
```

Insert your new element between them.

## Checking for Duplicates

Before inserting, always check if the entry already exists:

```bash
grep -n "unique_identifier" path/to/file.xml
```

If found, you may need to update the existing entry rather than insert a new one.

## Common Large Files

| File | Typical Size | Root Element |
|------|-------------|--------------|
| allContacts.xml | ~40,000 lines | `<contacts>` |
| {Project}.xml presenters | ~5,000-15,000 lines | `<datasetPresenters>` |
