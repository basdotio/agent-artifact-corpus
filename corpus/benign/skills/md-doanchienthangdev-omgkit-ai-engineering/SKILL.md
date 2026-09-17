---
name: ai-engineering
description: Building production AI applications with Foundation Models. Covers prompt engineering, RAG, agents, finetuning, evaluation, and deployment. Use when working with LLMs, building AI features, or architecting AI systems.
---

# AI Engineering Skills

Comprehensive skills for building AI applications with Foundation Models.

## AI Engineering Stack

```
┌─────────────────────────────────────────────────────┐
│  APPLICATION LAYER                                   │
│  Prompt Engineering, RAG, Agents, Guardrails        │
├─────────────────────────────────────────────────────┤
│  MODEL LAYER                                         │
│  Model Selection, Finetuning, Evaluation            │
├─────────────────────────────────────────────────────┤
│  INFRASTRUCTURE LAYER                                │
│  Inference Optimization, Caching, Orchestration     │
└─────────────────────────────────────────────────────┘
```

## 12 Core Skills

| Skill | Description | Guide |
|-------|-------------|-------|
| Foundation Models | Model architecture, sampling, structured outputs | [foundation-models/](foundation-models/SKILL.md) |
| Evaluation Methodology | Metrics, AI-as-judge, comparative evaluation | [evaluation-methodology/](evaluation-methodology/SKILL.md) |
| AI System Evaluation | End-to-end evaluation, benchmarks, model selection | [ai-system-evaluation/](ai-system-evaluation/SKILL.md) |
| Prompt Engineering | System prompts, few-shot, chain-of-thought, defense | [prompt-engineering/](prompt-engineering/SKILL.md) |
| RAG Systems | Chunking, embedding, retrieval, reranking | [rag-systems/](rag-systems/SKILL.md) |
| AI Agents | Tool use, planning strategies, memory systems | [ai-agents/](ai-agents/SKILL.md) |
| Finetuning | LoRA, QLoRA, PEFT, model merging | [finetuning/](finetuning/SKILL.md) |
| Dataset Engineering | Data quality, curation, synthesis, annotation | [dataset-engineering/](dataset-engineering/SKILL.md) |
| Inference Optimization | Quantization, batching, caching, speculative decoding | [inference-optimization/](inference-optimization/SKILL.md) |
| AI Architecture | Gateway, routing, observability, deployment | [ai-architecture/](ai-architecture/SKILL.md) |
| Guardrails & Safety | Input/output guards, PII protection, injection defense | [guardrails-safety/](guardrails-safety/SKILL.md) |
| User Feedback | Explicit/implicit signals, feedback loops, A/B testing | [user-feedback/](user-feedback/SKILL.md) |

## Development Process

```
1. Use Case Evaluation → 2. Model Selection → 3. Evaluation Pipeline
                                                      ↓
4. Prompt Engineering → 5. Context (RAG/Agents) → 6. Finetuning (if needed)
                                                      ↓
7. Inference Optimization → 8. Deployment → 9. Monitoring & Feedback
```

## Quick Decision Guide

| Need | Start With |
|------|------------|
| Improve output quality | prompt-engineering |
| Add external knowledge | rag-systems |
| Multi-step reasoning | ai-agents |
| Reduce latency/cost | inference-optimization |
| Measure quality | evaluation-methodology |
| Protect system | guardrails-safety |

## Reference

Based on "AI Engineering" by Chip Huyen (O'Reilly, 2025).
