"""Agent creation and execution."""
import os
from llm_client import chat_completion


def create_and_run_agent(agent_name: str,
                         system_prompt: str,
                         task: str,
                         model: str = None) -> dict:
    model = model or os.getenv("OPENROUTER_MODEL")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task},
    ]
    try:
        result = chat_completion(messages, temperature=0.7)
        return {"agent_name": agent_name, "status": "success",
                "result": result, "model_used": model}
    except Exception as e:
        return {"agent_name": agent_name, "status": "error", "error": str(e)}