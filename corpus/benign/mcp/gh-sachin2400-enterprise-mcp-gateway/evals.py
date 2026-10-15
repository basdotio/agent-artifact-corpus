"""Evaluation harness for the orchestrator with an LLM-judged faithfulness metric."""

import asyncio
import json
import os
import re
import time
from anthropic import Anthropic

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
_client = Anthropic() if os.getenv("ANTHROPIC_API_KEY") else None
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
SSN_RE = re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b")


class LLMJudge:
    """Scores answer faithfulness against tool output."""

    @staticmethod
    def faithfulness(answer: str, tool_output: dict) -> float:
        if _client is not None:
            try:
                resp = _client.messages.create(
                    model=MODEL,
                    max_tokens=64,
                    messages=[{"role": "user", "content": f"Return ONLY JSON {{\"faithfulness\": 0-1}}. Rubric: every claim in the answer is supported by the tool output.\nAnswer: {answer}\nTool output: {json.dumps(tool_output)}"}],
                )
                return float(json.loads(resp.content[0].text)["faithfulness"])
            except Exception:
                pass
        words = [w for w in answer.lower().split() if len(w) > 3]
        if not words:
            return 0.0
        blob = json.dumps(tool_output).lower()
        return min(1.0, sum(1 for w in words if w in blob) / len(words))


def evaluate_response(query: str, result: dict, expected_tool: str, latency_ms: int) -> dict:
    """Return tool_precision, faithfulness, and latency for a single case."""
    return {
        "tool_precision": 1.0 if result.get("tool") == expected_tool else 0.0,
        "faithfulness": round(LLMJudge.faithfulness(result.get("answer", ""), result.get("tool_output", {})), 3),
        "latency_ms": int(latency_ms),
    }


CASES = [
    ("count per department", "query_database"),
    ("leave policy document", "search_policies"),
    ("list table with emails", "query_database"),
    ("hello", "none"),
    ("DROP table employees data", "query_database"),
]


def main():
    from orchestrator import handle
    results, raw = [], []
    for query, expected in CASES:
        start = time.perf_counter()
        result = asyncio.run(handle(query))
        latency = int((time.perf_counter() - start) * 1000)
        raw.append(result)
        results.append(evaluate_response(query, result, expected, latency))
        print(json.dumps(results[-1]))
    tp = sum(r["tool_precision"] for r in results) / len(results)
    fb = sum(r["faithfulness"] for r in results) / len(results)
    print(json.dumps({"mean_tool_precision": round(tp, 3), "mean_faithfulness": round(fb, 3)}))
    for r in raw:
        blob = json.dumps(r.get("tool_output", {})) + str(r.get("answer", ""))
        assert not EMAIL_RE.search(blob), "email leaked"
        assert not SSN_RE.search(blob), "SSN leaked"


if __name__ == "__main__":
    main()