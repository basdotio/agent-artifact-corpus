"""LLM backends: AWS Bedrock (live) and a deterministic mock (tests/CI/eval).

The mock answers TOOL-DECIDE prompts with exact JSON so the agent loop is
fully deterministic without any API keys.
"""
from __future__ import annotations

import json
import re

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult

DECIDE_MARKER = "TOOL-DECIDE"


_RECORD_RE = re.compile(r"R-\d+")
_DOC_KW = re.compile(
    r"polic|refund|reset|password|\bplan\b|upgrade|\bapi\b|\berror\b|how do|how to", re.I
)
_STATS_KW = re.compile(r"analyz|stats|word count|reading time", re.I)


def _mock_decide(prompt: str) -> str:
    qm = re.search(r"Question:\s*(.*?)\s*History:", prompt, re.S)
    hm = re.search(r"History:\s*(.*)", prompt, re.S)
    question = qm.group(1).strip() if qm else ""
    history = hm.group(1).strip() if hm else ""
    used = re.findall(r"tool=(\w+)", history)

    def finalize() -> str:
        obs = re.findall(r"Observation\[(\w+)\]:\s*(.*?)(?=Observation\[|\Z)", history, re.S)
        parts = [f"{name}: {text.strip()[:300]}" for name, text in obs]
        summary = " | ".join(parts) if parts else "no tool results"
        return json.dumps({"answer": f"Based on tool results — {summary}"})

    has_record = bool(_RECORD_RE.search(question))
    has_doc_kw = bool(_DOC_KW.search(question))

    if used:  # follow-up decision: finish outstanding work, then answer
        if has_record and "record_lookup" not in used:
            rid = _RECORD_RE.search(question).group(0)
            return json.dumps({"tool": "record_lookup", "args": {"record_id": rid}})
        if has_doc_kw and "doc_search" not in used:
            return json.dumps({"tool": "doc_search", "args": {"query": question, "k": 3}})
        return finalize()

    if _STATS_KW.search(question):
        tm = re.search(r'"([^"]+)"', question)
        return json.dumps({"tool": "text_stats", "args": {"text": tm.group(1) if tm else question}})
    if has_record and not has_doc_kw:
        return json.dumps({"tool": "record_lookup",
                           "args": {"record_id": _RECORD_RE.search(question).group(0)}})
    if has_doc_kw:
        return json.dumps({"tool": "doc_search", "args": {"query": question, "k": 3}})
    if has_record:
        return json.dumps({"tool": "record_lookup",
                           "args": {"record_id": _RECORD_RE.search(question).group(0)}})
    return json.dumps({"answer": "I don't have enough information to answer that."})


def _last_human_text(messages) -> str:
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            return m.content if isinstance(m.content, str) else str(m.content)
    return "\n".join(str(getattr(m, "content", "")) for m in messages)


class MockChatLLM(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "mock-chat"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        prompt = _last_human_text(messages)
        reply = _mock_decide(prompt) if DECIDE_MARKER in prompt else "mock-response"
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=reply))])


class BedrockChatLLM(BaseChatModel):
    model_id: str
    region: str = "us-east-1"
    max_tokens: int = 512

    @property
    def _llm_type(self) -> str:
        return "bedrock-chat"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        import boto3

        client = boto3.client("bedrock-runtime", region_name=self.region)
        system, convo = [], []
        for m in messages:
            content = m.content if isinstance(m.content, str) else str(m.content)
            if isinstance(m, SystemMessage):
                system.append({"text": content})
            elif isinstance(m, HumanMessage):
                convo.append({"role": "user", "content": [{"text": content}]})
            elif isinstance(m, AIMessage):
                convo.append({"role": "assistant", "content": [{"text": content}]})
        request = {
            "modelId": self.model_id,
            "messages": convo,
            "inferenceConfig": {"maxTokens": self.max_tokens},
        }
        if system:
            request["system"] = system
        resp = client.converse(**request)
        text = "".join(b.get("text", "") for b in resp["output"]["message"]["content"])
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])


def get_llm(settings) -> BaseChatModel:
    if settings.mock_mode:
        return MockChatLLM()
    return BedrockChatLLM(
        model_id=settings.bedrock_model_id,
        region=settings.aws_region,
        max_tokens=settings.bedrock_max_tokens,
    )
