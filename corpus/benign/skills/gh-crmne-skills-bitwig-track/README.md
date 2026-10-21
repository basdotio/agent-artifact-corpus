# bitwig-track

An agent skill that composes an original track and builds it in Bitwig Studio.

The agent writes the music as data, then generates a Bitwig controller script from it. You add the script in Bitwig and press **Build**: it sets the tempo, creates the tracks, loads presets you have installed, sets sends, writes every part into clips, and adds cue markers. **Record** then plays it into the arranger. The agent also writes MIDI files for every part, so you can drag them in by hand if you prefer.

In Claude Code, run it with style notes:

```
/bitwig-track melodic organic house, 122 BPM, A minor
```

## Requirements

- Bitwig Studio 5.x or 6.x, with its Controller API (it ships with Bitwig).
- Python 3 (standard library only) to generate the score and the script.
- Node.js to syntax-check the script and run the host simulator.

## Install

```
gem exec skill add crmne/skills@bitwig-track
```

## Configuration

The skill looks in the usual places for each platform. Set these environment variables if yours differ:

| Variable | What | Default |
| --- | --- | --- |
| `BITWIG_HOME` | Bitwig install, used to find the API version | Linux `/opt/bitwig-studio`, macOS `/Applications/Bitwig Studio.app`, Windows `C:\Program Files\Bitwig Studio` |
| `BITWIG_API` | Controller API version for `loadAPI()` | detected from the installed Javadoc (25 is known good for Bitwig 6.1) |
| `BITWIG_SCRIPTS_DIR` | your Controller Scripts folder | Linux `~/Bitwig Studio/Controller Scripts`, macOS and Windows `~/Documents/Bitwig Studio/Controller Scripts` |
| `BITWIG_PACKAGES_DIR` | installed packages, where presets live | Linux `~/.BitwigStudio/installed-packages`, macOS `~/Library/Application Support/Bitwig/Bitwig Studio/installed-packages`, Windows `%LOCALAPPDATA%\Bitwig Studio\installed-packages` |

The agent only uses presets it finds installed. It never starts or stops Bitwig and never touches your open projects.

## Reference

`reference/` holds a worked, tested example: a film score generator (`film_score_example.py`), the controller script template (`template.control.js`), and a Node simulator of the Bitwig host (`simulate.cjs`). See the generator's docstring for its folder layout and input.
