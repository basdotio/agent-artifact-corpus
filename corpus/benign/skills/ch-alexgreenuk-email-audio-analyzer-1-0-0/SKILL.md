---
name: email-audio-analyzer
description: |
  Check email accounts for audio attachments, transcribe them (Lithuanian support),
  and extract event details (type, date, time, people count, contact info).
  Outputs structured summaries via Telegram or to file.
---

# Email Audio Analyzer Skill ⚡

Automatically checks email accounts for audio attachments, transcribes them using Whisper,
and extracts structured event information using AI analysis.

## Quick Start

**Manual trigger:**
```
Check work email for audio messages
Analyze audio emails from RUBIX
```

**On-demand with options:**
```
Check email audio --account work --output telegram
Check email audio --account gmail --since 24h
```

## Features

- ✅ Check Gmail (personal) or RUBIX work email
- ✅ Download audio attachments automatically
- ✅ Transcribe with Whisper (Lithuanian language support)
- ✅ Extract event details:
  - Event type (concert, party, private, normal day)
  - Date and time
  - Number of people/guests
  - Contact information (name, phone, email)
  - Special requirements/notes
- ✅ Output to Telegram, file, or both
- ✅ Supports multiple audio formats (mp3, wav, m4a, ogg, etc.)

## Configuration

Edit `config.json` to customize:

```json
{
  "defaultAccount": "work",
  "checkInterval": "30m",
  "output": {
    "telegram": true,
    "file": true,
    "memory": true
  },
  "languages": ["lt", "en"],
  "whisper": {
    "model": "base",
    "timeout": 120
  }
}
```

## Commands

### Check Email Now
```bash
cd ~/.openclaw/workspace/skills/email-audio-analyzer
node scripts/check-email.js --account work
```

### Transcribe Audio
```bash
node scripts/transcribe.js --file /path/to/audio.mp3 --language lt
```

### Analyze Transcription
```bash
node scripts/analyze.js --text "transcription text here"
```

## Automation

**Heartbeat (periodic check):**
Add to `HEARTBEAT.md`:
```
- Check RUBIX email for new audio messages
```

**Cron job:**
```bash
# Check every 30 minutes
*/30 * * * * cd ~/.openclaw/workspace/skills/email-audio-analyzer && node scripts/check-email.js --account work
```

## Output Format

Summaries are saved to `output/YYYY-MM-DD-HH-mm-summary.md`:

```markdown
## 📋 Event Inquiry

**Contact:**
- Name: Jonas Petraitis
- Phone: +370 612 34567
- Email: [REDACTED_SECRET]

**Event Details:**
- Type: Birthday party (private)
- Date: May 15, 2026
- Time: 20:00
- Guests: ~30 people
- Notes: Needs sound system, private room

**Source:** Email from [REDACTED_SECRET], received 2026-03-05 11:30
**Audio:** inquiry_20260305_113045.mp3
**Transcription:** [Full Lithuanian text...]
```

## Dependencies

- `himalaya` CLI (work email)
- `gog` CLI (Gmail)
- `whisper` CLI (transcription)
- Node.js 18+

Install dependencies:
```bash
cd ~/.openclaw/workspace/skills/email-audio-analyzer/scripts
npm install
```

## Troubleshooting

**Audio not downloading:**
- Check email CLI is configured (`himalaya configure` or `gog` auth)
- Verify attachment permissions

**Transcription failing:**
- Ensure Whisper is installed: `which whisper`
- Try smaller model: `--model tiny`
- Check audio format is supported

**Lithuanian accuracy poor:**
- Use `--model medium` or `--model large` for better accuracy
- Ensure `--language lt` is specified