---
name: friday-tunes
description: Build a playlist for a music theme (the weekly Friday 15:00 theme at work, or any "songs that..." / "X in the title" prompt) from the user's own listening history. Use when the user gives a music theme, asks for songs from their library that match something, or asks to search their Spotify or Last.fm history.
---

# friday-tunes

`ft` searches a local SQLite index of the user's music:
- Liked Songs, own playlists, and Spotify top and recent tracks.
- Last.fm scrobbles since 2008.
- The catalogs of followed and top artists: Last.fm top tracks, plus Spotify discographies that fill in over time.
- Last.fm tags, lyrics, Genius notes (a song's About text and listener annotations) and track embeddings, where a sync has fetched them.
- Summaries: a short account of what each song is about and the playlist themes it fits, written by a local model for songs with lyrics or Genius notes. A row shows it as `about`.
- Artist embeddings built from each artist's Last.fm tags.

Pick from this index instead of paging through Spotify with MCP tools. The Spotify app is rate limited hard, and a search here takes milliseconds.

## Commands

Read the default text output: a short block per track. It starts with the index's own track ID, which `ft playlist create` takes, then what the song is about and why it matched. It is compact enough to read whole. Pass `--json` only when you need a field the text leaves out, such as `spotify_url`. Tracks without a Spotify ID are scrobble or catalog tracks that `ft playlist create` looks up on Spotify.

- `ft theme --vibe "<mood>" --sound "<genres and sound>" --word <w> --word <w> --tag <t> --exclude-tag <t> --source library --json`: the main tool for open themes. It fuses these searches into one ranked list:
  - `vibe`: the mood against track embeddings.
  - `about-vibe`: the vibe against summary embeddings. This finds songs by what they are about, even when no theme word is in the title or lyrics.
  - `artist-vibe`: the sound against artist embeddings, then the tracks of each matching artist that sit closest to the vibe. This finds the artists that fit a theme, so you do not have to guess them. It runs only when you pass `--sound`.
  - One search per word across title, lyrics, Genius notes and summaries. The fields count as one signal, so a common word cannot outvote the vibe.
  - One search per tag.
  Each row lists the searches that found it in `signals` (`via` in text), and `score` rises when several agree. A small boost for plays and likes tips close calls toward songs the user knows. Covers and other versions of the same song are listed under the best ranked one as `versions` (`also` in text), so each song takes one place. Words accept a trailing `*`. One `ft theme` call with many `--word`s replaces a loop of `ft search title` calls.
- `ft search title <words>`: word match in the title. Add `--substring` to match inside words ("love" also finds "lovely").
- `ft search artist <words>`: word match in any artist name on the track.
- `ft search album <words>`, `ft search lyrics <words>`, `ft search tag <words>`: the same match on album, lyrics or Last.fm tags (track and artist tags).
- `ft search meaning <words>`: match in the Genius About text and annotations. Use it for themes about what a song means or where it comes from ("songs about a real event", "songs written for someone"). The `match` field shows the matching passage.
- `ft search about <words>`: word match in the summaries and their themes. Summaries are in English, whatever the language of the song.
- `ft search about-vibe <description>`: semantic search over the summaries. Describe the subject ("songs about war photographers", "protest songs against the Vietnam war").
- `ft search year 1996` or `ft search year 1990-1999`: release year. Scrobble-only tracks often have no year.
- `ft search vibe <description>`: semantic search over each track's title, artist, tags, lyrics and Genius notes. Describe the mood in a few words; Norwegian works too.
- `ft search artist-vibe <sound>`: semantic search over artists, returning up to 4 of each matching artist's most played tracks. Describe genres, instruments and regions ("indie folk, acoustic, nordic folk"). Moods and seasons ("autumn", "cozy") match poorly, because tags rarely name them.
- Filters for every mode:
  - `--source liked|library|scrobbled|catalog|any`: "library" means liked, own playlists and Spotify top tracks. "catalog" means songs by followed and top artists that the user may not have heard.
  - `--min-plays N`: at least N Last.fm scrobbles.
  - `--limit N`: default 50.
  - `--exclude-tag <t>`: leave out tracks whose own or artist tags contain this phrase. Repeat for several. "metal" also drops "heavy metal" and "power metal". It is blunt: one stray tag drops an artist entirely (Guns N' Roses carries a metal tag), so use it only for genres that would clearly break the mood, and check what it removed.
- A trailing `*` on a word is a prefix match. Quote it so the shell does not expand it: `ft search title 'witch*'`.
- `ft stats`: shows what is indexed and how old the sync is. Run it first if results look thin.
- `ft playlist create --name "<name>" --description "<text>" <id> <id> ...`: resolves Spotify IDs for scrobble-only tracks and creates a private playlist. It prints the link and any tracks that are not on Spotify.

A search runs a quick sync first when the index is more than 12 hours old. Its progress goes to stderr. If Spotify or Last.fm is not authorized, the search warns and uses the existing index.

## Workflow

1. Classify the theme. Most themes combine several of these:
   - literal title word ("songs with a color in the title")
   - artist name word ("artists named after animals")
   - lyric subject ("songs about rain")
   - era or year ("songs from the year you were born")
   - genre or mood that tags describe ("dreamy", "witch house", "christmas")
   - open vibe that needs judgment ("songs that evoke magic")
2. Expand the theme before you search. Themes are often puns or references, so write out what they could point to: people, places, events, band names and wordplay. "(Nobel) Peace (Prize)" points to Oslo, Dylan, Mandela, Gorbachev, a band called War, songs about peace and war, and the Norwegian "fred". Each becomes a `--word`, an artist search or part of the `--vibe`.
3. Search:
   1. For literal themes, expand the word list before searching. "Color" means red, blue, green, black, white, gold, yellow, purple, pink, grey and gray, and Norwegian words too (rød, blå, grønn, svart, hvit, gul, rosa). The user listens to a lot of Norwegian music.
   2. For vibe themes, run `ft theme` with all of these:
      - `--vibe`: the subject and mood in a sentence ("anti-war songs, protest against war and nuclear weapons"). It searches both the track embeddings and the summaries.
      - `--sound`: translate the theme into how it sounds, as genres, instruments and regions. "Autumn" becomes "indie folk, acoustic, singer-songwriter, chamber folk, nordic folk, dream pop". This is how the search finds the right artists. Do not search artist names one by one to cover them.
      - 5 to 10 related `--word`s, in English and Norwegian. Avoid month and weekday names unless the theme is about them: Genius notes are full of release dates. Norwegian words also match English text ("fred" finds Genius notes about someone named Fred), so check why a Norwegian word matched.
      - `--exclude-tag` for genres that would clearly break the mood, if any.
      - Tags only as extra hints.
   3. If the sound covers several styles, run `ft search artist-vibe` once per style as well (for autumn: "nordic folk", "dream pop", "slowcore"), so one style does not crowd out the others.
   4. Treat every signal as a hint, never as proof:
      - Tags are noisy, and artist tags say nothing about a single song.
      - Lyrics and Genius notes cover most of the library, but a word in a lyric can be in passing.
      - Title words are literal ("Must Be Nice" matched "fairy tale" in its lyrics).
      - The track vibe search leans toward title words.
      - `artist-vibe` finds artists by genre, so a fitting artist can still bring tracks that miss the theme. Check them.
      A track that several signals agree on is a strong candidate. A track with one weak signal needs your own judgment.
   5. Fill in specific songs you know fit but that no signal found, through `ft search title` or `ft search artist`. Use this for a few known gaps, not as the main way to find artists. If you find yourself adding many artists by hand, the `--sound` description is too narrow: rewrite it and search again.
   6. Search in parallel where you can.
4. Curate:
   - Judge every candidate against the theme yourself, from what you know about the song and its `match` passage. A signal only says where to look.
   - Prefer tracks with `liked` or `playlist` in `sources`, or with many `plays`. The user actually listens to those.
   - Drop weak literal matches whose word only technically fits. When a song has `versions`, pick the one the user plays or keeps in the library.
   - Aim for 30 to 50 tracks unless the user asks for a different size.
   - Group the tracks into 3 to 6 sub-vibes. Order the groups so the playlist flows.
5. Show the grouped list as "Title (Artist)". Name the notable songs you left out and why. Ask before you create anything.
6. After the user approves, run `ft playlist create`. Use the theme as the name, with emojis if the theme had them. Put the theme text and the date in the description. Return the link. Also list the tracks the command reports as not on Spotify.

## When the index is wrong

- If a song the user expects is missing, check `ft stats`. The song may be in a playlist that another user owns: Spotify blocks the contents of those for this app. Songs the user scrobbled on Last.fm are still indexed.
- If Spotify is not authorized, tell the user to run `ft auth`.
- Do not edit the SQLite file directly.
