---
name: intelli-router
description: >
  Intelligent model router that triages every incoming user message by complexity
  using a local Ollama model (qwen3:1.7b), then routes to the optimal AI model via
  session_status. Use on ALL incoming user messages to automatically select between
  local models (dengcao/Qwen3-32B:Q5_K_M via Ollama) for simple tasks, Claude Sonnet
  for moderate tasks, Codex for coding tasks, and Claude Opus for complex tasks.
  Triggers on any user message that is not a slash command.
  Keywords: model routing, triage, classify, complexity, cost optimization, smart routing.
requires:
  - python3
  - requests (pip)
---

# Intelli-Router: Automatic Model Routing

## Purpose

Automatically select the best model for each user message based on task complexity.
Saves money by handling simple tasks locally and only escalating to expensive
API models when the task requires it.

## When to Activate

Run the classification step on EVERY incoming user message BEFORE generating a response.
Do NOT classify messages that start with "/" (these are commands, not tasks).

## Workflow

1. Take the user's full message text.
2. Run the classifier:

```
python3 {baseDir}/scripts/classify.py "USER_MESSAGE_HERE"
```

3. Parse the JSON output. It returns:

```json
{"model": "provider/model-name", "tier": "simple|moderate|coding|complex", "reason": "..."}
```

4. Use the `model` value from the output to switch the session model:

```
session_status(model="<value from model field>")
```

5. Then proceed to answer the user's message using the newly selected model.

## Tier Routing Table

| Tier     | Model                             | Why                                    |
|----------|-----------------------------------|----------------------------------------|
| simple   | ollama/dengcao/Qwen3-32B:Q5_K_M  | Free local model, handles basic tasks  |
| moderate | anthropic/claude-sonnet-4-5       | Balanced cost and capability           |
| coding   | openai-codex/gpt-5.2             | Optimized for code generation/debugging|
| complex  | anthropic/claude-opus-4-5         | Maximum reasoning power                |

## Fallback Behavior

If Ollama is unreachable or the classifier fails, defaults to **moderate** (Sonnet).
If the model returns an invalid tier, the normalizer picks the best match.

## Important Notes

- The triage model (qwen3:1.7b) runs locally via Ollama at localhost:11434.
- Classification typically takes less than 500ms.
- Uses think:false to disable reasoning mode for speed.
- Do NOT re-classify follow-up messages in the same conversational turn.
- If the user explicitly requests a specific model (e.g., "use opus for this"), honor that instead.
