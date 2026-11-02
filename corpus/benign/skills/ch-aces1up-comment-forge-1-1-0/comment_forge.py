#!/usr/bin/env python3
"""
comment_forge.py — Corpus-grounded Reddit comment engine.

Feed it a post title, body, and comments. Get back a natural, QA'd reply
that sounds like a real person wrote it. Uses a real Reddit comment corpus
for few-shot prompting and 7-dimension QA scoring.

Two modes:
  product_drop: Mention a product naturally in the reply
  value_first:  Pure tactical advice, no product mention

Full pipeline:
  1. Corpus sampling (stratified, score-weighted)
  2. Fit scoring (classify thread intent, recommend mode)
  3. Draft generation (corpus-informed few-shot)
  4. QA pipeline (7-dim scoring + anti-AI cleaning + typo injection + revision loop)

Usage:
  python3 comment_forge.py --post "Best CRM for small teams?" --mode value_first
  python3 comment_forge.py --post "What tools do you use?" --product "Acme CRM" --product-url "https://acme.com"
  python3 comment_forge.py --file post.json --mode product_drop
  python3 comment_forge.py --post "..." --comments "Great question" "I use X" --json
  python3 comment_forge.py --corpus-stats

Requires:
  GEMINI_API_KEY or OPENROUTER_API_KEY (at least one)
  CEREBRAS_API_KEY (optional, for fit scoring)
"""

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time

try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q",
                           "requests", "python-dotenv"])
    import requests
    from dotenv import load_dotenv

# ─── Load env ────────────────────────────────────────────────────────────────

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_env_path = os.path.join(_SCRIPT_DIR, ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path)

# Also check ~/.comment-forge/config for keys
_home_config = os.path.expanduser("~/.comment-forge/config.json")
if os.path.exists(_home_config):
    try:
        with open(_home_config) as f:
            _cfg = json.load(f)
        for k, v in _cfg.items():
            env_key = k.upper().replace("-", "_")
            if v and not os.environ.get(env_key):
                os.environ[env_key] = str(v)
    except Exception:
        pass

VERSION = "1.0.0"

# ─── Config ──────────────────────────────────────────────────────────────────

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
TWITTERAPI_KEY = os.environ.get("TWITTERAPI_KEY", "")
CF_INSTALL_ID = os.environ.get("CF_INSTALL_ID", "")

# API endpoints
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL = "gemini-2.5-flash"
OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "google/gemini-2.5-flash-preview"
CEREBRAS_API_URL = "https://api.cerebras.ai/v1/chat/completions"
CEREBRAS_MODEL = "llama3.1-8b"

# Corpus API (hosted)
CORPUS_API_BASE = os.environ.get(
    "CF_CORPUS_API",
    "https://clawagents.dev/reddit-rank/v1/cf/corpus"
)

# Analytics
ANALYTICS_URL = os.environ.get(
    "CF_ANALYTICS_URL",
    "https://clawagents.dev/reddit-rank/v1/cf/usage"
)

# QA config
QA_WEIGHTS = {
    "naturalness": 0.15,
    "value_contribution": 0.15,
    "subtlety": 0.20,
    "tone_match": 0.10,
    "detection_risk": 0.10,
    "length_appropriate": 0.10,
    "ai_fingerprint": 0.20,
}
QA_PASS_THRESHOLD = 7.0
QA_MAX_RETRIES_PRODUCT = 2   # 3 total attempts for product-drop
QA_MAX_RETRIES_VALUE = 6     # 7 total attempts for value-first
FIT_SCORE_THRESHOLD = 8


# ─── Logging ─────────────────────────────────────────────────────────────────

_VERBOSE = False

def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def vlog(msg):
    if _VERBOSE:
        log(msg)


# ─── Analytics ───────────────────────────────────────────────────────────────

def _report_usage(mode, post_hash, success, error_msg=None):
    """Silent analytics phone-home."""
    if not CF_INSTALL_ID:
        return
    try:
        requests.post(ANALYTICS_URL, json={
            "install_id": CF_INSTALL_ID,
            "tool": "comment-forge",
            "version": VERSION,
            "mode": mode,
            "query_hash": post_hash,
            "results": 1 if success else 0,
            "error": error_msg,
        }, timeout=5)
    except Exception:
        pass


# ─── Anti-AI: Deterministic Cleaner ─────────────────────────────────────────

_AI_VOCAB = {
    "straightforward": "simple",
    "comprehensive": "solid",
    "navigate": "deal with",
    "navigating": "dealing with",
    "leverage": "use",
    "leveraging": "using",
    "utilize": "use",
    "utilizing": "using",
    "regarding": "about",
    "numerous": "a lot of",
    "significant": "big",
    "significantly": "way",
    "subsequently": "then",
    "facilitate": "help with",
    "facilitating": "helping with",
    "implement": "set up",
    "implementing": "setting up",
    "Additionally": "also",
    "Furthermore": "plus",
    "Moreover": "also",
    "Consequently": "so",
    "Nevertheless": "still",
    "In conclusion": "",
    "I hope this helps": "",
    "Feel free to": "",
    "Don't hesitate to": "",
    "it's worth noting": "fwiw",
    "It's worth noting": "fwiw",
    "game-changer": "solid",
    "game changer": "solid",
    "highly recommend": "def recommend",
    "I cannot recommend": "def recommend",
    "seamless": "smooth",
    "robust": "solid",
    "streamline": "speed up",
    "streamlined": "quick",
    "exceptional": "great",
    "invaluable": "super useful",
    "delve": "look into",
    "delving": "looking into",
    "plethora": "bunch",
    "myriad": "bunch of",
    "meticulous": "careful",
    "elevate": "step up",
    "pivotal": "key",
    "testament": "proof",
    "embark": "start",
    "commendable": "solid",
    "aligns with": "fits",
    "in terms of": "for",
    "at the end of the day": "tbh",
    "the bottom line is": "basically",
}

_HUMAN_TYPOS = {
    "definitely": "definately",
    "separate": "seperate",
    "experience": "experiance",
    "recommend": "reccomend",
    "different": "diffrent",
    "probably": "prolly",
    "because": "becuase",
    "received": "recieved",
    "through": "thru",
    "though": "tho",
    "really": "realy",
    "would": "woud",
    "their": "thier",
    "until": "untill",
    "already": "allready",
    "happened": "happend",
    "something": "somthing",
    "honestly": "honeslty",
    "basically": "basicaly",
    "especially": "expecially",
}

_TYPO_BLACKLIST = {"http", "https", "www", "com", "reddit", "r/", "u/"}


def anti_ai_clean(draft):
    """Strip AI fingerprints that LLMs can't self-detect."""
    draft = draft.replace("\u2014", " - ")
    draft = draft.replace("\u2013", " - ")
    draft = draft.replace(" -  ", " - ")
    draft = draft.replace("\u201c", '"').replace("\u201d", '"')
    draft = draft.replace("\u2018", "'").replace("\u2019", "'")

    for ai_word, human_word in _AI_VOCAB.items():
        draft = draft.replace(ai_word, human_word)
        draft = draft.replace(ai_word.lower(), human_word.lower())

    draft = draft.replace("; ", ". ")
    draft = draft.replace("\u2026", "..")
    draft = re.sub(r'\.{3,}', '..', draft)
    draft = re.sub(r'  +', ' ', draft)
    draft = re.sub(r'\.\s*\.', '.', draft)
    draft = re.sub(r'^\s*[,.]', '', draft)
    return draft.strip()


def inject_humanness(draft, product_name=""):
    """Add max 1 subtle typo. 40% chance. Never on product names or URLs."""
    if random.random() > 0.4:
        return draft

    blacklist = set(_TYPO_BLACKLIST)
    if product_name:
        blacklist.update(w.lower() for w in product_name.split())

    candidates = []
    words = draft.split()
    for i, word in enumerate(words):
        if i == 0 or i >= len(words) - 1:
            continue
        clean_word = word.strip(".,!?()\"'").lower()
        if clean_word in blacklist:
            continue
        if clean_word in _HUMAN_TYPOS:
            candidates.append((i, word, clean_word))

    if not candidates:
        return draft

    idx, original_word, clean_key = random.choice(candidates)
    typo = _HUMAN_TYPOS[clean_key]

    leading = ""
    trailing = ""
    core = original_word
    while core and not core[0].isalpha():
        leading += core[0]
        core = core[1:]
    while core and not core[-1].isalpha():
        trailing = core[-1] + trailing
        core = core[:-1]

    if core and core[0].isupper():
        typo = typo[0].upper() + typo[1:]

    words[idx] = leading + typo + trailing
    return " ".join(words)


# ─── Corpus API Client ──────────────────────────────────────────────────────

def fetch_corpus_samples(category, count=5, mode="generation", mention_style=None, exclude_ids=None):
    """Fetch corpus samples from the hosted API."""
    try:
        params = {"category": category, "count": count, "mode": mode}
        if mention_style:
            params["mention_style"] = mention_style
        if exclude_ids:
            params["exclude_ids"] = ",".join(str(i) for i in exclude_ids)

        resp = requests.get(f"{CORPUS_API_BASE}/samples", params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("samples", []), data.get("formatted", "")
        vlog(f"Corpus API returned {resp.status_code}")
        return [], ""
    except Exception as e:
        vlog(f"Corpus API error: {e}")
        return [], ""


def fetch_corpus_antipatterns(category, count=2):
    """Fetch antipattern examples from the hosted API."""
    try:
        resp = requests.get(
            f"{CORPUS_API_BASE}/antipatterns",
            params={"category": category, "count": count},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("samples", []), data.get("formatted", "")
        return [], ""
    except Exception:
        return [], ""


def fetch_corpus_stats():
    """Get corpus statistics."""
    try:
        resp = requests.get(f"{CORPUS_API_BASE}/stats", timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return {}
    except Exception:
        return {}


# ─── Real-Time Intel (Serper + X-Scout/TwitterAPI) ───────────────────────────

TWITTERAPI_SEARCH_URL = "https://api.twitterapi.io/twitter/tweet/advanced_search"


def _fetch_serper_context(query, num_results=5):
    """Search Google via Serper for relevant tactical snippets."""
    if not SERPER_API_KEY:
        return []
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            json={"q": query, "num": num_results},
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        snippets = []
        for r in data.get("organic", [])[:num_results]:
            snippet = r.get("snippet", "")
            title = r.get("title", "")
            if snippet:
                snippets.append(f"{title}: {snippet}")
        return snippets
    except Exception:
        return []


def _simplify_query(query):
    """Use Cerebras to simplify a long query into 2-4 search keywords."""
    if len(query.split()) <= 4:
        return query
    result = _call_cerebras(
        f"Simplify this into 2-4 broad search keywords for Twitter. "
        f"Return ONLY the keywords, nothing else: \"{query}\"",
        temperature=0.1, max_tokens=30)
    if "error" not in result:
        simplified = result["text"].strip().strip('"').strip("'")
        if 1 < len(simplified.split()) <= 5:
            return simplified
    # Fallback: take first 4 meaningful words
    words = [w for w in query.split() if len(w) > 3][:4]
    return " ".join(words) if words else query


def _fetch_x_posts(query, count=10):
    """Search Twitter/X via TwitterAPI.io for practitioner posts."""
    if not TWITTERAPI_KEY:
        return []
    try:
        simplified = _simplify_query(query)
        vlog(f"X-Scout query: \"{simplified}\"")

        resp = requests.get(
            TWITTERAPI_SEARCH_URL,
            params={"query": simplified, "queryType": "Latest", "cursor": ""},
            headers={"X-API-Key": TWITTERAPI_KEY},
            timeout=30,
        )
        if resp.status_code != 200:
            vlog(f"TwitterAPI returned {resp.status_code}")
            return []

        data = resp.json()
        tweets = data.get("tweets", [])
        if not tweets:
            return []

        posts = []
        for t in tweets[:count]:
            text = t.get("text", "")
            if not text or len(text) < 30:
                continue
            if text.startswith("RT @"):
                continue
            author = t.get("author", {}).get("userName", "anon")
            likes = t.get("likeCount", 0) or 0
            views = t.get("viewCount", 0) or 0
            posts.append(f"@{author} ({likes} likes, {views} views): {text[:280]}")
        return posts
    except Exception as e:
        vlog(f"TwitterAPI error: {e}")
        return []


def get_tactical_context(thread_title, product_description="", subreddit=""):
    """Fetch real-time tactical context for value-first generation.

    Combines Google search snippets + Twitter/X practitioner posts.
    """
    clean_title = thread_title
    for prefix in ["What's the best", "What is the best", "Anyone tried",
                    "Recommend me", "Looking for", "Help me find"]:
        if clean_title.lower().startswith(prefix.lower()):
            clean_title = clean_title[len(prefix):].strip(" ?")
            break

    serper_query = f"{clean_title} best practices tips"
    if subreddit:
        serper_query = f"{clean_title} {subreddit} tips"

    x_query = clean_title

    vlog("Fetching real-time intel (Serper + X-Scout)...")
    serper_snippets = _fetch_serper_context(serper_query, num_results=5)
    x_posts = _fetch_x_posts(x_query, count=10)

    # Retry X with product description if first attempt returned nothing
    if not x_posts and product_description:
        fallback_query = product_description.split(".")[0][:60]
        vlog(f"X-Scout retry with fallback: {fallback_query[:50]}")
        x_posts = _fetch_x_posts(fallback_query, count=10)

    has_context = bool(serper_snippets or x_posts)
    if has_context:
        vlog(f"  Serper: {len(serper_snippets)} snippets, X: {len(x_posts)} posts")
    else:
        vlog("  No real-time context found")

    return {
        "serper_snippets": serper_snippets,
        "x_posts": x_posts,
        "has_context": has_context,
    }


# ─── LLM Callers (sync) ─────────────────────────────────────────────────────

def _call_gemini(system_prompt, user_prompt, temperature=0.8, max_tokens=1024):
    """Call Gemini direct API. Returns {"text": str} or {"error": str}."""
    if not GEMINI_API_KEY:
        return {"error": "No GEMINI_API_KEY configured"}

    try:
        resp = requests.post(
            f"{GEMINI_BASE}/models/{GEMINI_MODEL}:generateContent",
            headers={
                "x-goog-api-key": GEMINI_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"parts": [{"text": user_prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                    "thinkingConfig": {"thinkingBudget": 0},
                },
            },
            timeout=60,
        )
        if resp.status_code != 200:
            return {"error": f"Gemini API error {resp.status_code}: {resp.text[:200]}"}

        data = resp.json()
        text = (data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", ""))
        if not text:
            return {"error": "Gemini returned empty response"}
        return {"text": text}
    except Exception as e:
        return {"error": f"Gemini request failed: {e}"}


def _call_openrouter(system_prompt, user_prompt, temperature=0.8, max_tokens=300, model=None):
    """Call OpenRouter API. Returns {"text": str} or {"error": str}."""
    if not OPENROUTER_API_KEY:
        return {"error": "No OPENROUTER_API_KEY configured"}

    try:
        resp = requests.post(
            OPENROUTER_BASE,
            json={
                "model": model or OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        if resp.status_code != 200:
            return {"error": f"OpenRouter API error {resp.status_code}: {resp.text[:200]}"}

        data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not text:
            return {"error": "OpenRouter returned empty response"}
        return {"text": text}
    except Exception as e:
        return {"error": f"OpenRouter request failed: {e}"}


def _call_cerebras(prompt, temperature=0.2, max_tokens=200):
    """Call Cerebras API for fast classification. Returns {"text": str} or {"error": str}."""
    if not CEREBRAS_API_KEY:
        return {"error": "No CEREBRAS_API_KEY configured"}

    keys = [k.strip() for k in CEREBRAS_API_KEY.split(",") if k.strip()]
    for key in keys:
        try:
            resp = requests.post(
                CEREBRAS_API_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": CEREBRAS_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                text = resp.json()["choices"][0]["message"]["content"].strip()
                return {"text": text}
        except Exception:
            continue
    return {"error": "All Cerebras keys failed"}


def _call_llm(system_prompt, user_prompt, temperature=0.8, max_tokens=1024):
    """Try Gemini first, fall back to OpenRouter."""
    if GEMINI_API_KEY:
        result = _call_gemini(system_prompt, user_prompt, temperature, max_tokens)
        if "error" not in result:
            return result, "gemini"
        vlog(f"Gemini failed: {result['error']}")

    if OPENROUTER_API_KEY:
        result = _call_openrouter(system_prompt, user_prompt, temperature, max_tokens)
        if "error" not in result:
            return result, "openrouter"
        vlog(f"OpenRouter failed: {result['error']}")

    return {"error": "No LLM API keys available (set GEMINI_API_KEY or OPENROUTER_API_KEY)"}, None


# ─── Fit Scorer ──────────────────────────────────────────────────────────────

def score_product_fit(thread_title, thread_content, top_comments, product_name, product_description):
    """Score how naturally a product fits this thread (1-10)."""
    comment_context = ""
    if top_comments:
        parts = []
        for c in top_comments[:5]:
            body = c if isinstance(c, str) else c.get("body", "")
            body = body[:150]
            score = 0 if isinstance(c, str) else c.get("score", 0)
            parts.append(f"({score}pts): {body}")
        comment_context = "\n".join(parts)

    prompt = f"""Analyze this Reddit thread and score how naturally a product fits into the conversation.

THREAD TITLE: "{thread_title}"
THREAD CONTENT: {(thread_content or '')[:400]}

TOP COMMENTS:
{comment_context or "(none)"}

PRODUCT: {product_name}
PRODUCT DESCRIPTION: {product_description[:300] if product_description else '(none)'}

Respond with valid JSON only:
{{
  "fit_score": <1-10 float. 10 = thread is explicitly asking for this exact type of product. 1 = product has zero relevance>,
  "thread_intent": "<one of: recommendation_seeking, comparison, problem_solving, discussion, venting, experience_sharing, how_to, news>",
  "reasoning": "<1 sentence explaining the fit score>"
}}"""

    # Try Cerebras first (fast, free)
    result = _call_cerebras(prompt)
    if "error" in result:
        # Fall back to main LLM
        result, _ = _call_llm("You are a thread analyzer. Respond with valid JSON only.", prompt, 0.2, 200)

    if "error" in result:
        return {
            "fit_score": 5.0, "thread_intent": "discussion",
            "recommended_mode": "value_first",
            "reasoning": "Classification failed, defaulting to value-first",
        }

    text = result["text"]
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()

    try:
        parsed = json.loads(text)
        fit_score = float(parsed.get("fit_score", 5))
        thread_intent = parsed.get("thread_intent", "discussion")
        if fit_score >= FIT_SCORE_THRESHOLD and thread_intent in ("recommendation_seeking", "comparison"):
            recommended_mode = "product_drop"
        else:
            recommended_mode = "value_first"
        return {
            "fit_score": round(fit_score, 1),
            "thread_intent": thread_intent,
            "recommended_mode": recommended_mode,
            "reasoning": parsed.get("reasoning", ""),
        }
    except (json.JSONDecodeError, ValueError):
        return {
            "fit_score": 5.0, "thread_intent": "discussion",
            "recommended_mode": "value_first",
            "reasoning": "Parse error, defaulting to value-first",
        }


# ─── Draft Generation ───────────────────────────────────────────────────────

def _build_system_prompt(corpus_examples, antipattern_examples):
    """System prompt for product-drop mode."""
    return f"""You are a real Reddit user who writes genuine, helpful comments. You contribute value to discussions first and only mention tools/products when they naturally fit.

{corpus_examples}

{antipattern_examples}

RULES:
1. Address the thread topic with useful information FIRST
2. Sound like a real person - casual, slightly imperfect, no corporate speak
3. Only mention the product if it genuinely fits the discussion
4. Never use phrases like "I highly recommend", "game-changer", "check out this amazing tool"
5. Match the existing thread tone (read the top comments)
6. Keep it under 150 words unless the thread calls for detail
7. Use lowercase, Reddit-native language (imo, tbh, fwiw - but don't force them)
8. If mentioning a product, also mention a trade-off or limitation
9. Never start with "I" - vary your openings
10. Address the OP's specific situation, don't give generic advice"""


def _build_value_first_system_prompt(corpus_examples, antipattern_examples):
    """System prompt for value-first mode (no product mention)."""
    return f"""You are a real Reddit user who writes genuine, helpful comments. You are an experienced practitioner who shares real tactical advice based on hands-on experience. You do NOT promote any product or tool.

{corpus_examples}

{antipattern_examples}

RULES:
1. Give specific, actionable tactical advice based on real experience
2. Sound like a real person - casual, slightly imperfect, no corporate speak
3. DO NOT mention any product, tool, or service by name - pure advice only
4. Never use phrases like "I highly recommend", "game-changer", "you should definitely"
5. Match the existing thread tone (read the top comments)
6. Keep it under 150 words unless the thread calls for detail
7. Use lowercase, Reddit-native language (imo, tbh, fwiw - but don't force them)
8. Share personal experience, specific numbers, real-world tradeoffs
9. Never start with "I" - vary your openings
10. Address the OP's specific situation with concrete steps, not generic advice
11. If you mention a strategy, explain WHY it works
12. Include at least one specific detail that shows real experience (a number, a timeframe, a gotcha)"""


def _build_user_prompt(thread_title, thread_content, top_comments,
                       product_name, product_url, product_description,
                       mention_style, tone):
    """User prompt for product-drop mode."""
    comment_context = _format_comments(top_comments)

    style_map = {
        "casual_drop": "Mention the product casually in passing, like it's one of several things you've tried.",
        "detailed_review": "Give a more detailed take on the product based on personal experience.",
        "comparison_with_alternative": "Compare the product with 1-2 alternatives you've also used.",
        "responding_to_question": "Directly answer the OP's question, with the product as part of your answer.",
        "unsolicited_recommendation": "Share the product as something you discovered that's relevant.",
        "experience_based": "Lead with your personal experience/story, product comes up naturally.",
    }
    style_instruction = f"\nMention style: {style_map.get(mention_style, mention_style)}" if mention_style else ""
    tone_instruction = f"\nTone: {tone}" if tone else ""

    return f"""Thread: "{thread_title}"

Thread content: {thread_content[:500] if thread_content else "(no body text)"}

Top comments in this thread:
{comment_context or "(no comments yet)"}

Product to subtly mention if relevant:
- Name: {product_name}
- URL: {product_url or "(none)"}
- What it does: {product_description or "(none)"}
{style_instruction}{tone_instruction}

Write a natural Reddit reply that contributes value. If the product fits, mention it casually. If it doesn't fit naturally, just write a helpful reply without mentioning it."""


def _build_value_first_user_prompt(thread_title, thread_content, top_comments, tone,
                                    tactical_context=None):
    """User prompt for value-first mode with optional real-time tactical context."""
    comment_context = _format_comments(top_comments)
    tone_instruction = f"\nTone: {tone}" if tone else ""

    # Build tactical context block from Serper + X-Scout
    tactical_block = ""
    if tactical_context and tactical_context.get("has_context"):
        sections = []
        if tactical_context.get("serper_snippets"):
            snippets = "\n".join(f"- {s}" for s in tactical_context["serper_snippets"][:3])
            sections.append(f"Current info from the web:\n{snippets}")
        if tactical_context.get("x_posts"):
            tweets = "\n".join(f"- {t}" for t in tactical_context["x_posts"][:3])
            sections.append(f"What people are saying on Twitter/X right now:\n{tweets}")
        if sections:
            tactical_block = "\n\nREAL-TIME CONTEXT (use this to inform your advice - incorporate specific details, not just generic tips):\n" + "\n\n".join(sections)

    return f"""Thread: "{thread_title}"

Thread content: {thread_content[:500] if thread_content else "(no body text)"}

Top comments in this thread:
{comment_context or "(no comments yet)"}
{tactical_block}{tone_instruction}

Write a natural Reddit reply that contributes real value. Share specific tactical advice from your experience. DO NOT mention or promote any product, tool, or service - just pure helpful advice that would get upvoted."""


def _format_comments(top_comments):
    """Format comment list for prompt injection."""
    if not top_comments:
        return ""
    parts = []
    for c in top_comments[:5]:
        if isinstance(c, str):
            parts.append(f"- {c[:200]}")
        else:
            author = c.get("author", "anon")
            body = c.get("body", "")[:200]
            score = c.get("score", 0)
            parts.append(f"- u/{author} ({score} pts): {body}")
    return "\n".join(parts)


def generate_draft(thread_title, thread_content, top_comments,
                   product_name="", product_url="", product_description="",
                   category="general", mention_style=None, tone=None,
                   corpus_samples=5, mode="product_drop", tactical_context=None):
    """Generate a corpus-informed draft reply."""
    # Fetch corpus from API
    samples, corpus_text = fetch_corpus_samples(category, corpus_samples, "generation", mention_style)
    _, anti_text = fetch_corpus_antipatterns(category, 2)

    if not corpus_text:
        corpus_text = "(No corpus examples available - generating without few-shot examples)"
    if not anti_text:
        anti_text = ""

    effective_style = mention_style or "experience_based"
    effective_tone = tone or "casual"

    if mode == "value_first":
        system_prompt = _build_value_first_system_prompt(corpus_text, anti_text)
        user_prompt = _build_value_first_user_prompt(
            thread_title, thread_content, top_comments, effective_tone,
            tactical_context=tactical_context)
    else:
        system_prompt = _build_system_prompt(corpus_text, anti_text)
        user_prompt = _build_user_prompt(
            thread_title, thread_content, top_comments,
            product_name, product_url, product_description,
            effective_style, effective_tone)

    result, model_used = _call_llm(system_prompt, user_prompt)
    if "error" in result:
        return {"error": result["error"]}

    return {
        "draft": result["text"].strip(),
        "corpus_context": {
            "category": category,
            "samples_injected": len(samples),
            "mention_style": effective_style if mode == "product_drop" else "none",
            "tone": effective_tone,
        },
        "model": model_used,
        "mode": mode,
        "_samples": samples,
    }


# ─── QA Scoring ──────────────────────────────────────────────────────────────

QA_SYSTEM_PROMPT = """You are a Reddit comment quality analyst specializing in detecting AI-generated content. You evaluate whether AI-generated Reddit reply drafts would pass as natural, genuine comments from real users.

You will be given:
1. REAL high-scoring Reddit comments as GROUND TRUTH reference
2. The thread context (title, content, existing comments)
3. The draft to evaluate

YOUR #1 JOB: Compare the draft against the REAL corpus reference comments. These are PROVEN to get upvotes on Reddit. The draft must match their tone, structure, vocabulary, and imperfections.

You have two tasks:
1. SCORE the draft across 7 dimensions (1-10 scale)
2. If score < 7, REVISE the draft to sound more like the reference comments

CRITICAL - AI FINGERPRINT DETECTION:
- Em-dashes or en-dashes: Real redditors use " - " or nothing
- Corporate/AI vocabulary: "straightforward", "comprehensive", "leverage", "navigate", "utilize", "robust", "seamless", "invaluable", "delve", "pivotal", "testament", "facilitate"
- Transition words AI overuses: "Additionally", "Furthermore", "Moreover", "However,", "Consequently"
- Overly perfect grammar: perfect comma placement, no typos, proper semicolons
- Perfectly structured paragraphs with topic sentences
- "I hope this helps" or "Feel free to" closings
- Smart quotes instead of straight quotes
- Starting multiple sentences the same way

What REAL Reddit comments look like:
- Casual tone, lowercase common, abbreviations (imo, tbh, fwiw, def)
- Run-on sentences, missing commas, occasional typos
- Starting with lowercase, fragments okay
- Dashes as " - " never em-dashes
- Short punchy responses, not essays
- Personal anecdotes with imperfect storytelling
- Acknowledging trade-offs naturally

When REVISING a draft that fails:
- Replace em-dashes with " - " or remove them
- Swap AI vocabulary for casual equivalents
- Drop unnecessary commas and perfect punctuation
- Make it shorter if it reads like an essay
- Add 1 small imperfection (dropped comma, casual abbreviation)
- NEVER introduce typos on the product name"""


def _build_qa_prompt(draft, thread_title, thread_content, top_comments,
                     product_name, corpus_refs, feedback, mode, tactical_context=None):
    """Build QA evaluation prompt."""
    comment_samples = _format_comments(top_comments[:3]) if top_comments else "(none)"

    feedback_section = f"\n\nPREVIOUS REVISION FEEDBACK:\n{feedback}\n" if feedback else ""
    corpus_section = f"\n{corpus_refs}\n" if corpus_refs else ""

    # Build tactical context for revision grounding
    tactical_section = ""
    if mode == "value_first" and tactical_context and tactical_context.get("has_context"):
        parts = []
        if tactical_context.get("serper_snippets"):
            snippets = "\n".join(f"  - {s}" for s in tactical_context["serper_snippets"][:3])
            parts.append(f"Current web intel:\n{snippets}")
        if tactical_context.get("x_posts"):
            tweets = "\n".join(f"  - {t}" for t in tactical_context["x_posts"][:3])
            parts.append(f"Twitter/X practitioner posts:\n{tweets}")
        if parts:
            tactical_section = "\n\nREAL-TIME INTEL (use these specific details when revising the draft - incorporate real data points, not generic advice):\n" + "\n".join(parts) + "\n"

    if mode == "value_first":
        product_section = "MODE: VALUE-FIRST (no product should be mentioned)"
        subtlety_desc = "subtlety: Does this read like genuine advice with NO hidden agenda? No product should be mentioned or hinted at."
        revision_instruction = "If composite < 7, provide a revised version that sounds like genuine tactical advice. Remove ANY product mentions. Use the REAL-TIME INTEL above to ground the revision in specific, current data points. Match the style of the best reference comment."
    else:
        product_section = f"PRODUCT BEING MENTIONED: {product_name}"
        subtlety_desc = "subtlety: If a product is mentioned, is it woven in naturally? Would a real redditor mention it this way?"
        revision_instruction = "If composite < 7, provide a revised version. Keep the product mention but make it feel more natural. Replace em-dashes, swap AI vocab for casual words."

    return f"""THREAD: "{thread_title}"
THREAD CONTENT: {(thread_content or '')[:300]}
TOP COMMENTS:
{comment_samples}

{product_section}
{corpus_section}{tactical_section}{feedback_section}
DRAFT TO EVALUATE:
---
{draft}
---

Compare the draft against both the thread's existing comments AND the reference corpus comments.

Score this draft on each dimension (1-10):
- naturalness: Does it sound like a real person wrote it? Compare against reference comments.
- value_contribution: Does it address the thread topic with useful info?
- {subtlety_desc}
- tone_match: Does the tone match both the thread and the reference comments?
- detection_risk: Would other redditors flag this as spam/promotion? Lower risk = higher score.
- length_appropriate: Is the length similar to natural comments in this type of thread?
- ai_fingerprint: Does the draft contain AI tells? Check for em-dashes, AI vocabulary, perfect grammar, semicolons. Score 10 if zero AI tells, score 1 if reads like ChatGPT.

IMPORTANT - REVISION INSTRUCTIONS:
{revision_instruction}

Output valid JSON only. No markdown, no explanation:

{{
  "scores": {{
    "naturalness": 0,
    "value_contribution": 0,
    "subtlety": 0,
    "tone_match": 0,
    "detection_risk": 0,
    "length_appropriate": 0,
    "ai_fingerprint": 0
  }},
  "issues": ["list specific problems"],
  "suggestions": ["list specific fixes"],
  "revised_draft": "Revised version or null if score >= 7.",
  "verdict": "pass | needs_revision | fail"
}}"""


def _compute_composite(scores):
    """Calculate weighted composite QA score."""
    total = 0
    for dim, weight in QA_WEIGHTS.items():
        total += scores.get(dim, 5) * weight
    return round(total, 1)


def _parse_qa_response(content):
    """Parse JSON from QA model response."""
    if not content:
        return None
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```\w*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        cleaned2 = re.sub(r',\s*([}\]])', r'\1', cleaned)
        try:
            return json.loads(cleaned2)
        except (json.JSONDecodeError, TypeError):
            return None


def score_draft(draft, thread_title, thread_content="", top_comments=None,
                product_name="", corpus_refs="", feedback=None, mode="product_drop",
                tactical_context=None):
    """Score a single draft. Returns QA result dict."""
    prompt = _build_qa_prompt(
        draft, thread_title, thread_content,
        top_comments or [], product_name, corpus_refs, feedback, mode,
        tactical_context=tactical_context)

    result, _ = _call_llm(QA_SYSTEM_PROMPT, prompt, temperature=0.3, max_tokens=2048)
    if "error" in result:
        return {"error": result["error"]}

    parsed = _parse_qa_response(result.get("text", ""))
    if not parsed:
        return {
            "scores": {d: 5 for d in QA_WEIGHTS},
            "composite": 5.0, "verdict": "needs_revision",
            "issues": ["QA scoring parse error"],
            "suggestions": [], "revised_draft": None,
        }

    scores = parsed.get("scores", {})
    composite = _compute_composite(scores)
    verdict = "pass" if composite >= QA_PASS_THRESHOLD else (
        "needs_revision" if composite >= 5 else "fail")

    return {
        "scores": scores,
        "composite": composite,
        "verdict": verdict,
        "issues": parsed.get("issues", []),
        "suggestions": parsed.get("suggestions", []),
        "revised_draft": parsed.get("revised_draft"),
    }


def qa_pipeline(draft, thread_title, thread_content="", top_comments=None,
                product_name="", corpus_refs="", mode="product_drop",
                tactical_context=None):
    """Full QA pipeline: score -> revise -> re-score -> anti-AI clean -> humanize.

    product_drop: 3 total attempts
    value_first: 7 total attempts
    Fallback: product_drop -> value_first after 3 failures
    """
    current_draft = draft
    current_mode = mode
    revision_history = []
    attempts = 0
    mode_fallback = False

    max_retries = QA_MAX_RETRIES_VALUE if mode == "value_first" else QA_MAX_RETRIES_PRODUCT

    for attempt in range(1 + max_retries):
        attempts += 1
        vlog(f"QA attempt {attempts}/{1 + max_retries} (mode: {current_mode})")

        feedback = None
        if revision_history:
            last = revision_history[-1]
            issues = last.get("issues", [])
            if issues:
                feedback = "Previous issues to fix:\n" + "\n".join(f"- {i}" for i in issues)

        result = score_draft(
            current_draft, thread_title, thread_content,
            top_comments, product_name, corpus_refs,
            feedback=feedback, mode=current_mode,
            tactical_context=tactical_context)

        if "error" in result:
            return {
                "final_draft": current_draft,
                "qa": {"composite": 0, "verdict": "fail", "dimensions": {},
                       "attempts": attempts, "issues": [result["error"]], "suggestions": []},
                "revision_history": revision_history,
                "revised_from_original": len(revision_history) > 0,
                "anti_ai_applied": False,
                "mode": current_mode, "mode_fallback": mode_fallback,
            }

        revision_history.append({
            "draft": current_draft,
            "score": result["composite"],
            "attempt": attempts,
            "mode": current_mode,
            "issues": result.get("issues", []),
        })

        vlog(f"  Score: {result['composite']:.1f} ({result['verdict']})")

        if result["verdict"] == "pass":
            break

        if result.get("revised_draft"):
            current_draft = result["revised_draft"]

    # Fallback: product_drop failed -> try value_first
    if result.get("verdict") != "pass" and mode == "product_drop":
        log("Product-drop failed, falling back to value-first mode")
        mode_fallback = True
        current_mode = "value_first"

        # Regenerate in value-first mode (with tactical context)
        regen = generate_draft(
            thread_title, thread_content, top_comments,
            product_name=product_name, mode="value_first",
            tactical_context=tactical_context)

        if regen and "error" not in regen:
            current_draft = regen["draft"]
            remaining = QA_MAX_RETRIES_VALUE - QA_MAX_RETRIES_PRODUCT
            for attempt in range(1 + remaining):
                attempts += 1
                feedback = None
                if revision_history:
                    last = revision_history[-1]
                    issues = last.get("issues", [])
                    if issues:
                        feedback = "Previous issues to fix:\n" + "\n".join(f"- {i}" for i in issues)

                result = score_draft(
                    current_draft, thread_title, thread_content,
                    top_comments, product_name, corpus_refs,
                    feedback=feedback, mode="value_first",
                    tactical_context=tactical_context)

                if "error" in result:
                    break

                revision_history.append({
                    "draft": current_draft,
                    "score": result["composite"],
                    "attempt": attempts,
                    "mode": "value_first",
                    "issues": result.get("issues", []),
                })

                if result["verdict"] == "pass":
                    break
                if result.get("revised_draft"):
                    current_draft = result["revised_draft"]

    # Post-QA: deterministic anti-AI cleaning
    pre_clean = current_draft
    current_draft = anti_ai_clean(current_draft)

    # Post-QA: smart typo injection
    current_draft = inject_humanness(current_draft, product_name=product_name)

    anti_ai_applied = current_draft != pre_clean

    return {
        "final_draft": current_draft,
        "qa": {
            "composite": result.get("composite", 0),
            "verdict": result.get("verdict", "fail"),
            "dimensions": result.get("scores", {}),
            "attempts": attempts,
            "issues": result.get("issues", []),
            "suggestions": result.get("suggestions", []),
        },
        "revision_history": revision_history if len(revision_history) > 1 else [],
        "revised_from_original": len(revision_history) > 1,
        "anti_ai_applied": anti_ai_applied,
        "mode": current_mode,
        "mode_fallback": mode_fallback,
    }


# ─── Main Pipeline ──────────────────────────────────────────────────────────

def run_pipeline(post_title, post_body="", comments=None, product_name="",
                 product_url="", product_description="", category="general",
                 mode=None, mention_style=None, tone=None, skip_qa=False,
                 subreddit=""):
    """Run the full comment forge pipeline.

    If mode is None, auto-detects based on fit scoring.
    """
    comments = comments or []
    post_hash = hashlib.sha256(post_title.encode()).hexdigest()[:12]

    log(f"Post: \"{post_title[:60]}...\"" if len(post_title) > 60 else f"Post: \"{post_title}\"")
    log(f"Comments provided: {len(comments)}")

    # Step 1: Fit scoring (if product provided and mode not forced)
    fit_result = None
    if product_name and mode is None:
        log("Scoring product-thread fit...")
        fit_result = score_product_fit(
            post_title, post_body, comments,
            product_name, product_description)
        mode = fit_result["recommended_mode"]
        log(f"  Fit: {fit_result['fit_score']}/10 | Intent: {fit_result['thread_intent']} | Mode: {mode}")
    elif mode is None:
        mode = "value_first"

    # Step 1.5: Fetch real-time tactical context (Serper + X-Scout/TwitterAPI)
    tactical_context = None
    if SERPER_API_KEY or TWITTERAPI_KEY:
        log("Fetching real-time intel (Serper + X)...")
        tactical_context = get_tactical_context(
            post_title, product_description, subreddit)
        if tactical_context and tactical_context.get("has_context"):
            serper_n = len(tactical_context.get("serper_snippets", []))
            x_n = len(tactical_context.get("x_posts", []))
            log(f"  Intel: {serper_n} web snippets, {x_n} X posts")
        else:
            log("  No real-time intel found (continuing with corpus only)")

    # Step 2: Generate draft
    log(f"Generating draft (mode: {mode})...")
    gen_result = generate_draft(
        post_title, post_body, comments,
        product_name, product_url, product_description,
        category, mention_style, tone, mode=mode,
        tactical_context=tactical_context)

    if "error" in gen_result:
        log(f"Generation failed: {gen_result['error']}")
        _report_usage(mode, post_hash, False, gen_result["error"])
        return {"error": gen_result["error"]}

    log(f"  Draft generated ({gen_result['model']}, {len(gen_result['draft'])} chars)")

    if skip_qa:
        # Apply anti-AI cleaning even without full QA
        final = anti_ai_clean(gen_result["draft"])
        final = inject_humanness(final, product_name)
        _report_usage(mode, post_hash, True)
        return {
            "draft": final,
            "mode": mode,
            "fit": fit_result,
            "qa": None,
            "corpus": gen_result["corpus_context"],
            "tactical_context": bool(tactical_context and tactical_context.get("has_context")),
        }

    # Step 3: Fetch QA corpus refs
    qa_samples, qa_refs_text = fetch_corpus_samples(
        category, 3, "qa",
        exclude_ids=[s.get("id") for s in gen_result.get("_samples", [])])

    # Step 4: QA pipeline
    log("Running QA pipeline...")
    qa_result = qa_pipeline(
        gen_result["draft"], post_title, post_body, comments,
        product_name, qa_refs_text, mode,
        tactical_context=tactical_context)

    log(f"  QA: {qa_result['qa']['composite']:.1f} ({qa_result['qa']['verdict']})")
    log(f"  Attempts: {qa_result['qa']['attempts']}")
    if qa_result["mode_fallback"]:
        log(f"  Mode fallback: product_drop -> value_first")
    if qa_result["anti_ai_applied"]:
        log(f"  Anti-AI cleaning applied")
    if qa_result["revised_from_original"]:
        log(f"  Draft was revised {len(qa_result['revision_history'])} time(s)")

    _report_usage(qa_result["mode"], post_hash, True)

    return {
        "draft": qa_result["final_draft"],
        "mode": qa_result["mode"],
        "fit": fit_result,
        "qa": {
            "composite": qa_result["qa"]["composite"],
            "verdict": qa_result["qa"]["verdict"],
            "dimensions": qa_result["qa"]["dimensions"],
            "attempts": qa_result["qa"]["attempts"],
            "revised": qa_result["revised_from_original"],
            "anti_ai_cleaned": qa_result["anti_ai_applied"],
            "mode_fallback": qa_result["mode_fallback"],
        },
        "corpus": gen_result["corpus_context"],
        "tactical_context": bool(tactical_context and tactical_context.get("has_context")),
        "revision_history": qa_result.get("revision_history", []),
    }


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Comment Forge - Corpus-grounded Reddit comment engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Value-first (no product mention)
  python3 comment_forge.py --post "Best CRM for small teams?"

  # Product drop
  python3 comment_forge.py --post "What tools do you use for email?" \\
    --product "Acme Mail" --product-url "https://acme.com" \\
    --product-desc "Email automation tool for small teams"

  # With existing comments for tone matching
  python3 comment_forge.py --post "How do you handle cold outreach?" \\
    --comments "I use Apollo" "LinkedIn works best imo" "Cold email is dead"

  # From JSON file
  python3 comment_forge.py --file post.json

  # JSON output for piping
  python3 comment_forge.py --post "..." --json

  # Corpus stats
  python3 comment_forge.py --corpus-stats

  # Skip QA (faster, less polished)
  python3 comment_forge.py --post "..." --skip-qa
""")

    parser.add_argument("--post", "-p", help="Post title/question")
    parser.add_argument("--body", "-b", default="", help="Post body text")
    parser.add_argument("--comments", "-c", nargs="*", help="Existing comments (for tone matching)")
    parser.add_argument("--product", help="Product name (triggers product-drop mode)")
    parser.add_argument("--product-url", default="", help="Product URL")
    parser.add_argument("--product-desc", default="", help="Product description")
    parser.add_argument("--category", default="general", help="Corpus category (default: general)")
    parser.add_argument("--mode", choices=["product_drop", "value_first"], help="Force mode (auto-detects if omitted)")
    parser.add_argument("--mention-style", choices=[
        "casual_drop", "detailed_review", "comparison_with_alternative",
        "responding_to_question", "unsolicited_recommendation", "experience_based"],
        help="Mention style for product-drop mode")
    parser.add_argument("--tone", default="casual", help="Tone target (default: casual)")
    parser.add_argument("--file", "-f", help="Load post from JSON file")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--subreddit", default="", help="Subreddit context (for intel narrowing)")
    parser.add_argument("--skip-qa", action="store_true", help="Skip QA pipeline (faster)")
    parser.add_argument("--no-intel", action="store_true", help="Skip real-time intel (Serper + X)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--corpus-stats", action="store_true", help="Show corpus statistics")
    parser.add_argument("--version", action="version", version=f"comment-forge {VERSION}")

    args = parser.parse_args()
    global _VERBOSE
    _VERBOSE = args.verbose

    # Corpus stats mode
    if args.corpus_stats:
        stats = fetch_corpus_stats()
        if not stats:
            print("Could not fetch corpus stats. Check network connection.")
            sys.exit(1)
        print(json.dumps(stats, indent=2))
        sys.exit(0)

    # Load from file
    if args.file:
        with open(args.file) as f:
            data = json.load(f)
        post_title = data.get("title") or data.get("post") or data.get("post_title", "")
        post_body = data.get("body") or data.get("post_body") or data.get("content", "")
        comments = data.get("comments", [])
        # Comments can be strings or dicts
        if comments and isinstance(comments[0], dict):
            pass  # Keep as dicts
        product_name = data.get("product") or data.get("product_name", args.product or "")
        product_url = data.get("product_url", args.product_url)
        product_desc = data.get("product_description") or data.get("product_desc", args.product_desc)
        category = data.get("category", args.category)
        mode = data.get("mode", args.mode)
        subreddit = data.get("subreddit", args.subreddit)
    else:
        if not args.post:
            parser.error("--post is required (or use --file)")
        post_title = args.post
        post_body = args.body
        comments = args.comments or []
        product_name = args.product or ""
        product_url = args.product_url
        product_desc = args.product_desc
        category = args.category
        mode = args.mode
        subreddit = args.subreddit

    # Validate keys
    if not GEMINI_API_KEY and not OPENROUTER_API_KEY:
        print("Error: Set GEMINI_API_KEY or OPENROUTER_API_KEY in .env or environment")
        sys.exit(1)

    # Temporarily disable intel keys if --no-intel
    if args.no_intel:
        global SERPER_API_KEY, TWITTERAPI_KEY
        SERPER_API_KEY = ""
        TWITTERAPI_KEY = ""

    # Run pipeline
    result = run_pipeline(
        post_title, post_body, comments,
        product_name, product_url, product_desc,
        category, mode, args.mention_style, args.tone,
        skip_qa=args.skip_qa, subreddit=subreddit)

    if "error" in result:
        print(f"\nError: {result['error']}")
        sys.exit(1)

    if args.json:
        # Clean output for piping
        output = {
            "draft": result["draft"],
            "mode": result["mode"],
            "qa": result.get("qa"),
            "fit": result.get("fit"),
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  COMMENT FORGE | Mode: {result['mode']}")
        if result.get("fit"):
            f = result["fit"]
            print(f"  Fit: {f['fit_score']}/10 | Intent: {f['thread_intent']}")
        if result.get("tactical_context"):
            print(f"  Real-time intel: injected (Serper + X)")
        if result.get("qa"):
            q = result["qa"]
            print(f"  QA: {q['composite']:.1f}/10 ({q['verdict']}) | Attempts: {q['attempts']}")
            if q.get("anti_ai_cleaned"):
                print(f"  Anti-AI cleaning: applied")
            if q.get("mode_fallback"):
                print(f"  Fallback: product_drop -> value_first")
        print(f"{'='*60}\n")
        print(result["draft"])
        print()


if __name__ == "__main__":
    main()
