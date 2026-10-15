---
name: yt-playlists
description: Groups the user's existing videos into themed homepage playlists ("journeys") for a monthly refresh. Use when the user says "refresh playlists", "homepage playlists", "playlist suggestions", "organize the channel", "monthly playlist refresh", or asks how to arrange the channel homepage.
---

# Playlist Refresh

Group the channel's library into themed "journeys" to feature on the homepage. First read `${CLAUDE_PLUGIN_ROOT}/OPERATING-RULES.md` and follow it (if the channel context is missing, run `yt-setup`).

## Procedure
1. Pull the library with `vidiq_channel_videos` (long-form, enough to cover recent + evergreen). ~5 credits.
2. Group videos into 4–6 **journeys** matched to the audience's real needs and goals from the context file (what they're struggling with or trying to do). Order the videos within each so they form a path (hook / validation → deeper teaching → practical next step). Name each journey in the audience's own words.

## Report structure
For each proposed playlist:
- **Title** (searchable + clear).
- **The journey** it takes the viewer on (one line).
- The **videos** in order, by title.

## Honest scope note
VidIQ cannot create, order, or publish playlists. This skill produces the groupings and order; the actual playlist is built in **YouTube Studio** by a person. Present the output ready to recreate there, and flag it as a 💡 recommendation to implement.
