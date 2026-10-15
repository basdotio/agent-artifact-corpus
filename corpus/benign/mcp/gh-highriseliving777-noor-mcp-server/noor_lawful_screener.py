#!/usr/bin/env python3
"""
noor_lawful_screener.py — Deterministic lawful/unlawful screening.

ARCHITECTURE:
  Step 1: Keyword pre-filter detects categories
  Step 2: Code checks for first-person direct participation (WE are the actor)
  Step 3: Tier is determined by code, not LLM:
    - BLOCKED: only if WE directly participate in unlawful activity (retired, never fires)
    - FLAGGED: any category detected, client bears responsibility
    - CLEAR: no categories detected

Design principle (Sam's ruling, 2026-08-19):
  We sell IT SERVICES, not participation in the underlying activity.
  We screen for unlawful-adjacent elements. We flag them.
  The client bears responsibility for their own compliance.
  We never engage directly in unlawful activity.
  We never manually review certificates.

External terminology: lawful, unlawful, usury, uncertainty, gambling, alcohol, pork, adult content, weapons.

Disclaimer: Orientation, not adjudication. Not a fatwa. Consult a qualified scholar.
"""

import os
import re
import json
import hashlib
import requests
from pathlib import Path
from typing import Tuple, Dict, List

# --- Configuration ---
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
LOCAL_MODEL = "qwen2.5:3b"
CLOUD_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
UNLAWFUL_REFERENCE_FILE = Path(__file__).parent / "_reference" / "references" / "unlawful_categories.md"
AAOIFI_SUMMARY_FILE = Path(__file__).parent / "_reference" / "references" / "aaoifi_screener_summary.md"

DISCLAIMER = (
    "This screening is automated and based on publicly available scholarship. "
    "It is not a religious ruling. For definitive guidance, consult a qualified scholar. "
    "Noor provides orientation, not adjudication."
)

# --- Layer 1: Keyword patterns per category ---
KEYWORD_PATTERNS = {
    "usury": [
        r"\binterest\s+rate\b", r"\bmortgage\b", r"\bloan\b", r"\bAPR\b", r"\bAPY\b",
        r"\bbond\b", r"\btreasury\b", r"\bcredit\s+card\b", r"\bpayday\b",
        r"\bstudent\s+loan\b", r"\busury\b"
    ],
    "gambling": [
        r"\bcasino\b", r"\bbetting\b", r"\bbet\b", r"\bpoker\b", r"\blottery\b",
        r"\bblackjack\b", r"\broulette\b", r"\bslots?\b", r"\bwagering\b",
        r"\bsports\s+betting\b", r"\bsweepstakes\b", r"\bfantasy\s+sports\b",
        r"\bbookmaker\b", r"\bgambling\b"
    ],
    "uncertainty": [
        r"\bspeculative\s+derivative\b", r"\bshort\s+selling\b"
    ],
    "alcohol": [
        r"\balcohol\b", r"\bliquor\b", r"\bwine\b", r"\bbeer\b", r"\bbrewery\b",
        r"\bdistillery\b", r"\bwinery\b", r"\bnightclub\b"
    ],
    "pork": [
        r"\bpork\b", r"\bbacon\b", r"\bham\b"
    ],
    "adult_content": [
        r"\bpornography\b", r"\bporn\b", r"\badult\s+content\b",
        r"\bexplicit\s+content\b", r"\bprostitution\b"
    ],
    "weapons": [
        r"\bweapons?\s+production\b", r"\bweapons?\s+sale\b",
        r"\bweapons?\s+distribution\b"
    ],
    "tobacco_drugs": [
        r"\btobacco\b", r"\brecreational\s+drug\b", r"\bnarcotics?\b", r"\bmakhdarat\b"
    ]
}

COMPILED_KEYWORDS = {
    cat: [re.compile(p, re.IGNORECASE) for p in patterns]
    for cat, patterns in KEYWORD_PATTERNS.items()
}

# --- Direct participation patterns (WE are the actor) ---
DIRECT_PARTICIPATION_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\bwe\s+(?:will|want\s+to|need\s+to|plan\s+to|intend\s+to)\s+(?:take|accept|operate|run|own|sell|buy|engage|invest|start)",
        r"\bour\s+(?:own|company|business|firm)\s+.*(?:casino|gambling|interest|loan|brewery|alcohol)",
        r"\bwe\s+are\s+(?:taking|operating|running|selling|buying|starting)",
        r"\bfor\s+ourselves\b",
        r"\bwe\s+ourselves\b",
    ]
]

def detect_direct_participation(task: str) -> bool:
    """Return True only if WE (Noor/Sam/Aarif) are the direct actor."""
    for pattern in DIRECT_PARTICIPATION_PATTERNS:
        if pattern.search(task):
            return True
    return False

# --- Layer 2: LLM subtle check (only when no keywords detected) ---
def load_lawful_reference() -> str:
    """Load both reference files: the 15-category list + the AAOIFI summary."""
    parts = []
    if UNLAWFUL_REFERENCE_FILE.exists():
        parts.append(UNLAWFUL_REFERENCE_FILE.read_text())
    if AAOIFI_SUMMARY_FILE.exists():
        parts.append("\n\n=== AAOIFI KEY DEFINITIONS ===\n\n")
        parts.append(AAOIFI_SUMMARY_FILE.read_text())
    if not parts:
        return "(Reference files not found)"
    return "".join(parts)

def call_ollama(prompt: str) -> str:
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": LOCAL_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 200}
        }, timeout=60)
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
    except Exception:
        pass
    return ""

def call_openrouter(prompt: str) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return ""
    try:
        resp = requests.post(OPENROUTER_URL, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }, json={
            "model": CLOUD_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200
        }, timeout=30)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return ""

def llm_detect_categories(task: str) -> List[str]:
    """Ask the LLM to identify any unlawful-adjacent categories. Returns list."""
    reference = load_lawful_reference()
    prompt = "You identify whether a task involves any of these unlawful-adjacent categories:\n\n"
    prompt += reference + "\n\n"
    prompt += "TASK: " + task + "\n\n"
    prompt += "If the task involves ANY of the above categories (even if only building software FOR such a business), respond with a JSON list of the category names.\n"
    prompt += "If no category applies, respond with [].\n"
    prompt += 'Format: ["category1", "category2"] or []\n'
    prompt += "Respond with ONLY the JSON list, nothing else."

    response = call_ollama(prompt)
    if not response:
        response = call_openrouter(prompt)

    if response:
        try:
            result = json.loads(response)
            if isinstance(result, list):
                # Normalize category names
                valid = set(COMPILED_KEYWORDS.keys())
                return [c for c in result if c in valid]
        except json.JSONDecodeError:
            match = re.search(r"\[.*?\]", response, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group())
                    if isinstance(result, list):
                        valid = set(COMPILED_KEYWORDS.keys())
                        return [c for c in result if c in valid]
                except json.JSONDecodeError:
                    pass
    return []

# --- Layer 3: Deterministic screen_task ---
def hash_task(task: str) -> str:
    return "sha256:" + hashlib.sha256(task.encode()).hexdigest()[:16]

def screen_task(task_description: str) -> Tuple[str, Dict]:
    if not task_description or not task_description.strip():
        return "CLEAR", {
            "tier": "CLEAR",
            "categories": [],
            "reasoning": "Empty task — nothing to screen.",
            "task_hash": hash_task(task_description or ""),
            "disclaimer": DISCLAIMER
        }

    # Step 1: Keyword pre-filter
    detected = []
    for category, patterns in COMPILED_KEYWORDS.items():
        for pattern in patterns:
            if pattern.search(task_description):
                detected.append(category)
                break

    # Step 2: Check for first-person direct participation
    is_direct = detect_direct_participation(task_description)

    # Step 3: Deterministic tier logic
    if is_direct and detected:
        # BLOCKED — we are the actor and it is unlawful. Retired: never fires in practice.
        return "BLOCKED", {
            "tier": "BLOCKED",
            "categories": detected,
            "reasoning": "Noor will never directly participate in unlawful activity.",
            "task_hash": hash_task(task_description),
            "disclaimer": DISCLAIMER
        }

    if detected:
        # FLAGGED — client business involves unlawful-adjacent elements, we are IT providers
        return "FLAGGED", {
            "tier": "FLAGGED",
            "categories": sorted(set(detected)),
            "reasoning": "Client business involves unlawful-adjacent elements: " + ", ".join(sorted(set(detected))) + ". Noor provides IT services only; the client bears responsibility for their compliance.",
            "task_hash": hash_task(task_description),
            "disclaimer": DISCLAIMER
        }

    # Step 4: No keywords detected — LLM subtle check
    subtle_categories = llm_detect_categories(task_description)
    if subtle_categories:
        return "FLAGGED", {
            "tier": "FLAGGED",
            "categories": subtle_categories,
            "reasoning": "Screening detected unlawful-adjacent elements via reasoning: " + ", ".join(subtle_categories) + ". Noor provides IT services only.",
            "task_hash": hash_task(task_description),
            "disclaimer": DISCLAIMER
        }

    # Step 5: CLEAR
    return "CLEAR", {
        "tier": "CLEAR",
        "categories": [],
        "reasoning": "No unlawful-adjacent elements detected.",
        "task_hash": hash_task(task_description),
        "disclaimer": DISCLAIMER
    }

def get_screener_status() -> dict:
    return {
        "status": "active",
        "mode": "deterministic three-tier (CLEAR/FLAGGED/BLOCKED)",
        "layers": ["keyword_prefilter", "direct_participation_check", "llm_subtle_check"],
        "llm_primary": LOCAL_MODEL,
        "llm_fallback": CLOUD_MODEL if os.environ.get("OPENROUTER_API_KEY") else "none",
        "unlawful_reference": str(UNLAWFUL_REFERENCE_FILE),
        "aaoifi_summary": str(AAOIFI_SUMMARY_FILE),
        "manual_review_required": False,
        "blocked_is_retired": True,
        "disclaimer": "Orientation, not adjudication."
    }

# Backward-compatible alias
def get_firewall_status() -> dict:
    return get_screener_status()

# --- Testing ---
if __name__ == "__main__":
    print("Testing noor_lawful_screener.py (deterministic)")
    print("=" * 70)
    test_cases = [
        "Build a CRM for a construction company",
        "Build a casino platform",
        "Write code for a mortgage rate comparison website",
        "Build a booking system for a hotel that serves alcohol",
        "Build a sports betting app",
        "Create a website for a bakery",
        "We want to take an interest loan for our own expansion",
        "Design a UI for a brewery",
    ]
    for task in test_cases:
        print()
        print("Task: " + task)
        tier, result = screen_task(task)
        print("  Tier: " + tier)
        print("  Categories: " + str(result.get("categories", [])))
        print("  Reasoning: " + result.get("reasoning", "")[:150])
    print()
    print("=" * 70)
    print("Status:", json.dumps(get_screener_status(), indent=2))
