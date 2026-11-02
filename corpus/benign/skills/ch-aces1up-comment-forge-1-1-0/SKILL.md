---
name: Comment Forge
slug: comment-forge
version: 1.0.0
description: Corpus-grounded Reddit comment engine. Generate natural replies that pass AI detection, powered by real comment corpus and 7-dimension QA scoring.
author: OpenClaw
license: MIT
tags:
  - reddit
  - comments
  - ai-detection
  - content
  - marketing
  - copywriting
requires:
  - python>=3.10
---

# Comment Forge

Generate Reddit-native comments that sound like a real person wrote them. Powered by a real Reddit comment corpus and a 7-dimension QA pipeline that catches AI fingerprints.

## What It Does

Feed it a post title, body, and existing comments. Get back a natural reply that:

- **Matches the thread tone** using corpus-informed few-shot prompting
- **Passes AI detection** via 7-dimension QA scoring (naturalness, value, subtlety, tone, detection risk, length, AI fingerprint)
- **Strips AI tells** with deterministic anti-AI cleaning (em-dashes, smart quotes, 50+ AI vocabulary swaps)
- **Adds subtle humanness** with smart typo injection (40% chance, max 1 per draft, never on product names)

## Two Modes

**Value-First**: Pure tactical advice. No product mention. Great for building karma and credibility.

**Product-Drop**: Mention a product naturally in the reply. Auto-fit scoring determines if the product fits the thread (1-10 score). If it doesn't fit naturally, falls back to value-first.

## Pipeline

1. **Corpus Sampling** - Stratified, score-weighted real Reddit comment examples
2. **Fit Scoring** - Classify thread intent, recommend mode (optional, for product-drop)
3. **Draft Generation** - Corpus-informed few-shot prompting via Gemini or OpenRouter
4. **QA Pipeline** - Score, revise, re-score loop (3 attempts for product-drop, 7 for value-first)
5. **Anti-AI Cleaning** - Deterministic post-processing strips AI vocabulary, em-dashes, smart quotes
6. **Human Touch** - Smart typo injection for believable imperfections

## Quick Start

```bash
bash setup.sh
source .venv/bin/activate

# Value-first (no product)
python3 comment_forge.py --post "Best CRM for small teams?"

# Product-drop
python3 comment_forge.py --post "What tools do you use for email?" \
  --product "Acme Mail" --product-desc "Email automation for small teams"

# With existing comments for tone matching
python3 comment_forge.py --post "How do you handle cold outreach?" \
  --comments "I use Apollo" "LinkedIn works best imo"

# From JSON file
python3 comment_forge.py --file post.json --json

# Skip QA (faster)
python3 comment_forge.py --post "..." --skip-qa
```

## JSON File Format

```json
{
  "title": "Best CRM for small teams?",
  "body": "Looking for something simple...",
  "comments": [
    "I use HubSpot free tier",
    "Notion works if you're small"
  ],
  "product": "Acme CRM",
  "product_url": "https://acme.com",
  "product_description": "Simple CRM for small teams",
  "category": "saas",
  "mode": "product_drop"
}
```

## API Keys

| Key | Required | Purpose |
|-----|----------|---------|
| `GEMINI_API_KEY` | Yes (or OpenRouter) | Primary LLM for generation + QA |
| `OPENROUTER_API_KEY` | Fallback | Alternative LLM provider |
| `CEREBRAS_API_KEY` | Optional | Fast fit scoring (free tier) |

## QA Dimensions

| Dimension | Weight | What It Checks |
|-----------|--------|----------------|
| naturalness | 15% | Does it sound like a real person? |
| value_contribution | 15% | Does it help the thread? |
| subtlety | 20% | Is the product mention (if any) natural? |
| tone_match | 10% | Does it match thread + corpus tone? |
| detection_risk | 10% | Would redditors flag it as spam? |
| length_appropriate | 10% | Right length for this thread type? |
| ai_fingerprint | 20% | Em-dashes, AI vocab, perfect grammar? |

Pass threshold: 7.0/10 composite score.