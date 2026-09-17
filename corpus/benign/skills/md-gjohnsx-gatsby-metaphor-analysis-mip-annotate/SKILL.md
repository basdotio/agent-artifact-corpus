---
name: mip-annotate
description: Phase 2 of MIP pipeline - Orchestrate parallel annotation of all 9 chapters using subagents. Each chapter analyzed independently for metaphors.
allowed-tools: Task, Read, Write, Bash
---

# MIP Annotation Phase

Orchestrate parallel metaphor annotation across all 9 chapters of *The Great Gatsby*.

## Your Task

Spawn 9 parallel subagents using the **Task tool** to analyze each chapter independently. Each subagent applies the MIP (Metaphor Identification Procedure) and outputs structured JSON.

## Critical Implementation

You MUST use the Task tool to spawn 9 subagents in parallel. Example:

```
Use Task tool with subagent_type: "general-purpose" for each chapter
```

## Subagent Instructions Template

Each subagent should receive these instructions:

```
You are annotating Chapter X of The Great Gatsby for metaphors using MIP.

Read: book/chapters/chapter-0X.txt
Read: mip-analysis/research-notes.md (for procedure and seed systems)

Apply MIP to identify 8-15 significant metaphors. For each:

1. Read surrounding context (full paragraph minimum)
2. Identify lexical unit (word/phrase with potential metaphorical meaning)
3. Determine contextual meaning (meaning in THIS passage)
4. Determine basic meaning (concrete, bodily, historically older sense)
5. Compare: if different and understood via comparison → metaphor
6. Classify MIPVU type: indirect, direct, or implicit
7. Map source → target domains
8. Note thematic function

Output JSON to: mip-analysis/annotations/chapter-0X.json
```

## JSON Schema

Each annotation file must follow this structure:

```json
{
  "chapter": 1,
  "total_metaphors": 12,
  "annotations": [
    {
      "id": "ch1-001",
      "location": {
        "chapter": 1,
        "paragraph": 3,
        "quote": "the exact quoted text"
      },
      "lexical_unit": "the specific word or phrase",
      "contextual_meaning": "what it means in this specific passage",
      "basic_meaning": "concrete, physical, or historically older meaning",
      "mip_decision": true,
      "mipvu_type": "indirect|direct|implicit",
      "source_domain": "SOURCE DOMAIN IN CAPS",
      "target_domain": "TARGET DOMAIN IN CAPS",
      "cmt_mapping": "TARGET IS SOURCE",
      "function": ["theme", "characterization", "setting", "narrative"]
    }
  ]
}
```

## Process

1. Read `mip-analysis/research-notes.md` to understand the procedure
2. Ensure `mip-analysis/annotations/` directory exists
3. Spawn 9 parallel Task agents, one per chapter
4. Each agent reads its chapter and the research notes
5. Each agent outputs its JSON file
6. Verify all 9 files created successfully

## Chapters to Process

| Agent | Input | Output |
|-------|-------|--------|
| 1 | book/chapters/chapter-01.txt | mip-analysis/annotations/chapter-01.json |
| 2 | book/chapters/chapter-02.txt | mip-analysis/annotations/chapter-02.json |
| 3 | book/chapters/chapter-03.txt | mip-analysis/annotations/chapter-03.json |
| 4 | book/chapters/chapter-04.txt | mip-analysis/annotations/chapter-04.json |
| 5 | book/chapters/chapter-05.txt | mip-analysis/annotations/chapter-05.json |
| 6 | book/chapters/chapter-06.txt | mip-analysis/annotations/chapter-06.json |
| 7 | book/chapters/chapter-07.txt | mip-analysis/annotations/chapter-07.json |
| 8 | book/chapters/chapter-08.txt | mip-analysis/annotations/chapter-08.json |
| 9 | book/chapters/chapter-09.txt | mip-analysis/annotations/chapter-09.json |

## Success Criteria

- 9 JSON files created in `mip-analysis/annotations/`
- Each file contains 8-15 metaphor annotations
- Total of 40-80+ metaphors identified across all chapters
- JSON structure valid and consistent
- Ready for `/mip-cluster` phase
