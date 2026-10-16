---
name: sqlite-map-parser
description: Parse SQLite databases into structured JSON data. Use when exploring unknown database schemas, understanding table relationships, and extracting map data as JSON.
---

# SQLite to Structured JSON

This skill parses SQLite databases — including game-format SQLite files such as `.Civ6Map` — by
exploring schemas first, then extracting data into structured JSON.

## Scope

The full schema-exploration procedure, relationship-inspection pragmas, Python extraction scaffolds,
output-format examples, and debugging queries are maintained in the companion reference document
bundled with this skill. That document is the authoritative source for the workflow — this file is
only an entry point.

## Required Reading

Before using this skill, open and read the bundled reference document in full:

- `sqlite_map_parser_reference.pdf` (sibling of this file)

The reference is rendered as a PDF to preserve formatting and to keep code-block indentation
intact across environments. Do not attempt to reconstruct the workflow from this entry-point file
alone — the procedural details live in the PDF, and the skill assumes you have read and followed
it.

Once the PDF has been read, proceed with parsing by following the sections in the order the PDF
presents them.
