---
name: narrated-demo
description: Generate narrated demo videos with synchronized audio using ElevenLabs TTS and Playwright
---

# narrated-demo

Generate narrated demo videos with synchronized audio using ElevenLabs TTS and Playwright browser automation.

## When to Use

Use this skill when you need to:
- Create product demo videos with voice narration
- Record feature walkthroughs with synchronized audio
- Generate marketing videos showing UI interactions
- Create tutorial content with explanations

## Requirements

Before using this skill, ensure:

1. **demos-not-memos** is installed (see Installation below)
2. **ElevenLabs API key** is set: `export ELEVENLABS_API_KEY="your-key"`
3. **ffmpeg** and **ffprobe** are installed:
   ```bash
   # macOS
   brew install ffmpeg

   # Ubuntu/Debian
   sudo apt install ffmpeg
   ```

## Installation

The demos-not-memos library must be installed from GitHub:

```bash
# Clone the repository
git clone https://github.com/markng/demos-not-memos.git
cd demos-not-memos

# Install dependencies
npm install

# (Optional) Install Playwright browsers if not already installed
npx playwright install chromium
```

**Node.js 18.0.0 or higher is required.**

## Quick Start

```bash
cd /path/to/demos-not-memos

# Create a demo script
cat > demos/my-demo.ts << 'EOF'
import { NarratedDemo } from '../src/demo-builder';

async function run() {
  const demo = new NarratedDemo({
    baseUrl: 'http://localhost:8000',
    output: './output/my-demo.mp4'
  });

  await demo.start();
  await demo.narrate("Welcome to the demo.");
  await demo.page.click('#button');
  await demo.narrate("The demo is complete.");
  await demo.finish();
}

run().catch(console.error);
EOF

# Run the demo
npm run dev narrate --script demos/my-demo.ts
```

## DSL API Reference

### NarratedDemo

```typescript
const demo = new NarratedDemo({
  baseUrl: string;          // Required: Base URL for the demo
  output: string;           // Required: Output file path (.mp4)
  viewport?: { width, height };  // Default: 1280x720
  voice?: string;           // Default: 'Rachel'
  model?: string;           // Default: 'eleven_v3'
  sounds?: boolean;         // Default: false - enable UI sounds
});

await demo.start();         // Launch browser and start recording
demo.page                   // Playwright Page for browser actions
await demo.narrate(text);   // Generate TTS and wait for completion
await demo.finish();        // Merge audio/video and save
demo.getElapsedTime();      // Milliseconds since start
```

### Page Interactions

When `sounds: true`, `demo.page` returns a `SoundEnabledPage` wrapper that records click and keystroke sounds automatically.

```typescript
await demo.page.goto('/products');
await demo.page.click('#submit');           // Records click sound
await demo.page.type('#email', 'test@x.com'); // Records keystrokes
await demo.page.fill('#password', 'secret'); // No keystroke sounds
await demo.page.locator('.card').first().click();
await demo.page.waitForSelector('.loaded');
```

### Narration

The `narrate()` method returns a Narration object:

```typescript
const narration = await demo.narrate("Welcome to our product.");
narration.getDuration();  // Duration in milliseconds
```

### Concurrent Narration with Actions

For "watch as I..." scenarios, use concurrent narration:

```typescript
// Method 1: doWhileNarrating convenience method
await demo.doWhileNarrating(
  "Watch as I fill in the form and submit",
  async () => {
    await demo.page.type('#email', 'user@example.com');
    await demo.page.click('#submit');
  }
);

// Method 2: narrateAsync with whileDoing
const narration = await demo.narrateAsync("Watch as I click the button...");
await narration.whileDoing(async () => {
  await demo.page.click('#button');
});
```

### Emotional Expression (Eleven v3 Audio Tags)

Use bracket-enclosed audio tags for expressive narration:

```typescript
await demo.narrate("[excited] Check out this amazing feature!");
await demo.narrate("[whispers] Here's a secret tip.");
await demo.narrate("[curious] What happens if we click here? [laughs] Perfect!");
```

**Supported Tags:**

| Category | Tags |
|----------|------|
| Emotions | `[excited]`, `[curious]`, `[sarcastic]`, `[mischievously]` |
| Voice | `[whispers]`, `[sighs]`, `[laughs]`, `[crying]` |
| Sounds | `[applause]`, `[gunshot]`, `[gulps]` |
| Accents | `[strong French accent]`, `[strong British accent]` |

## Voice Options

Built-in voice mappings:
- Rachel (default) - Clear, professional female voice
- Domi - Professional female voice
- Josh - Friendly male voice
- Antoni - Professional male voice
- Adam - Professional male voice

You can also use any ElevenLabs voice ID directly:

```typescript
const demo = new NarratedDemo({
  voice: 'pNInz6obpgDQGcFmaJgB',  // Voice ID
  // ...
});
```

See [ElevenLabs Voice Library](https://elevenlabs.io/voice-library) for more options.

## Full Example: Product Tour

```typescript
import { NarratedDemo } from '../src/demo-builder';

async function run() {
  const demo = new NarratedDemo({
    baseUrl: 'https://your-product.com',
    voice: 'Rachel',
    model: 'eleven_v3',
    sounds: true,
    output: './output/product-tour.mp4'
  });

  await demo.start();

  // Homepage
  await demo.narrate("[excited] Welcome to our product!");

  // Navigate to features
  await demo.page.click('a[href="/features"]');
  await demo.page.waitForLoadState('networkidle');
  await demo.narrate("[curious] Let me show you what makes us special...");

  // Scroll through features
  await demo.page.locator('#key-features').scrollIntoViewIfNeeded();
  await demo.narrate("These features save our customers hours every week.");

  // Call to action
  await demo.page.click('.cta-button');
  await demo.narrate("[whispers] Getting started takes just a minute.");

  // Form demo
  await demo.page.type('#email', 'demo@example.com');
  await demo.narrate("[excited] Thanks for watching!");

  await demo.finish();
}

run().catch(console.error);
```

## Troubleshooting

### "Demo not started" error
Ensure you call `await demo.start()` before accessing `demo.page` or calling `demo.narrate()`.

### ffmpeg not found
Install ffmpeg and ensure it's in your PATH:
```bash
which ffmpeg  # Should output a path
```

### ElevenLabs API errors
- Verify your API key is set: `echo $ELEVENLABS_API_KEY`
- Check your ElevenLabs account has available credits
- Ensure you're using a valid voice name or ID

### Audio/video sync issues
The DSL uses real-time timing. If sync issues occur:
- Ensure your system clock is stable
- Try shorter narration segments
- Check that no background processes are causing timing delays

## Full Documentation

See the [demos-not-memos README](https://github.com/markng/demos-not-memos#readme) for complete API reference and examples.
