# Email Audio Analyzer - Quick Start ⚡

## Test It Now

**Check work email for audio messages:**
```bash
cd ~/.openclaw/workspace/skills/email-audio-analyzer
node index.js --account=work
```

**Check Gmail:**
```bash
node index.js --account=gmail
```

**Just transcribe a specific audio file:**
```bash
node scripts/transcribe.js --file /path/to/audio.mp3 --language lt
```

**Analyze existing transcription:**
```bash
node scripts/analyze.js --file /path/to/transcription.txt --output
```

## Add to Heartbeat (Auto-check)

Edit `~/.openclaw/workspace/HEARTBEAT.md`:
```markdown
- Check RUBIX email for new audio messages
```

## Output Location

All summaries saved to:
```
~/.openclaw/workspace/skills/email-audio-analyzer/output/
```

## Features You Can Add Later

- [ ] Speaker diarization (separate voices)
- [ ] Calendar integration (auto-create events)
- [ ] Multi-language support
- [ ] Batch processing
- [ ] Webhook triggers (process on email arrival)
- [ ] SMS notifications
- [ ] Voice reply to sender
- [ ] Event booking confirmation workflow

## Troubleshooting

**Himalaya not configured:**
```bash
himalaya configure
```

**Whisper not installed:**
```bash
# Check if whisper exists
which whisper

# Install if needed (depends on your setup)
pip install openai-whisper
```

**Permission errors:**
```bash
chmod +x scripts/*.js
```

---

_Skill created: 2026-03-05_
