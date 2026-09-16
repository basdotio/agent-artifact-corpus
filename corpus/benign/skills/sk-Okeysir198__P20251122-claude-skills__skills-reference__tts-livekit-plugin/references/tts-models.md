# HuggingFace TTS Models Comparison

## Overview

This guide compares the top self-hosted TTS models available on HuggingFace for LiveKit voice agent integration. All models support streaming for low-latency voice interactions.

---

## Recommended Models for 2025

### 1. Parler-TTS (Recommended for Production)

**Model:** `parler-tts/parler-tts-mini-v1` or `parler-tts/parler-tts-large-v1`

**Key Features:**
- **Streaming support**: Native streaming capabilities with low latency
- **Voice control**: Text-based voice description (no reference audio needed)
- **Quality**: Natural-sounding speech with good prosody
- **Speed**: Fast inference (~2-3x real-time on CPU)
- **Multilingual**: Primarily English, but supports basic multilingual

**Specifications:**
- Sample rate: 24kHz
- Model size: ~880M parameters (mini), ~2.4B parameters (large)
- Latency: <200ms streaming latency achievable
- Device: CPU-friendly, GPU-accelerated

**Voice Description Examples:**
```python
"A friendly, conversational voice with moderate pace."
"A professional, clear voice speaking slowly."
"An energetic, upbeat voice with fast delivery."
```

**Pros:**
- Text-based voice control (no audio samples needed)
- Good quality/speed tradeoff
- Built-in streaming support
- Easy deployment

**Cons:**
- Limited to pre-trained voice characteristics
- Primarily English-focused

**Best for:** Production voice agents requiring consistent quality and low latency

---

### 2. F5-TTS

**Model:** `F5-TTS` (via f5-tts package)

**Key Features:**
- **Flow matching**: Advanced generative model
- **Quality**: Excellent natural speech quality
- **Voice cloning**: Few-shot voice cloning from reference audio
- **Training**: Can be fine-tuned on custom datasets

**Specifications:**
- Sample rate: 24kHz
- Model size: Varies by configuration
- Latency: ~150-300ms
- Device: GPU recommended

**Pros:**
- State-of-the-art quality
- Voice cloning capabilities
- Highly customizable
- Active development

**Cons:**
- Requires reference audio for voice cloning
- More complex setup
- Higher compute requirements

**Best for:** High-quality applications where voice customization is important

---

### 3. XTTS-v2 (Coqui TTS)

**Model:** `coqui/XTTS-v2`

**Key Features:**
- **Multilingual**: Supports 17+ languages
- **Voice cloning**: Clone voices from 6+ seconds of audio
- **Streaming**: <150ms latency with streaming mode
- **Quality**: Very natural, expressive speech

**Specifications:**
- Sample rate: 24kHz
- Model size: ~1.2B parameters
- Latency: <150ms streaming (GPU)
- Device: GPU recommended for real-time

**Pros:**
- Excellent multilingual support
- Fast voice cloning
- Production-ready
- Well-documented

**Cons:**
- GPU required for real-time
- Larger model size
- Requires reference audio

**Best for:** Multilingual applications or when voice cloning is essential

---

## Performance Comparison

| Model | Quality | Speed (CPU) | Speed (GPU) | Streaming | Voice Control | Multilingual |
|-------|---------|-------------|-------------|-----------|---------------|--------------|
| Parler-TTS Mini | ★★★★☆ | ★★★★★ | ★★★★★ | ✅ Native | ✅ Text-based | Limited |
| Parler-TTS Large | ★★★★★ | ★★★☆☆ | ★★★★★ | ✅ Native | ✅ Text-based | Limited |
| F5-TTS | ★★★★★ | ★★☆☆☆ | ★★★★☆ | ✅ | ✅ Audio-based | Good |
| XTTS-v2 | ★★★★★ | ★☆☆☆☆ | ★★★★★ | ✅ | ✅ Audio-based | Excellent |

---

## Streaming Implementation Patterns

### Sentence-Level Streaming (Recommended)

Process text sentence-by-sentence for optimal latency:

```python
def split_into_sentences(text: str) -> list[str]:
    """Split text on sentence boundaries."""
    import re
    sentences = re.split(r'([.!?]+\s+)', text)
    result = []
    for i in range(0, len(sentences) - 1, 2):
        result.append(sentences[i] + sentences[i + 1])
    if len(sentences) % 2 == 1:
        result.append(sentences[-1])
    return result
```

**Benefits:**
- Lower perceived latency
- Natural speech rhythm
- Better error recovery

### Chunk-Level Streaming

Process fixed-duration chunks:

```python
CHUNK_SIZE = 50  # characters
chunks = [text[i:i+CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
```

**Benefits:**
- Predictable latency
- Simpler implementation

**Drawbacks:**
- May split mid-word
- Less natural prosody

---

## Model Selection Guide

### For Production Voice Agents

**Recommended:** Parler-TTS Mini
- Fast enough for real-time on modest hardware
- Good quality for conversational AI
- No reference audio needed
- Consistent performance

### For High-Quality Applications

**Recommended:** F5-TTS or Parler-TTS Large
- Superior natural quality
- Better prosody and emotion
- Worth the extra compute

### For Multilingual Support

**Recommended:** XTTS-v2
- Best multilingual coverage
- Consistent quality across languages
- Voice cloning across languages

### For Cost Optimization

**Recommended:** Parler-TTS Mini on CPU
- Runs efficiently on CPU
- Lower infrastructure costs
- Good enough quality for most use cases

---

## Deployment Considerations

### Hardware Requirements

**CPU-Only (Parler-TTS Mini):**
- 4+ cores recommended
- 8GB+ RAM
- ~2-3x real-time synthesis

**GPU-Accelerated:**
- NVIDIA GPU with 8GB+ VRAM
- CUDA 11.8+ or 12.x
- ~10-20x real-time synthesis

### Optimization Tips

1. **Model Loading**: Load model once at startup, not per request
2. **Batch Processing**: Process multiple sentences in parallel when possible
3. **Caching**: Cache common phrases/responses
4. **Streaming**: Use WebSocket for bi-directional streaming
5. **Async Processing**: Use asyncio for non-blocking synthesis

### Scaling Strategies

1. **Horizontal Scaling**: Multiple TTS API instances behind load balancer
2. **GPU Pooling**: Shared GPU resources across multiple workers
3. **Model Serving**: Use model serving frameworks (TorchServe, Triton)

---

## Code Examples

### Parler-TTS

```python
from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer

model = ParlerTTSForConditionalGeneration.from_pretrained(
    "parler-tts/parler-tts-mini-v1"
).to("cuda")
tokenizer = AutoTokenizer.from_pretrained("parler-tts/parler-tts-mini-v1")

# Generate with voice description
input_ids = tokenizer(
    "A friendly voice with moderate pace.",
    return_tensors="pt"
).input_ids.to("cuda")

prompt_ids = tokenizer(
    "Hello! How can I help you today?",
    return_tensors="pt"
).input_ids.to("cuda")

audio = model.generate(
    input_ids=input_ids,
    prompt_input_ids=prompt_ids,
    do_sample=True
)
```

### XTTS-v2

```python
from TTS.api import TTS

tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cuda")

# Generate with voice cloning
audio = tts.tts(
    text="Hello! How can I help you today?",
    speaker_wav="reference_audio.wav",  # 6+ seconds of reference
    language="en"
)
```

---

## Resources

- **Parler-TTS**: https://github.com/huggingface/parler-tts
- **F5-TTS**: https://github.com/SWivid/F5-TTS
- **XTTS-v2**: https://huggingface.co/coqui/XTTS-v2
- **HuggingFace TTS Task**: https://huggingface.co/tasks/text-to-speech
- **Modal Blog on TTS**: https://modal.com/blog/open-source-tts
