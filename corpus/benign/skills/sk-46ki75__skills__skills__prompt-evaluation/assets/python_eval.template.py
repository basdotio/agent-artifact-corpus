"""Prompt evaluation template using the Anthropic SDK.

Demonstrates:
- Prompt caching on the stable system block (10x cheaper reads)
- Extended-thinking-safe block extraction (filter type == "text")
- Set-match grader for multi-label classification
- Structured Outputs for a model-graded judge (no deprecated prefill)
- Async/concurrent runner with rate-limit-friendly bounds

Usage:
    export ANTHROPIC_API_KEY=...
    python python_eval.template.py
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Callable

from anthropic import Anthropic, AsyncAnthropic

CLIENT = Anthropic()
ASYNC_CLIENT = AsyncAnthropic()

# Use the alias form (`-latest`) when you want auto-updates within a
# generation; use a pinned form (e.g. `claude-haiku-4-5-20251001`)
# when you want frozen reproducibility for a regression suite.
MODEL = "claude-haiku-4-5-20251001"
JUDGE_MODEL = "claude-haiku-4-5-20251001"


# --- prompt versions --------------------------------------------------

V1_SYSTEM = """\
You are a customer support triage assistant. Classify the
complaint into one of: Software Bug, Hardware Malfunction,
User Error, Feature Request, Service Outage. Respond with only
the category name and nothing else."""


V2_SYSTEM = """\
You are a customer support triage assistant. Classify the
complaint into one or more of: Software Bug, Hardware Malfunction,
User Error, Feature Request, Service Outage. Prefer a single
category when possible. Respond with only the category name(s),
comma-separated, and nothing else.

Categories:
- Software Bug: code defect causing incorrect behavior
- Hardware Malfunction: physical device failure
- User Error: misuse or misunderstanding by the user
- Feature Request: a desired capability not yet implemented
- Service Outage: backend / network unavailability

Examples:
- "App crashes when I upload a photo" -> Software Bug
- "My printer isn't recognized" -> Hardware Malfunction
- "I forgot my password" -> User Error
"""


# --- dataset ----------------------------------------------------------

EVAL_DATA: list[dict] = [
    {"complaint": "The app crashes when I upload a photo",
     "golden_answer": ["Software Bug"]},
    {"complaint": "My printer isn't recognized by my computer",
     "golden_answer": ["Hardware Malfunction"]},
    {"complaint": "I can't figure out how to change my password",
     "golden_answer": ["User Error"]},
    {"complaint": "Your service is down and I urgently need a CSV export feature",
     "golden_answer": ["Service Outage", "Feature Request"]},
    # ... add more from real failures (see references/dataset_design.md)
]


# --- extended-thinking-safe text extractor ----------------------------

def extract_text(response) -> str:
    """Get the assistant's text reply.

    When extended thinking is on (Opus 4.7+ adaptive thinking, etc.),
    the first content block is `type: "thinking"`, not the text reply.
    `response.content[0].text` silently returns the thinking summary
    instead of the answer. Always iterate.
    """
    return "".join(
        block.text for block in response.content if block.type == "text"
    )


# --- code-graded run (with prompt caching) ----------------------------

def get_completion_cached(system_text: str, user_text: str) -> str:
    """Call the model with the system block cached.

    On a warm cache, the system tokens cost 0.1x (10x cheaper).
    Minimum cacheable size: 4,096 tokens on Opus 4.5/4.6/4.7 /
    Mythos Preview / Haiku 4.5; 1,024 tokens on Opus 4.8 /
    Sonnet 4.5 / Sonnet 4.6. Below the minimum: silent cache miss
    (no error).
    """
    resp = CLIENT.messages.create(
        model=MODEL,
        max_tokens=200,
        system=[{
            "type": "text",
            "text": system_text,
            "cache_control": {"type": "ephemeral"},  # 5-min TTL
        }],
        messages=[{"role": "user", "content": user_text}],
    )
    # Verify cache effectiveness over a run by summing
    # resp.usage.cache_read_input_tokens across calls.
    return extract_text(resp)


def set_match(output: str, golden: list[str]) -> bool:
    """Order-insensitive multi-label match."""
    predicted = {c.strip().lower() for c in output.split(",")}
    expected = {c.lower() for c in golden}
    return predicted == expected


@dataclass
class Result:
    item: dict
    output: str
    passed: bool


def run_code_graded(system_text: str, data: list[dict]) -> list[Result]:
    results = []
    for item in data:
        output = get_completion_cached(system_text, item["complaint"])
        passed = set_match(output, item["golden_answer"])
        results.append(Result(item=item, output=output, passed=passed))
    return results


# --- async concurrent runner ------------------------------------------

async def get_completion_async(system_text: str, user_text: str) -> str:
    resp = await ASYNC_CLIENT.messages.create(
        model=MODEL,
        max_tokens=200,
        system=[{
            "type": "text",
            "text": system_text,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_text}],
    )
    return extract_text(resp)


async def run_concurrent(
    system_text: str, data: list[dict], concurrency: int = 5
) -> list[Result]:
    sem = asyncio.Semaphore(concurrency)

    async def one(item: dict) -> Result:
        async with sem:
            output = await get_completion_async(system_text, item["complaint"])
            return Result(
                item=item,
                output=output,
                passed=set_match(output, item["golden_answer"]),
            )

    return await asyncio.gather(*(one(it) for it in data))


# --- model-graded judge (Structured Outputs, no prefill) --------------

JUDGE_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "reasoning": {"type": "string"},
            "verdict": {"type": "string", "enum": ["correct", "incorrect"]},
        },
        "required": ["reasoning", "verdict"],
        "additionalProperties": False,
    },
}

JUDGE_SYSTEM = """\
You are grading classifications. The criterion is:
"the predicted category set is exactly equal to the golden category set;
case-insensitive, order-insensitive, but the set of labels must match."
Reason briefly, then return a verdict."""


def llm_judge(prediction: str, golden: list[str]) -> tuple[bool, str]:
    """Pointwise binary judge with Structured Outputs.

    Used here for illustration — for an exact-set criterion you should
    use set_match() above (code-graded; cheaper and more reliable).
    This pattern matters for open-ended outputs.
    """
    user = (
        f"<golden>{json.dumps(golden)}</golden>\n"
        f"<prediction>{prediction}</prediction>"
    )
    resp = CLIENT.messages.create(
        model=JUDGE_MODEL,
        max_tokens=400,
        temperature=0,
        system=[{
            "type": "text",
            "text": JUDGE_SYSTEM,
            "cache_control": {"type": "ephemeral"},  # rubric is stable
        }],
        messages=[{"role": "user", "content": user}],
        output_config={"format": JUDGE_SCHEMA},
    )
    parsed = json.loads(extract_text(resp))
    return parsed["verdict"] == "correct", parsed["reasoning"]


# --- reporting --------------------------------------------------------

def report(label: str, results: list[Result]) -> None:
    passes = sum(r.passed for r in results)
    total = len(results)
    print(f"\n=== {label}: {passes}/{total} = {passes/total:.1%} ===")
    for r in results:
        if not r.passed:
            print(f"  FAIL: {r.item['complaint']!r}")
            print(f"    expected={r.item['golden_answer']}")
            print(f"    got     ={r.output!r}")


# --- main -------------------------------------------------------------

if __name__ == "__main__":
    # Sequential (simple)
    v1 = run_code_graded(V1_SYSTEM, EVAL_DATA)
    v2 = run_code_graded(V2_SYSTEM, EVAL_DATA)
    report("v1 (code-graded)", v1)
    report("v2 (code-graded)", v2)

    # Concurrent (faster, respects rate limits via semaphore)
    # v2_async = asyncio.run(run_concurrent(V2_SYSTEM, EVAL_DATA))
    # report("v2 (async)", v2_async)

    # Batch API (~50% cheaper for offline regression sweeps):
    # See https://docs.anthropic.com/en/api/messages-batches
