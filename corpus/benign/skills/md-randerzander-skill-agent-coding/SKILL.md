---
name: coding
description: Write and execute Python code to process data, analyze scraped content, or perform computations
---

# Coding Skill

Use this skill to generate and execute Python code for data processing, analysis, or computation tasks.

Most often the code result should produce an image of a plot or a textual output that answers the user's question. Those artifacts should be saved in scratch/

## When to use this skill

- Process or analyze scraped web content from `scratch/` directories
- Perform calculations or data transformations
- Parse JSON/JSONL files from search results or URL content
- Generate reports or visualizations
- Any task requiring programmatic data processing

## Available scraped data

The web skill saves content to the scratch directory:
- `scratch/query_*.jsonl` - Search results (one JSON object per line)
- `scratch/url_*.jsonl` - Scraped web page content with URL, title, and markdown content
- `scratch/USER_QUERY.txt` - Original user question

## Workflow

1. Use `generate_code` to generate Python code, save it, and execute it in one step
2. The code is automatically saved to `scratch/code/` and executed
3. Results are returned including output, exit code, and any new files created

## Tools

- `grep_file(filepath: str, pattern: str, case_sensitive: bool, max_results: int)` - Search for pattern in a file with regex
- `generate_code(task_description: str, context: str)` - Generate Python code with Qwen, save it, execute it, and return results (all in one step)

**Note**: `read_file`, `write_code`, and `run_code` are disabled. Use `grep_file` to search files, 
or `generate_code` which handles everything automatically.

## Tips

- Always use relative paths starting with `scratch/` to read data files
- Scripts run with the project root as working directory
- Use standard libraries (json, pathlib, etc.) without installation
- For data analysis & viz, you can use pandas, numpy, plotly, matplotlib if needed
- Print results to stdout - they will be captured and returned
