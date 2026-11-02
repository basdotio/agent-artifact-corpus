---
name: local-tts
description: Ultra-low latency Coqui-TTS local server skill. Optimized for Paul Bettany (Jarvis) and HAL9000 voices.
version: 1.0.0
author: Hugo Espuny (@fakehec)
metadata:
  {
    "openclaw":
      {
        "emoji": "🔊",
        "requires": { "bins": ["curl", "bash"] },
        "tags": ["audio", "tts", "local", "coqui", "stark"]
      }
  }
---

# Local TTS (Coqui-TTS Stark Edition)

High-performance Text-to-Speech skill using a local Coqui-TTS server. Part of the Stark Fleet AI infrastructure.

## Server Configuration
This skill connects to a local server at `http://sphinx.espuny.net:5100` (OpenAI-compatible API).

## Available Voices

- **JARVIS**: Calm, technical voice based on Paul Bettany's clone. (Default)
- **HAL**: Retro-tech voice inspired by HAL9000.

## Usage

```bash
{baseDir}/scripts/say.sh "Hello sir, the analysis is complete." --voice JARVIS --lang en
```

## Performance
- **Latency:** ~250ms for typical agent responses.
- **Hardware:** Optimized for NVIDIA RTX 5090 acceleration.