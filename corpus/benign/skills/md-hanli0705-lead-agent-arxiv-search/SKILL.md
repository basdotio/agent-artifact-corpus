---
name: arxiv-search
description: Search arXiv preprint repository for academic papers in physics, mathematics, computer science, and related fields
---

# arXiv Search Skill

This skill provides access to arXiv, a free distribution service and open-access archive for scholarly articles.

## When to Use This Skill

Use this skill when you need to:
- Search for academic papers or research articles
- Find preprints before journal publication
- Look up papers in computer science, physics, mathematics, or related fields
- Search for specific topics like "DeepSeek", "machine learning", "neural networks", etc.
- Find the latest research on any technical topic

## How to Use

This skill provides a Python script that searches arXiv and returns formatted results.

### Basic Usage

Use the `shell` tool to execute the arXiv search script:

```bash
python3 superagent/agent_skills/arxiv-search/arxiv_search.py --query "your search query" [--max-papers N]
```

**Arguments:**
- `query` (required): The search query string (e.g., "DeepSeek-V3", "machine learning", "neural networks")
- `--max-papers` (optional): Maximum number of papers to retrieve (default: 10)

### Examples

Search for DeepSeek papers:
```bash
python3 superagent/agent_skills/arxiv-search/arxiv_search.py --query "DeepSeek-V3" --max-papers 5
```

Search for machine learning papers:
```bash
python3 superagent/agent_skills/arxiv-search/arxiv_search.py --query "deep learning" --max-papers 10
```

## Output Format

The script returns formatted results with:
- **Title**: Paper title
- **Summary**: Abstract/summary text

Each paper is separated by blank lines for readability.

## Dependencies

This skill requires the `arxiv` Python package. If not installed, use:

```bash
pip install arxiv
```

## Notes

- arXiv is particularly strong for computer science (cs.LG, cs.AI, cs.CV), physics, and mathematics
- Papers are preprints and may not be peer-reviewed
- Results include both recent uploads and older papers
- Best for computational/theoretical work
