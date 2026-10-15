"""
datashaper.tools
=============

MCP tool definitions and handlers.

``TOOLS`` is the list of Tool objects advertised to the MCP client.
``handle_call_tool`` is the dispatcher called by the MCP server on every
``tools/call`` request.

This module is intentionally free of MCP server state — it only imports from
``mcp.types``, not from ``mcp.server``.  The Server instance and its
decorators live exclusively in ``server.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from mcp.types import TextContent, Tool

from .labeler import GenericLabeler

# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _ok(text: str) -> list[TextContent]:
    return [TextContent(type="text", text=text)]


def _err(text: str) -> list[TextContent]:
    return [TextContent(type="text", text=f"❌ {text}")]


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[Tool] = [
    Tool(
        name="inspect_csv",
        description=(
            "Inspect a CSV file: returns column names, types, row count, and a data sample. "
            "Run this first to discover the right column names before calling run_labeling_job."
        ),
        inputSchema={
            "type": "object",
            "required": ["csv_path"],
            "properties": {
                "csv_path": {
                    "type": "string",
                    "description": "Absolute path to the CSV file.",
                },
                "sample_rows": {
                    "type": "integer",
                    "description": "Number of sample rows to display. Default: 3.",
                    "default": 3,
                },
            },
        },
    ),
    Tool(
        name="preview_labeling_job",
        description=(
            "Dry-run a labeling job on the first N rows (default 5). "
            "Use this to iterate on your task_description prompt before committing to a full run."
        ),
        inputSchema={
            "type": "object",
            "required": ["csv_path", "id_column", "input_column", "label_column", "task_description"],
            "properties": {
                "csv_path":         {"type": "string", "description": "Absolute path to the CSV file."},
                "id_column":        {"type": "string", "description": "Column containing unique row IDs."},
                "input_column":     {"type": "string", "description": "Column containing the main input text."},
                "label_column":     {"type": "string", "description": "Column containing the label to validate."},
                "task_description": {"type": "string", "description": "Plain-English description of the labeling task."},
                "output_column":    {"type": "string", "description": "Optional: column with the model/assistant response text."},
                "extra_columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: extra columns to include as context for each row.",
                },
                "provider": {
                    "type": "string",
                    "enum": ["gemini", "openai"],
                    "description": "LLM provider. Default: gemini.",
                    "default": "gemini",
                },
                "model": {
                    "type": "string",
                    "description": "Model name. Defaults to gemini-2.0-flash or gpt-4o.",
                },
                "preview_rows": {
                    "type": "integer",
                    "description": "Number of rows to preview. Default: 5.",
                    "default": 5,
                },
            },
        },
    ),
    Tool(
        name="run_labeling_job",
        description=(
            "Run a full LLM-powered labeling job on a CSV file. "
            "Batches are processed in parallel with automatic retry on failure. "
            "Only rows where the label changes are written to the output CSV, "
            "along with the original label and the LLM's reasoning. "
            "Supports any task expressible as a natural-language prompt: label correction, "
            "classification, entity extraction, moderation, quality evaluation, and more."
        ),
        inputSchema={
            "type": "object",
            "required": ["csv_path", "id_column", "input_column", "label_column", "task_description"],
            "properties": {
                "csv_path":         {"type": "string", "description": "Absolute path to the input CSV file."},
                "id_column":        {"type": "string", "description": "Column containing unique row IDs."},
                "input_column":     {"type": "string", "description": "Column containing the main input text."},
                "label_column":     {"type": "string", "description": "Column containing the existing label to validate / correct."},
                "task_description": {
                    "type": "string",
                    "description": (
                        "Plain-English description of what the LLM should do. "
                        "Be specific: list valid label values, rules, and edge cases. "
                        "Example: 'Verify that the sentiment label (positive / negative / neutral) "
                        "is correct. Flag sarcasm as negative.'"
                    ),
                },
                "output_column": {
                    "type": "string",
                    "description": "Optional: column with the model/assistant response (provides extra context).",
                },
                "extra_columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: additional columns to include as context for each row.",
                },
                "provider": {
                    "type": "string",
                    "enum": ["gemini", "openai"],
                    "description": "LLM provider. Default: gemini.",
                    "default": "gemini",
                },
                "model": {
                    "type": "string",
                    "description": "Model name. Defaults to gemini-2.0-flash or gpt-4o.",
                },
                "batch_size": {
                    "type": "integer",
                    "description": "Rows per LLM call. Default: 10.",
                    "default": 10,
                },
                "max_retries": {
                    "type": "integer",
                    "description": "Maximum retry attempts for each failed batch. Default: 3.",
                    "default": 3,
                },
                "output_path": {
                    "type": "string",
                    "description": "Absolute path for the output CSV. Auto-generated next to the input file if omitted.",
                },
                "limit_rows": {
                    "type": "integer",
                    "description": "Process only the first N rows. Useful for large files.",
                },
                "offset_rows": {
                    "type": "integer",
                    "description": "Skip the first N rows before processing. Default: 0.",
                    "default": 0,
                },
            },
        },
    ),
]


# ---------------------------------------------------------------------------
# Tool handler
# ---------------------------------------------------------------------------


async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Dispatch an MCP ``tools/call`` request to the appropriate handler."""

    # --- inspect_csv --------------------------------------------------------
    if name == "inspect_csv":
        path = Path(arguments["csv_path"])
        n_sample = int(arguments.get("sample_rows", 3))
        if not path.exists():
            return _err(f"File not found: {path}")
        try:
            df = pd.read_csv(path, low_memory=False)
            lines = [
                f"**{path.name}** — {len(df):,} rows, {len(df.columns)} columns",
                "",
                "**Columns:**",
            ]
            for col in df.columns:
                sample = df[col].dropna().iloc[0] if df[col].notna().any() else "—"
                sample_str = str(sample)
                if len(sample_str) > 60:
                    sample_str = sample_str[:60] + "…"
                lines.append(f"  - `{col}` ({df[col].dtype}) — e.g. {sample_str!r}")
            lines += ["", f"**First {n_sample} rows:**", "```"]
            lines.append(df.head(n_sample).to_string(index=False))
            lines.append("```")
            return _ok("\n".join(lines))
        except Exception as exc:
            return _err(f"Could not read CSV: {exc}")

    # --- preview_labeling_job -----------------------------------------------
    if name == "preview_labeling_job":
        n = int(arguments.get("preview_rows", 5))
        try:
            labeler = GenericLabeler(
                csv_path=arguments["csv_path"],
                id_column=arguments["id_column"],
                input_column=arguments["input_column"],
                label_column=arguments["label_column"],
                task_description=arguments["task_description"],
                output_column=arguments.get("output_column"),
                extra_columns=arguments.get("extra_columns", []),
                provider=arguments.get("provider", "gemini"),
                model=arguments.get("model"),
                batch_size=n,
                max_retries=1,
                limit_rows=n,
            )
            labeler.load_data()
            results = await labeler.process_all_batches()

            if results.empty:
                return _ok(f"✅ Preview complete ({n} rows) — no corrections needed.")

            lines = [f"🔍 **Preview** ({n} rows) — {len(results)} correction(s):", ""]
            for _, row in results.iterrows():
                lines += [
                    f"**ID {row['id']}**",
                    f"  Original:  {row['original_label']}",
                    f"  Corrected: {row['corrected_label']}",
                    f"  Reason:    {row['reasoning']}",
                    "",
                ]
            return _ok("\n".join(lines))
        except Exception as exc:
            return _err(f"Preview failed: {exc}")

    # --- run_labeling_job ---------------------------------------------------
    if name == "run_labeling_job":
        try:
            labeler = GenericLabeler(
                csv_path=arguments["csv_path"],
                id_column=arguments["id_column"],
                input_column=arguments["input_column"],
                label_column=arguments["label_column"],
                task_description=arguments["task_description"],
                output_column=arguments.get("output_column"),
                extra_columns=arguments.get("extra_columns", []),
                provider=arguments.get("provider", "gemini"),
                model=arguments.get("model"),
                batch_size=int(arguments.get("batch_size", 10)),
                max_retries=int(arguments.get("max_retries", 3)),
                limit_rows=arguments.get("limit_rows"),
                offset_rows=int(arguments.get("offset_rows", 0)),
            )
            labeler.load_data()
            n_rows = len(labeler.df)  # type: ignore[arg-type]

            results = await labeler.process_all_batches()
            out_path = labeler.save_results(results, arguments.get("output_path"))

            pct = len(results) / n_rows * 100 if n_rows else 0
            lines = [
                "✅ **Labeling job complete**",
                "",
                f"  Rows processed : {n_rows:,}",
                f"  Corrections    : {len(results):,} ({pct:.1f}%)",
                f"  Provider       : {labeler.provider} / {labeler.model}",
                f"  Output CSV     : {out_path}",
            ]
            if not results.empty:
                lines += ["", "**Sample corrections (first 3):**"]
                for _, row in results.head(3).iterrows():
                    lines += [
                        f"  [{row['id']}] {row['original_label']!r} → {row['corrected_label']!r}",
                        f"  {row['reasoning']}",
                        "",
                    ]
            return _ok("\n".join(lines))
        except Exception as exc:
            return _err(f"Labeling job failed: {exc}")

    return _err(f"Unknown tool: '{name}'")
