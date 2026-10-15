"""
datashaper.labeler
===============

``GenericLabeler`` is the core engine of mcp-data-shaper.

It reads a CSV, splits it into equal-sized batches, sends each batch to an
LLM, and collects only the rows where the label changed together with the
LLM's reasoning.  Batches are dispatched concurrently (up to
``_PARALLEL_BATCHES`` at a time) and automatically retried on failure.

Typical usage::

    labeler = GenericLabeler(
        csv_path="data.csv",
        id_column="id",
        input_column="text",
        label_column="sentiment",
        task_description="Verify that the sentiment label is correct ...",
    )
    labeler.load_data()
    results  = await labeler.process_all_batches()
    out_path = labeler.save_results(results)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .llm import (
    DEFAULT_MODELS,
    _BATCH_DELAY,
    _PARALLEL_BATCHES,
    _RETRY_DELAY,
    LLMClient,
    _build_client,
)
from .models import BatchOutput, CorrectedRow

logger = logging.getLogger(__name__)


class GenericLabeler:
    """
    LLM-powered CSV labeler that requires no subclassing.

    All task-specific configuration is passed at construction time, making
    ``GenericLabeler`` usable directly from the MCP tool handlers (or from
    any Python script) without writing any extra code.

    Parameters
    ----------
    csv_path        : Path to the input CSV file.
    id_column       : Column containing unique, stable row identifiers.
    input_column    : Column containing the main text the LLM should read.
    label_column    : Column containing the existing label to validate.
    task_description: Natural-language instructions for the LLM.
    output_column   : Optional column with the model/assistant response
                      (provides extra context for conversational datasets).
    extra_columns   : Additional columns to include verbatim in each prompt.
    provider        : LLM provider — ``"gemini"`` (default) or ``"openai"``.
    model           : Model name; defaults to ``DEFAULT_MODELS[provider]``.
    batch_size      : Rows per LLM call (default 10).
    max_retries     : Maximum retry attempts per failed batch (default 3).
    limit_rows      : Process only the first N rows (useful for large files).
    offset_rows     : Skip the first N rows before processing (default 0).
    """

    def __init__(
        self,
        *,
        csv_path: str | Path,
        id_column: str,
        input_column: str,
        label_column: str,
        task_description: str,
        output_column: str | None = None,
        extra_columns: list[str] | None = None,
        provider: str = "gemini",
        model: str | None = None,
        batch_size: int = 10,
        max_retries: int = 3,
        limit_rows: int | None = None,
        offset_rows: int = 0,
    ) -> None:
        self.csv_path      = Path(csv_path)
        self.id_column     = id_column
        self.input_column  = input_column
        self.label_column  = label_column
        self.output_column = output_column
        self.extra_columns = extra_columns or []
        self.provider      = provider
        self.model         = model or DEFAULT_MODELS.get(provider, "gemini-2.0-flash")
        self.batch_size    = batch_size
        self.max_retries   = max_retries
        self.limit_rows    = limit_rows
        self.offset_rows   = offset_rows
        self.df: pd.DataFrame | None = None

        # Build the system prompt once — it is identical for every batch
        self._system_prompt = self._build_system_prompt(task_description)
        self._llm: LLMClient = _build_client(provider)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_data(self) -> None:
        """Read the CSV and apply offset / limit.  Raises on missing columns."""
        df = pd.read_csv(self.csv_path, low_memory=False)

        required = [self.id_column, self.input_column, self.label_column]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(
                f"Column(s) not found in CSV: {missing}\n"
                f"Available columns: {list(df.columns)}"
            )

        if self.offset_rows:
            df = df.iloc[self.offset_rows :]
        if self.limit_rows:
            df = df.iloc[: self.limit_rows]

        self.df = df.reset_index(drop=True)
        logger.info(
            "Loaded %d rows from %s (offset=%d, limit=%s)",
            len(self.df), self.csv_path.name, self.offset_rows, self.limit_rows,
        )

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_system_prompt(self, task_description: str) -> str:
        return (
            "You are an expert data labeler reviewing a CSV dataset.\n\n"
            f"## Your task\n\n{task_description}\n\n"
            "## Output rules\n\n"
            "- Return **only** rows where the label must change.\n"
            "- For every changed row include: `id`, `corrected_label` (string), "
            "`original_label` (verbatim copy from input), `reasoning` (one sentence).\n"
            "- If every label in the batch is already correct, return an empty list."
        )

    def _build_user_prompt(self, formatted_items: list[str]) -> str:
        return (
            "Review the items below. Return only the rows where the label needs correction.\n\n"
            + "\n".join(formatted_items)
        )

    def _format_row(self, row: dict[str, Any]) -> str:
        """Serialise one CSV row into a human-readable block for the LLM prompt."""

        def _val(v: Any) -> str:
            return str(v) if pd.notna(v) else ""

        lines = [
            "---",
            f"id: {_val(row.get(self.id_column))}",
            f"input: {_val(row.get(self.input_column))}",
        ]
        if self.output_column and self.output_column in row:
            lines.append(f"output: {_val(row[self.output_column])}")
        lines.append(f"current_label: {_val(row.get(self.label_column))}")
        for col in self.extra_columns:
            if col in row:
                lines.append(f"{col}: {_val(row[col])}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Batch execution
    # ------------------------------------------------------------------

    async def _run_batch(
        self,
        batch: list[dict[str, Any]],
        batch_idx: int,
        total: int,
    ) -> tuple[BatchOutput, bool]:
        """Send one batch to the LLM.  Returns ``(result, success)``."""
        try:
            formatted = [self._format_row(r) for r in batch]
            result = await asyncio.wait_for(
                self._llm.parse_structured_output(
                    model=self.model,
                    system_prompt=self._system_prompt,
                    user_prompt=self._build_user_prompt(formatted),
                    response_model=BatchOutput,
                ),
                timeout=300,
            )
            logger.info(
                "Batch %d/%d — %d correction(s)",
                batch_idx + 1, total, len(result.corrected_rows),
            )
            return result, True
        except asyncio.TimeoutError:
            logger.warning("Batch %d/%d timed out.", batch_idx + 1, total)
        except Exception as exc:
            logger.error("Batch %d/%d failed: %s", batch_idx + 1, total, exc)
        return BatchOutput(corrected_rows=[]), False

    async def _run_chunk(
        self,
        chunk: list[tuple[int, list[dict[str, Any]]]],
        total: int,
        sink: list[CorrectedRow],
    ) -> list[int]:
        """
        Fire up to ``_PARALLEL_BATCHES`` LLM calls concurrently.

        Appends successful corrections to *sink*; returns the indices of any
        batches that failed so they can be scheduled for retry.
        """
        tasks: dict[asyncio.Task[tuple[BatchOutput, bool]], int] = {
            asyncio.create_task(self._run_batch(data, idx, total)): idx
            for idx, data in chunk
        }
        failed: list[int] = []
        pending = set(tasks)
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                result, ok = task.result()
                if ok:
                    sink.extend(result.corrected_rows)
                else:
                    failed.append(tasks[task])
        return failed

    async def process_all_batches(self) -> pd.DataFrame:
        """
        Main processing loop with automatic retry.

        Splits rows into batches, sends ``_PARALLEL_BATCHES`` at a time, then
        retries failed batches up to ``max_retries`` times.

        Returns a DataFrame with columns:
        ``id``, ``corrected_label``, ``original_label``, ``reasoning``.
        Only rows where the label changed are included.
        """
        if self.df is None:
            raise RuntimeError("Call load_data() before process_all_batches().")

        rows = self.df.to_dict("records")
        batches = [
            (i // self.batch_size, rows[i : i + self.batch_size])
            for i in range(0, len(rows), self.batch_size)
        ]
        total = len(batches)
        logger.info("%d row(s) → %d batch(es) of %d", len(rows), total, self.batch_size)

        corrections: list[CorrectedRow] = []
        failure_counts: dict[int, int] = {}  # batch_idx → number of failures so far

        # --- first pass ---
        for start in range(0, total, _PARALLEL_BATCHES):
            chunk = batches[start : start + _PARALLEL_BATCHES]
            for idx in await self._run_chunk(chunk, total, corrections):
                failure_counts[idx] = failure_counts.get(idx, 0) + 1
            if start + _PARALLEL_BATCHES < total:
                await asyncio.sleep(_BATCH_DELAY)

        # --- retry rounds ---
        for retry_round in range(1, self.max_retries + 1):
            retryable = [
                (idx, batches[idx][1])
                for idx, cnt in failure_counts.items()
                if cnt < self.max_retries
            ]
            if not retryable:
                break
            logger.info(
                "Retry round %d/%d — %d batch(es)",
                retry_round, self.max_retries, len(retryable),
            )
            await asyncio.sleep(_RETRY_DELAY)
            for start in range(0, len(retryable), _PARALLEL_BATCHES):
                chunk = retryable[start : start + _PARALLEL_BATCHES]
                for idx in await self._run_chunk(chunk, total, corrections):
                    failure_counts[idx] = failure_counts.get(idx, 0) + 1
                if start + _PARALLEL_BATCHES < len(retryable):
                    await asyncio.sleep(_BATCH_DELAY)

        exhausted = [idx for idx, cnt in failure_counts.items() if cnt >= self.max_retries]
        if exhausted:
            logger.warning(
                "Batches permanently failed after %d retries: %s",
                self.max_retries, exhausted,
            )

        if not corrections:
            logger.info("All labels are correct — no corrections produced.")
            return pd.DataFrame(columns=["id", "corrected_label", "original_label", "reasoning"])

        return pd.DataFrame([
            {
                "id": r.id,
                "corrected_label": r.corrected_label,
                "original_label": r.original_label,
                "reasoning": r.reasoning,
            }
            for r in corrections
        ])

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def save_results(self, df: pd.DataFrame, output_path: str | Path | None = None) -> Path:
        """Write the corrections DataFrame to a CSV.

        If *output_path* is omitted the file is placed next to the input CSV
        with an auto-generated name that encodes the row range and timestamp.
        """
        if output_path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            n = len(self.df) if self.df is not None else 0
            end = self.offset_rows + n - 1
            output_path = (
                self.csv_path.parent
                / f"corrections_{self.csv_path.stem}_{self.offset_rows}-{end}_{ts}.csv"
            )
        out = Path(output_path)
        df.to_csv(out, index=False)
        logger.info("Saved %d correction(s) → %s", len(df), out)
        return out
