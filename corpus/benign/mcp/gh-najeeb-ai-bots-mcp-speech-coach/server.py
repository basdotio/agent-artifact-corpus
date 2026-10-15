"""
mcp-speech-coach — a Model Context Protocol (MCP) server.

The ANALYSIS BRAIN for a voice speaking-coach. Exposes speech-coaching analysis
as MCP tools that any host (a Flet/Streamlit voice app, Claude Desktop, Orcha)
can call. The host handles live mic + spoken feedback (TTS); this server does
the measurement across 15+ dimensions.

Design (see README): single-purpose tools, verb-noun names, descriptions that
state purpose/inputs/outputs/when-to-use, typed params, structured dict output.

Run:
    pip install -r requirements.txt
    python server.py
"""

from mcp.server.fastmcp import FastMCP

from speech_engine import (
    analyze_delivery as _delivery,
    analyze_language as _language,
    analyze_fluency as _fluency,
    analyze_pronunciation as _pronunciation,
    assess_emotional_state as _emotion,
    coach_feedback as _coach,
)

mcp = FastMCP("speech-coach")


@mcp.tool()
def analyze_delivery(transcript: str, duration_s: float = 0.0,
                     wav_path: str = "") -> dict:
    """Analyze speech DELIVERY: words-per-minute, pacing, pauses, voice
    projection, and stress/intonation.

    Use when you need the acoustic/timing side of a speech (how it was said).
    For the wording itself use analyze_language.

    Args:
        transcript: The spoken text (for WPM).
        duration_s: Clip length in seconds (enables WPM/pace). 0 = unknown.
        wav_path: Optional path to the audio file for pitch/energy/pauses.

    Returns:
        dict with wpm, pace, pitch_var_hz, intonation, n_pauses,
        longest_pause_s, projection, engine.
    """
    return _delivery(transcript, duration_s or None, wav_path or None)


@mcp.tool()
def analyze_language(transcript: str, technical_terms: list[str] = []) -> dict:
    """Analyze LANGUAGE: grammar, vocabulary richness, sentence variety, word
    repetition, punctuation (run-ons), and technical-term accuracy.

    Use for the content/wording of the speech. For timing/acoustics use
    analyze_delivery.

    Args:
        transcript: The spoken text to analyze.
        technical_terms: Optional list of domain terms the speaker was expected
            to use correctly (checks coverage).

    Returns:
        dict with vocabulary_richness_ttr, top_repeated_words,
        avg_sentence_length, sentence_variety_spread, run_on_sentences,
        grammar_error_count, grammar_errors, technical_terms.
    """
    return _language(transcript, technical_terms or None)


@mcp.tool()
def analyze_fluency(transcript: str) -> dict:
    """Analyze FLUENCY: flow, filler-word rate, and confidence vs. hedging markers.

    Use to measure how smoothly and assertively the person spoke.

    Args:
        transcript: The spoken text to analyze.

    Returns:
        dict with filler_count, filler_rate_pct, flow,
        confidence_markers_positive, hedging_markers_negative.
    """
    return _fluency(transcript)


@mcp.tool()
def analyze_pronunciation(transcript: str, wav_path: str = "") -> dict:
    """Analyze PRONUNCIATION clarity (proxy) and technical-term handling.

    Use for a quick clarity read. Full phoneme-level scoring needs a dedicated
    pronunciation model; this returns a transcript-confidence proxy.

    Args:
        transcript: The spoken text (STT output).
        wav_path: Optional audio path.

    Returns:
        dict with clarity_proxy and an explanatory note.
    """
    return _pronunciation(transcript, wav_path or None)


@mcp.tool()
def assess_emotional_state(transcript: str, duration_s: float = 0.0,
                           wav_path: str = "") -> dict:
    """Estimate ANXIETY and CONFIDENCE levels during the session.

    Use to gauge how nervous or assured the speaker sounded, derived from pace,
    fillers, hedging, pitch variation, and pauses.

    Args:
        transcript: The spoken text.
        duration_s: Clip length in seconds (improves accuracy). 0 = unknown.
        wav_path: Optional audio path for pitch/pause signals.

    Returns:
        dict with anxiety_level (0-100), confidence_level (0-100), and state.
    """
    d = _delivery(transcript, duration_s or None, wav_path or None)
    f = _fluency(transcript)
    return _emotion(transcript, d, f)


@mcp.tool()
def coach_feedback(transcript: str, duration_s: float = 0.0, wav_path: str = "",
                   technical_terms: list[str] = [],
                   use_llm_api_key: str = "") -> dict:
    """Produce spoken-style COACHING feedback synthesizing all analyses.

    Use this as the final step — it runs delivery, language, fluency,
    pronunciation and emotion, then returns one encouraging coaching script
    suitable for text-to-speech playback by the host app.

    Args:
        transcript: The spoken text.
        duration_s: Clip length in seconds. 0 = unknown.
        wav_path: Optional audio path.
        technical_terms: Optional expected domain terms.
        use_llm_api_key: Optional Anthropic key for richer LLM-written coaching;
            omit to use the free rule-based coach.

    Returns:
        dict with spoken_feedback (text to speak) and the full metric breakdown.
    """
    d = _delivery(transcript, duration_s or None, wav_path or None)
    lang = _language(transcript, technical_terms or None)
    f = _fluency(transcript)
    p = _pronunciation(transcript, wav_path or None)
    e = _emotion(transcript, d, f)
    provider = "Anthropic" if use_llm_api_key else "Rule-based"
    coached = _coach(d, lang, f, p, e, provider=provider, api_key=use_llm_api_key)
    return {
        "spoken_feedback": coached["spoken_feedback"],
        "coach_engine": coached["engine"],
        "metrics": {"delivery": d, "language": lang, "fluency": f,
                    "pronunciation": p, "emotion": e},
    }


if __name__ == "__main__":
    mcp.run()
