# timeline-video

An agent skill (Claude Code, and any agent that reads `SKILL.md` skills) for writing and rendering
**timeline-scripted AI videos**: one generation up to 30 seconds, scripted second by second, so a long video model
holds a single take, a locked character and a planned reveal. It's the format behind viral single-take ads such as
the endless zoom-out, where a voice note asks for something and each pull-back shows how impossible it is from here.

The skill gives the agent the format and the craft (`SKILL.md`), a blank script and a complete example, and one
Python 3.8+ standard-library script that:

- **checks** a script: all six blocks present, the timeline's windows run from 0 to the duration with no gaps, voice
  lines fit their windows, the character is locked, the negatives forbid text and logos;
- **prices** it from OpenRouter's live model list before anything is spent;
- **renders** it on OpenRouter's async video API (ByteDance Seedance 2.5 by default; any OpenRouter video model):
  submit, poll, download, plus a JSON sidecar with the prompt, parameters, job id and the real charge;
- **lays out a contact sheet** of one frame per beat, to check continuity before you use the take (needs `ffmpeg`).

## Install

```bash
git clone https://github.com/askdestava/claude-skills
cp -R claude-skills/skills/timeline-video ~/.claude/skills/
```

(Or link it, to pick up changes with `git pull`: `ln -s "$PWD/claude-skills/skills/timeline-video" ~/.claude/skills/timeline-video`.)

You need an [OpenRouter](https://openrouter.ai/keys) key in `OPENROUTER_API_KEY` or a file passed with `--key-file`.
Then ask in plain words: *"make a 30-second single-take video like this one"*, *"script a zoom-out reveal of a
surfer who gets a work email"*, *"render this Seedance prompt"*.

## Use it without an agent

```bash
python3 scripts/timeline_video.py check  examples/the-sandbar.md
python3 scripts/timeline_video.py render examples/the-sandbar.md -o out/ --dry-run     # price only
python3 scripts/timeline_video.py render examples/the-sandbar.md -o out/ --key-file ~/openrouter.key
python3 scripts/timeline_video.py sheet  out/the-sandbar.mp4 examples/the-sandbar.md
python3 scripts/timeline_video.py models --model bytedance/seedance-2.5
```

A 30-second Seedance 2.5 render at 720p costs about $7 and takes about five minutes. Seedance is billed per video
token and the conversion isn't published, so the price shown before a render is an estimate (on a real 30-second job:
$6.93 estimated, $6.94 charged); the sidecar records what was charged.

## Credit

The six-block format follows the Seedance prompt [@iamneubert](https://x.com/iamneubert/status/2099199895039336459)
shared with the breakdown of a viral single-take ad. This skill contains none of that prompt or video.

## Licence

MIT. See [LICENSE](LICENSE).
