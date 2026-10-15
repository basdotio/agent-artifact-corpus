---
name: doomscroll
description: Study a batch of saved short-form videos (Instagram reels, TikToks, YouTube Shorts) and turn what they teach into a few reusable skills. Use when someone shares video links or a saved collection and wants Claude to learn from them.
---

# Doomscroll

The person has a pile of saved videos they never went back to. Your job is to go through them the way they would if they had the time, pull out what's actually worth doing more than once, and save it as skills they can use.

## 1. Before you start

Ask only what you need, in one message:

- **What job the skills are for.** "Editing my Instagram reels" or "writing cold emails for my agency." This matters more than anything else. Skills built for a specific job are useful; skills built for "content" are generic.
- **Where the videos are.** A list of links, or the name of a saved collection.
- **Anything about their style you should respect.** Their existing preferences win over whatever the videos say.

If they only gave you links and it's obvious what the job is, skip the questions and start.

Tell them up front that going through video uses a good amount of usage, and suggest starting with 5 to 15 videos on one topic.

## 2. Get each video

Try these in order and use the first one that works:

1. **Through their browser (Claude in Chrome).** Most platforms block Claude's own servers from loading videos, so use the person's logged-in browser. Open each link, read the caption, and grab the lowest-quality video and audio the page loads. If Chrome blocks multiple downloads from one page, bundle the files into one download.
2. **From their collection directly.** If they named a collection instead of pasting links, open it in their browser and work through it. Skip anything that isn't about the job (memes, ads, off-topic posts) and tell them what you skipped.
3. **Text only.** If you can't get the video, ask them to paste the caption and a transcript. Say that you'll miss anything that's only shown on screen.

Keep the files only as long as you need them. Delete anything you downloaded to their computer when you're done, and tell them you did.

## 3. Study each video

For every video, write down:

- **Transcript.** Transcribe the audio with whatever speech-to-text you have.
- **Frames.** Pull frames every half second for the first 3 seconds, then evenly through the rest. Look at the on-screen text, cuts, graphics, and layout. The first 3 seconds usually carry the hook, so look closely there.
- **Caption and CTA.** What it asks the viewer to do.
- **The actual teaching.** What would someone do differently after watching it? Write it as steps or rules, not a summary.

Skip videos that turn out to have nothing concrete in them. Say which ones and why.

## 4. Turn it into skills

- **Group by job, not by video.** Aim for 2 to 4 skills that cover the work start to finish (for content: write it, check it, edit it). Don't make one skill per video.
- **Keep what's specific.** Numbers, steps, exact phrasing, timing, tools. Cut motivational filler and anything that would be true of any video on the topic.
- **Respect their style.** Where a video's advice clashes with how the person already works, keep their way and note the clash, with how the skill handles it.
- **Credit the source.** In each skill, list which videos each technique came from, with links.
- **Write it so it can be used cold.** A new chat with no context should be able to follow the skill.

Each skill is a folder with a `SKILL.md`. Start the file with frontmatter:

```
---
name: short-kebab-case-name
description: One sentence on what it does and when to use it.
---
```

Then the instructions: when to use it, the steps, the rules, what the output looks like, and the sources.

## 5. Hand it back

- Offer the skills for them to review and save. In the Claude desktop app, propose them so they get a save card. Otherwise give them the files and tell them to upload each one under Customize > Skills (code execution needs to be on in Settings > Capabilities).
- Write a short report: each skill, what it's for, one example prompt that triggers it, and a table of every video with what it taught and which skill it went into.
- Suggest running it again when they've saved more videos, and offer to update the existing skills instead of making new ones.
