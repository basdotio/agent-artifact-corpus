"""
speech_engine.py — the analysis engine behind the mcp-speech-coach tools.

Covers 15+ speech-coaching dimensions, grouped into coherent analysis functions.
Kept separate from server.py so the MCP tool definitions stay clean and the
engine is independently testable. Degrades gracefully when optional libraries
(librosa, language_tool_python) are unavailable.

Dimensions covered:
  Delivery:   words-per-minute, pacing, pauses, voice projection, stress/intonation
  Language:   grammar, vocabulary richness, sentence variety, word repetition,
              punctuation awareness, technical-term accuracy
  Fluency:    fluency/flow, filler words, confidence markers
  Pronunciation: clarity (proxy), technical-term handling
  Emotional:  anxiety + confidence estimates
"""

import re
from collections import Counter

FILLERS = ["um", "uh", "like", "you know", "so", "actually", "basically",
           "literally", "i mean", "right", "okay", "well"]

CONFIDENCE_MARKERS_POS = ["definitely", "certainly", "clearly", "absolutely",
                          "confident", "will", "proven", "demonstrated"]
CONFIDENCE_MARKERS_NEG = ["maybe", "perhaps", "i think", "i guess", "sort of",
                          "kind of", "possibly", "not sure", "hopefully"]


# ---------- helpers ----------
def _words(text):
    return re.findall(r"\b[\w']+\b", text.lower())

def _sentences(text):
    return [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]


# ---------- 1. DELIVERY ----------
def analyze_delivery(transcript: str, duration_s: float | None = None,
                     wav_path: str | None = None) -> dict:
    """WPM, pacing, pauses, projection, stress/intonation."""
    words = _words(transcript)
    wpm = round(len(words) / (duration_s / 60), 1) if duration_s else None

    pace_label = "unknown"
    if wpm is not None:
        if wpm < 110: pace_label = "too slow"
        elif wpm <= 160: pace_label = "ideal"
        elif wpm <= 190: pace_label = "slightly fast"
        else: pace_label = "too fast"

    acoustic = {"pitch_var_hz": None, "energy_var": None, "n_pauses": None,
                "longest_pause_s": None, "projection": None, "engine": "text-only"}
    if wav_path:
        try:
            import librosa, numpy as np
            y, sr = librosa.load(wav_path, sr=None, mono=True)
            rms = librosa.feature.rms(y=y)[0]
            acoustic["energy_var"] = round(float(np.std(rms)), 4)
            acoustic["projection"] = ("strong" if float(np.mean(rms)) > 0.04
                                      else "soft/low")
            try:
                f0, _, _ = librosa.pyin(y, fmin=65.0, fmax=2093.0, sr=sr)
                f0v = f0[~np.isnan(f0)] if f0 is not None else np.array([])
                pv = float(np.std(f0v)) if f0v.size else 0.0
                acoustic["pitch_var_hz"] = round(pv, 1)
                acoustic["intonation"] = ("dynamic" if pv > 25 else
                                          "monotone" if pv < 10 else "moderate")
            except Exception:
                pass
            iv = librosa.effects.split(y, top_db=30)
            acoustic["n_pauses"] = max(0, len(iv) - 1)
            lp = 0.0
            for i in range(1, len(iv)):
                lp = max(lp, (iv[i][0] - iv[i-1][1]) / sr)
            acoustic["longest_pause_s"] = round(lp, 2)
            acoustic["engine"] = "librosa"
        except Exception as e:
            acoustic["engine"] = f"text-only ({e})"

    return {"wpm": wpm, "pace": pace_label, **acoustic}


# ---------- 2. LANGUAGE ----------
def analyze_language(transcript: str, technical_terms: list | None = None) -> dict:
    """Grammar, vocabulary richness, sentence variety, repetition, punctuation,
    technical-term accuracy."""
    words = _words(transcript)
    sents = _sentences(transcript)
    wc = len(words)

    # vocabulary richness (type-token ratio)
    unique = len(set(words))
    ttr = round(unique / wc, 2) if wc else 0.0

    # word repetition (most common non-trivial word)
    stop = {"the", "a", "an", "and", "to", "of", "in", "is", "it", "i", "you",
            "we", "that", "this", "for", "on", "with", "as", "are", "be"}
    content = [w for w in words if w not in stop and len(w) > 2]
    rep = Counter(content).most_common(3)

    # sentence variety (stdev of sentence lengths)
    lens = [len(_words(s)) for s in sents] or [0]
    avg_len = round(sum(lens) / len(lens), 1)
    variety = round((max(lens) - min(lens)), 0) if len(lens) > 1 else 0

    # punctuation awareness (very long run-on sentences)
    run_ons = sum(1 for L in lens if L > 40)

    # grammar via language_tool
    grammar = _grammar(transcript)

    # technical-term accuracy (did they use the expected terms?)
    tech = {}
    if technical_terms:
        low = transcript.lower()
        used = [t for t in technical_terms if t.lower() in low]
        tech = {"expected": technical_terms, "used": used,
                "coverage_pct": round(100 * len(used) / len(technical_terms), 0)}

    return {
        "word_count": wc,
        "vocabulary_richness_ttr": ttr,
        "top_repeated_words": [{"word": w, "count": c} for w, c in rep],
        "avg_sentence_length": avg_len,
        "sentence_variety_spread": variety,
        "run_on_sentences": run_ons,
        "grammar_error_count": grammar["error_count"],
        "grammar_errors": grammar["errors"][:10],
        "grammar_engine": grammar["engine"],
        "technical_terms": tech,
    }


def _grammar(text):
    try:
        import language_tool_python
        tool = language_tool_python.LanguageTool("en-US")
        matches = tool.check(text)
        errs = [{"message": m.message,
                 "suggestion": ", ".join(m.replacements[:2]) if m.replacements else "",
                 "context": m.context} for m in matches[:20]]
        try: tool.close()
        except Exception: pass
        return {"error_count": len(matches), "errors": errs, "engine": "LanguageTool"}
    except Exception:
        return {"error_count": 0, "errors": [], "engine": "unavailable"}


# ---------- 3. FLUENCY ----------
def analyze_fluency(transcript: str) -> dict:
    """Fluency/flow, filler words, confidence markers."""
    words = _words(transcript)
    wc = len(words) or 1
    low = " " + transcript.lower() + " "
    filler_count = sum(low.count(" " + f + " ") for f in FILLERS)
    filler_rate = round(100 * filler_count / wc, 1)

    pos = sum(low.count(" " + m + " ") for m in CONFIDENCE_MARKERS_POS)
    neg = sum(low.count(" " + m + " ") for m in CONFIDENCE_MARKERS_NEG)

    flow = ("choppy" if filler_rate > 6 else
            "smooth" if filler_rate < 2 else "moderate")
    return {
        "filler_count": filler_count,
        "filler_rate_pct": filler_rate,
        "flow": flow,
        "confidence_markers_positive": pos,
        "hedging_markers_negative": neg,
    }


# ---------- 4. PRONUNCIATION (proxy) ----------
def analyze_pronunciation(transcript: str, wav_path: str | None = None) -> dict:
    """Pronunciation clarity proxy + technical-term handling.
    (A full pronunciation score needs a phoneme model like faster-whisper +
    forced alignment; this returns a transcript-confidence-based proxy.)"""
    clarity = "unknown"
    note = ("Full phoneme-level scoring requires the faster-whisper pronunciation "
            "module; this is a transcript-availability proxy.")
    if transcript and not transcript.startswith("(no transcript"):
        # crude proxy: did STT produce coherent words?
        words = _words(transcript)
        real = sum(1 for w in words if len(w) > 1)
        clarity = "clear" if words and real / len(words) > 0.9 else "unclear"
    return {"clarity_proxy": clarity, "note": note}


# ---------- 5. EMOTIONAL STATE ----------
def assess_emotional_state(transcript: str, delivery: dict, fluency: dict) -> dict:
    """Estimate anxiety + confidence from pace, fillers, hedging, pitch."""
    anxiety = 30
    confidence = 60

    wpm = delivery.get("wpm")
    if wpm and wpm > 185:       anxiety += 20; confidence -= 10   # rushing
    if fluency["filler_rate_pct"] > 6: anxiety += 15; confidence -= 10
    if fluency["hedging_markers_negative"] > fluency["confidence_markers_positive"]:
        anxiety += 10; confidence -= 15
    else:
        confidence += 10
    pv = delivery.get("pitch_var_hz")
    if pv is not None and pv < 10:  confidence -= 5   # monotone can read as nervous
    lp = delivery.get("longest_pause_s")
    if lp and lp > 4:           anxiety += 10

    anxiety = max(0, min(100, anxiety))
    confidence = max(0, min(100, confidence))
    band = ("calm & assured" if confidence >= 70 and anxiety <= 35 else
            "some nerves" if anxiety <= 60 else "high anxiety")
    return {"anxiety_level": anxiety, "confidence_level": confidence,
            "state": band}


# ---------- 6. COACH SYNTHESIS ----------
def coach_feedback(delivery, language, fluency, pronunciation, emotion,
                   provider="Rule-based", api_key="") -> dict:
    """Synthesize all analyses into spoken-style coaching text (for TTS)."""
    if provider.startswith("Anthropic") and api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            prompt = (
                "You are a warm, encouraging voice speaking-coach. Based on these "
                "metrics, give short spoken-style coaching (120 words max, 2nd person, "
                "plain text for text-to-speech). Cover pace, fillers, tone, and "
                "confidence, ending with one specific action.\n\n"
                f"delivery={delivery}\nlanguage={language}\nfluency={fluency}\n"
                f"pronunciation={pronunciation}\nemotion={emotion}"
            )
            msg = client.messages.create(model="claude-sonnet-4-5", max_tokens=350,
                                         messages=[{"role": "user", "content": prompt}])
            return {"spoken_feedback": msg.content[0].text, "engine": "Claude"}
        except Exception:
            pass

    tips = []
    if delivery.get("pace") == "too fast":
        tips.append("You're speaking quite fast — try slowing down and pausing after key points.")
    elif delivery.get("pace") == "too slow":
        tips.append("Pick up your pace a little to keep your listener engaged.")
    elif delivery.get("pace") == "ideal":
        tips.append("Your pace is right in the sweet spot — nice work.")
    if fluency["filler_rate_pct"] > 4:
        tips.append(f"You used {fluency['filler_count']} filler words. Try a silent pause instead of 'um' or 'like'.")
    if delivery.get("intonation") == "monotone":
        tips.append("Add more vocal variety — let your pitch rise and fall to emphasize important words.")
    if language["grammar_error_count"] > 0:
        tips.append(f"I spotted {language['grammar_error_count']} grammar point(s) to tighten up.")
    tips.append(f"Overall you sound {emotion['state']}. "
                f"Confidence is around {emotion['confidence_level']} out of 100.")
    spoken = " ".join(tips)
    return {"spoken_feedback": spoken, "engine": "rule-based"}
