# 🔌🎙️ mcp-speech-coach — an MCP Server for Voice Coaching

> A **Model Context Protocol (MCP)** server — the analysis *brain* of a voice speaking-coach. Exposes 15+ speech-coaching dimensions as callable tools that any host (a voice app, Claude Desktop, Orcha) can use.

**Built by:** [Mohammed Abdul Najeeb](https://github.com/Najeeb-AI-bots)

> 💡 Pairs with my [VoiceCoach Lite](https://github.com/Najeeb-AI-bots/voicecoach-lite) app. The **app** handles the live microphone and the spoken feedback (text-to-speech); this **MCP server** is the measurement engine it calls. That separation is the whole point of MCP: the host runs the experience, the server supplies the capabilities.

---

## Why MCP (and what it is / isn't)

MCP is "USB-C for AI" — a standard protocol so any AI host can call any server's tools. An MCP server **cannot** open a microphone or talk back on its own; it exposes **tools** and the host decides when to call them. So the architecture is:

```
Voice Coach App (host)  ── live mic, TTS spoken feedback, conversation
        │ calls tools over MCP
        ▼
mcp-speech-coach (this)  ── analysis across 15+ dimensions
```

## The tools (15+ dimensions, grouped into 6 coherent tools)

| Tool | Dimensions covered |
|------|--------------------|
| `analyze_delivery` | words-per-minute · pacing · pauses · voice projection · stress/intonation |
| `analyze_language` | grammar · vocabulary richness · sentence variety · word repetition · punctuation awareness · technical-term accuracy |
| `analyze_fluency` | fluency/flow · filler words · confidence markers |
| `analyze_pronunciation` | pronunciation clarity (proxy) · technical-term handling |
| `assess_emotional_state` | anxiety level · confidence level (during the session) |
| `coach_feedback` | synthesizes everything into **spoken-style feedback** the host app can read aloud via TTS |

> Design note: these are grouped by *job*, not split into 15 micro-tools (that would be the "too many near-identical tools" anti-pattern) and not merged into one mega-tool (that would be the vague-mode anti-pattern). Each tool is one coherent responsibility with a typed schema and structured dict output.

## How the "voice AI tutor" experience is delivered

1. The app records the user (live mic)
2. The app transcribes + measures duration
3. The app calls `coach_feedback(transcript, duration_s, wav_path)` on this server
4. The server returns `spoken_feedback` (a short coaching script) + full metrics
5. **The app speaks `spoken_feedback` aloud via TTS** — that's the "voice tutor" moment
6. For real-time conversation, the app loops steps 1-5

## Run / register

```bash
pip install -r requirements.txt
python server.py            # stdio transport
```

Register with Claude Desktop (see `claude_desktop_config.example.json`), then ask:
*"Analyze the delivery of this transcript (duration 30s): ..."* → it calls `analyze_delivery`.

## Skills demonstrated

MCP server design · multi-tool architecture · tool granularity (right-sizing) · structured output · audio + NLP analysis · separation of concerns (analysis vs. experience)

## License

MIT.
