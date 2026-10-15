# mcp-data-shaper

> **LLM-powered CSV labeling as an MCP server.**
> Validate, correct, and enrich labels in any dataset using OpenAI or Gemini — directly from Claude, Cursor, or any MCP client.

---

## What it does

`mcp-data-shaper` exposes three MCP tools that let an AI agent run **batch LLM labeling jobs** on CSV files:

- Send rows to an LLM with a custom prompt describing the task
- The LLM returns only the rows where the label needs to change
- Results are saved as a CSV with the original label, corrected label, and reasoning

All you define is the **task description** in plain English. No code, no config classes, no boilerplate.

---

## Use cases

| Task | Example prompt |
|------|---------------|
| **Label correction** | "Review whether the sentiment label (positive/negative/neutral) is correct" |
| **Content classification** | "Classify each text into one of: sports / politics / tech / entertainment" |
| **Entity extraction** | "Extract all person names mentioned and format as a comma-separated list" |
| **Content moderation** | "Flag any text that contains hate speech, self-harm, or illegal content" |
| **Quality evaluation** | "Rate the helpfulness of the assistant response on a scale of 1–5" |
| **Fact checking** | "Given the context column, verify if the claim in the label column is accurate" |
| **Data enrichment** | "Infer the user's intent from the conversation and label it" |
| **Structured extraction** | "Extract the company name and job title from the bio text" |
| **PII detection** | "Identify any personally identifiable information present in the text" |
| **Custom rule validation** | "Apply the rules in the guidelines column and verify the label is correct" |

---

## Tools

### `inspect_csv`
Inspect a CSV file before running a job: shows column names, data types, row count, and a sample.

**Parameters:**
- `csv_path` — absolute path to the CSV
- `sample_rows` — number of sample rows to show (default: 3)

---

### `preview_labeling_job`
Run the labeling logic on the first N rows only. Use this to test and refine your prompt before committing to a full run.

**Parameters:**
- `csv_path`, `id_column`, `input_column`, `label_column`, `task_description` — required
- `output_column` — optional: assistant/response text for extra context
- `extra_columns` — optional: additional context columns
- `provider` — `gemini` (default) or `openai`
- `model` — model name (default: `gemini-2.0-flash` / `gpt-4o`)
- `preview_rows` — rows to preview (default: 5)

---

### `run_labeling_job`
Run the full labeling job with parallel batching and automatic retry on failures.

**Parameters:**
- `csv_path`, `id_column`, `input_column`, `label_column`, `task_description` — required
- `output_column` — optional: assistant/response text for extra context
- `extra_columns` — optional: additional context columns
- `provider` — `gemini` (default) or `openai`
- `model` — model name
- `batch_size` — rows per LLM call (default: 10)
- `max_retries` — max retry attempts per failed batch (default: 3)
- `output_path` — output CSV path (auto-generated if omitted)
- `limit_rows` — process only the first N rows
- `offset_rows` — skip the first N rows (default: 0)

**Output CSV columns:** `id`, `corrected_label`, `original_label`, `reasoning`

---

## Architecture

```
CSV file
  ↓
Split into batches (batch_size rows each)
  ↓
Process CHUNK_SIZE batches in parallel (async)
  ↓
Each batch → LLM call (OpenAI or Gemini) with structured output
  ↓
LLM returns only rows where label changed
  ↓
Failed batches retried up to max_retries times
  ↓
Output CSV with corrections + reasoning
```

Internally uses async Python (`asyncio`) with `asyncio.wait(FIRST_COMPLETED)` for parallel batch execution and exponential backoff on retries.

---

## Installation

**Requirements:** Python 3.11+

```bash
git clone https://github.com/YOUR_USERNAME/mcp-data-shaper
cd mcp-data-shaper
chmod +x install.sh
./install.sh
```

---

## Configuration

Set your API keys once in your MCP client config. No credentials are stored in the repository.

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "data-shaper": {
      "command": "/absolute/path/to/mcp-data-shaper/.venv/bin/python",
      "args": ["/absolute/path/to/mcp-data-shaper/server.py"],
      "env": {
        "GEMINI_API_KEY": "your-gemini-key",
        "OPENAI_API_KEY": "your-openai-key"
      }
    }
  }
}
```

### Cursor

Edit `~/.cursor/mcp.json` with the same structure.

### Claude CLI

```bash
claude mcp add data-shaper \
  "/absolute/path/to/mcp-data-shaper/.venv/bin/python" \
  "/absolute/path/to/mcp-data-shaper/server.py" \
  -e GEMINI_API_KEY=your-gemini-key \
  -e OPENAI_API_KEY=your-openai-key
```

---

## Credentials

| Variable | Required for |
|----------|-------------|
| `GEMINI_API_KEY` | Gemini models (default provider) |
| `OPENAI_API_KEY` | OpenAI models |

You only need the key for the provider(s) you plan to use.

---

## Example usage

Once configured, ask Claude in natural language:

```
Inspect the CSV at /Users/me/data/reviews.csv
```

```
Preview a labeling job on /Users/me/data/reviews.csv
  - id column: review_id
  - input column: review_text
  - label column: sentiment
  Task: "Verify that the sentiment label (positive / negative / neutral)
  is correct. Consider sarcasm and mixed reviews carefully."
```

```
Run the full labeling job on /Users/me/data/reviews.csv, same settings as the preview.
Use batch_size 15 and gemini-2.0-flash.
```

---

## Supported MCP clients

Any client that supports MCP stdio transport:

- [Claude Desktop](https://claude.ai/download)
- [Cursor](https://cursor.sh)
- [Claude CLI (Claude Code)](https://docs.anthropic.com/en/docs/claude-code)
- [Windsurf](https://codeium.com/windsurf), [Zed](https://zed.dev), [Continue](https://continue.dev), [Cline](https://cline.bot)
- Any custom agent using the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) or [mcp-use](https://github.com/mcp-use/mcp-use)

---

## License

MIT — see [LICENSE](LICENSE)
