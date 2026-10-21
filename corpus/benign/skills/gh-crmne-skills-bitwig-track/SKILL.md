---
name: bitwig-track
description: Compose an original, professional track and build it inside Bitwig Studio through a generated controller script (Bitwig Controller API) that loads the user's installed presets, writes every part, and arranges it. Use when asked to make a track, song, beat, or score in Bitwig, or when invoked as /bitwig-track followed by style notes.
license: MIT
argument-hint: <style notes, e.g. "melodic organic house, 122 BPM, A minor">
---

# Make a track in Bitwig

Style notes for this track: **$ARGUMENTS**

You compose the music as data, generate a Bitwig controller script from it, and the user presses one button in Bitwig to build the whole project with their own presets. You can't hear audio, so the craft is in the composition, the sound choices, and verification.

## Ground rules

- **Original music only.** "In the style of X" means the genre, tempo, instrumentation, harmony and production feel of that artist. Never copy their melodies, chord sequences note for note, lyrics, or samples, and never name the artist in track, clip, or file names.
- **Never start, stop, or restart Bitwig yourself**, and never touch the user's open projects. Check whether it's running (`pgrep -af -i bitwig` on Linux and macOS, `tasklist | findstr /i bitwig` on Windows). The user runs the script.
- Work in a new folder for the track (in the current directory if it's a music folder, else ask where). Commit it if the folder is a git repository.

## The environment

Find these before you write anything. Environment variables win over the defaults.

| What | Variable | Default |
| --- | --- | --- |
| Bitwig install | `BITWIG_HOME` | Linux `/opt/bitwig-studio`, macOS `/Applications/Bitwig Studio.app`, Windows `C:\Program Files\Bitwig Studio` |
| Controller API version | `BITWIG_API` | detected from the install's Javadoc (25 is known good for Bitwig 6.1) |
| User controller scripts | `BITWIG_SCRIPTS_DIR` | Linux `~/Bitwig Studio/Controller Scripts`, macOS and Windows `~/Documents/Bitwig Studio/Controller Scripts` |
| Installed packages (presets) | `BITWIG_PACKAGES_DIR` | Linux `~/.BitwigStudio/installed-packages`, macOS `~/Library/Application Support/Bitwig/Bitwig Studio/installed-packages`, Windows `%LOCALAPPDATA%\Bitwig Studio\installed-packages` |

If a default doesn't exist, search for it (for example `find / -name 'installed-packages' -type d 2>/dev/null`) or ask the user. Bitwig's own Settings > Locations shows where it keeps packages and scripts.

- **API version.** Don't hard-code it. Find the Javadoc under the install (`resources/doc/control-surface/api/` on Linux and Windows, inside `Contents/` on macOS) and take the highest version it mentions: `grep -rhoE 'API version [0-9]+' <javadoc> | sort -k3 -n | tail -1`. The example script does this for you. Use that number in `loadAPI(N)`.
- **Javadoc.** `member-search-index.js` in the Javadoc folder lists every method. Grep it before you use a call.
- **Stock scripts** to learn from: `ControllerScripts/` next to the Javadoc's `doc/` folder.
- **User scripts** live at `<scripts dir>/<Vendor>/<Name>.control.js`. Bitwig reloads a changed file; turning the controller off and on in Settings > Controllers forces it.
- **Presets.** Discover what's installed, and pick only from that: `find "<packages dir>" -name '*.bwpreset'`. Group them by device folder (`.../Presets/<Device>/...`) to see what instruments, drums and effects you have. Common packages are Bitwig's Essentials (Polysynth, Phase-4, FM-4, Poly Grid, Polymer, E-Kick, E-Snare, E-Hat, Reverb, Delay-2, Compressor+, EQ+ and more) and Polymerics, but never assume any package is there. Check every path you use exists before you write the script.

A worked, tested example is in `reference/` next to this file:

- `film_score_example.py`: a score generator for a short film. It reads the film's scene timings, composes against them, and writes score.json, per-part MIDI files (with a built-in SMF writer), the Bitwig script and the README's arrangement map. Its docstring documents the folder layout, the input, and the flags. Its preset table is an example: it warns about every preset that isn't installed.
- `template.control.js`: the Bitwig script template. The generator fills in the API version, vendor, name, UUID and the score.
- `simulate.cjs`: a Node simulator of the Bitwig host that presses every button and checks the result against score.json.

Reuse their structure. They are written for a film cue, so adapt them to song sections.

## Method

1. **Pin the style down from $ARGUMENTS.** Write a short brief in the track's README before any notes:
   - tempo, key/mode, time signature, length and section map (for example intro 16, build 16, breakdown 32, drop 32, outro 16 bars);
   - instrumentation and the role of each part;
   - harmonic language (progression families, extensions, voice leading);
   - rhythmic feel (straight or swung 16ths, groove);
   - sound design and mix intent (sidechain feel, space, width, what carries the emotion).

   Ask the user only if the style is genuinely ambiguous. Otherwise decide and state your choices.
2. **Compose like a producer.** Write it as data: parts with notes `[start beat, pitch, velocity, duration]`, on a 16th grid unless the style needs otherwise.
   - A strong progression with real voice leading, plus a bass line that locks to the kick and moves with the harmony.
   - A memorable motif that develops across sections: call and response, variation, a final statement.
   - Drums with variation, fills into section changes, and velocity and humanization where the style wants it.
   - Arrangement dynamics: parts enter and leave, filter or energy builds, a breakdown that breathes, a drop that pays it off. Build with risers and impacts, or reverse swells.
   - Keep ranges playable and mixes uncluttered: one element owns each frequency band at a time.
3. **Choose sounds** from the presets you found, for each part, plus return tracks (reverb, delay) and a gentle master glue compressor. Write down why each preset fits the style.
4. **Generate everything from one script** (Python, standard library only; see the example): `score.json`, `midi/NN-<part>.mid` plus one combined type-1 `.mid` with section markers, the controller script, and the README with the arrangement map. Read paths from the environment variables above, with flags to override them.
5. **The controller script** (see `reference/template.control.js`):
   - `loadAPI(N)` with the detected version, a fresh UUID per track, no MIDI ports (`host.defineMidiPorts(0, 0)`).
   - Put its buttons in **controller preferences** (`host.getPreferences().getSignalSetting(...)`) so they show under the controller in Settings > Controllers. Document settings live in the Studio I/O panel, which is easy to miss.
   - Buttons: **Build**, **Lengths**, **Record**, **Stop**.
   - Build does all of this, safe to run again (reuse tracks, recreate clips), sequenced with `host.scheduleTask`, and waits and verifies after each async step:
     - set the tempo;
     - create the instrument tracks and return tracks, and load presets with `InsertionPoint.insertFile(path)`;
     - set the sends;
     - create one launcher clip per part in scene 1, or one scene per section;
     - write the notes through a launcher cursor clip (`setStepSize`, `setStep(channel, x, key, velocity, duration)`);
     - add cue markers per section.
6. **Verify without Bitwig:** syntax-check with `node --check`, and run the simulator against the script (`node bitwig/simulate.cjs`; extend it for anything new the script does). Parse the MIDI back (note counts, ranges, timing against the section map). Optionally render a rough numpy preview, clearly labelled as timing only.
7. **Install and hand over:** copy the script into `<scripts dir>/<Vendor>/` and give the user exact steps:
   1. File > New.
   2. Settings > Controllers > Add controller > <vendor> > <name>.
   3. Press Build, wait for the final popup, and press Lengths.
   4. Press Record, or launch scene 1 at bar 1 with arranger record armed, stopping after the last bar.
   5. Balance by ear, add a limiter, and use File > Export Audio (stems per track).

## Hard-won lessons (don't relearn these)

- **Clip length:** a new launcher clip is **1 bar long** whatever length you ask `createEmptyClip` for (seen in Bitwig 6.1.1). Setting `getPlayStart`, `getPlayStop`, `getLoopStart`, `getLoopLength` and `isLoopEnabled` without first calling `markInterested()` on each at init was ignored, so **mark them interested at init** (as the stock Maschine JAM script does). This is the likely cause, not yet confirmed in Bitwig. Set them on the empty clip and again after writing the notes, read them back, retry, and fall back to `duplicateContent()` doubling. Report every clip's length, as in "Pad: 128 beats (32 bars) (confirmed)", in a popup and with `host.println`.
- **Where messages go:** `host.println` goes to the **Controller Script Console** (the console icon on the controller in Settings > Controllers), not Bitwig's log file. Use `host.showPopupNotification` for the headline results the user should see.
- **Async:** track creation, device insertion and cursor-clip moves are asynchronous. Wait on observers (for example the track name or the clip's note count), never on fixed sleeps alone.
- **Presets:** drum presets play on specific keys. Check the note range a preset responds to (look at the preset's device), and pin one-shot parts to that key.
- **Fallback:** always ship the MIDI files, so the user can drag parts in by hand if a script step fails.
- **Final report:** the arrangement map (bars to sections), the preset per part, and what couldn't be verified. Be honest that you haven't heard it.
