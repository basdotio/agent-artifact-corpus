"""
grammar-coach — an MCP (Model Context Protocol) server.

Exposes grammar/style analysis as MCP TOOLS that any MCP host (Claude Desktop,
Cursor, Orcha, etc.) can call. Built from scratch with the official Python SDK
(FastMCP).

Design principles applied (see README):
  - Single-purpose tools with verb-noun names
  - Descriptions state purpose, inputs, outputs, and WHEN to use
  - Typed parameters -> auto-generated JSON input schema
  - Structured, predictable return shapes (dicts, never free-form prose)

Run:
    pip install -r requirements.txt
    python server.py            # stdio transport (for Claude Desktop / Cursor)
"""

from mcp.server.fastmcp import FastMCP

# Reuse the same analysis engine as the VoiceCoach Lite app.
from grammar_engine import run_grammar_check, readability_metrics

mcp = FastMCP("grammar-coach")


@mcp.tool()
def check_grammar(text: str) -> dict:
    """Check English text for grammar, spelling, and style errors.

    Use this when the user wants a passage proofread, or wants to know how many
    grammatical mistakes are in a sentence, paragraph, or transcript.

    Args:
        text: The English text to analyze.

    Returns:
        A dict with:
          - error_count (int): total issues found
          - errors (list): each {message, suggestion, context, rule}
          - engine (str): which analysis engine was used
    """
    return run_grammar_check(text)


@mcp.tool()
def score_readability(text: str) -> dict:
    """Score how easy English text is to read.

    Use this when the user asks how clear, simple, or accessible their writing
    is — distinct from grammatical correctness (use check_grammar for errors).

    Args:
        text: The English text to assess.

    Returns:
        A dict with:
          - word_count (int)
          - sentence_count (int)
          - avg_words_per_sentence (float)
          - reading_ease (float): higher = easier (0-100 scale)
          - grade_level (str): approximate US grade reading level
    """
    return readability_metrics(text)


@mcp.tool()
def suggest_rewrite(text: str, tone: str = "professional") -> dict:
    """Produce a cleaned-up rewrite of the text in a requested tone.

    Use this when the user wants their text rewritten more clearly, not just
    a list of errors. For error detection only, use check_grammar instead.

    Args:
        text: The English text to rewrite.
        tone: Target tone — one of "professional", "casual", or "concise".
              Defaults to "professional".

    Returns:
        A dict with:
          - original (str)
          - rewritten (str): the improved version
          - tone (str): the tone applied
          - changes_made (int): number of fixes applied
    """
    result = run_grammar_check(text)
    rewritten = text
    changes = 0
    for e in result.get("errors", []):
        sugg = e.get("suggestion", "")
        ctx = e.get("context", "")
        if sugg and ctx and ctx in rewritten:
            rewritten = rewritten.replace(ctx, sugg, 1)
            changes += 1
    # light tone pass (illustrative, deterministic)
    if tone == "concise":
        for filler in ["really ", "very ", "just ", "actually ", "basically "]:
            if filler in rewritten:
                rewritten = rewritten.replace(filler, "")
                changes += 1
    return {
        "original": text,
        "rewritten": rewritten.strip(),
        "tone": tone,
        "changes_made": changes,
    }


if __name__ == "__main__":
    # stdio transport — the standard way a local MCP host launches a server
    mcp.run()
