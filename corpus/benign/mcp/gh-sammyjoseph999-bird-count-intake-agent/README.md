# Bird count intake agent

[![tests](https://github.com/Sammyjoseph999/bird-count-intake-agent/actions/workflows/tests.yml/badge.svg)](https://github.com/Sammyjoseph999/bird-count-intake-agent/actions/workflows/tests.yml)

A tool-using LLM agent that turns three piles of messy, hand-written bird count notes into one clean, validated roster, and sends anything it cannot clean with confidence to a review queue instead of guessing.

The idea comes from a Dataquest guided project on tool-using agents. The scenario, data, tool design, prompt and tests in this repository are my own.

## The problem

A local nature club runs an autumn bird count. Volunteers send in their tallies in whatever form they like:

- a paper logbook, typed up afterwards: `half a dozen cedar waxwings in the hawthorn`, `some kind of gull, too far out to tell`
- an email written as prose: `A couple of hawks were circling high up, couldn't tell which kind`
- a spreadsheet typed in a hurry: `Canda Goose`, a blank site, `12 (est)`, a bird that does not exist

The notes contain nicknames, typos, vague counts ("a handful"), relative dates ("yesterday"), missing fields, a date from the wrong month, and one sighting reported by two different people.

## Design

The work is split between a model and ordinary code, and the split is the point of the project.

| The model does the fuzzy part | The tools do the exact part |
|---|---|
| Reads free text and finds the sightings in it | Decides which species name is official |
| Works out that "pair" is 2 and "yesterday" is a date | Decides whether a record is complete and valid |
| Chooses a reason when something has to be flagged | Decides what counts as a duplicate |

Two rules follow from that:

1. **The agent never identifies a bird.** It passes the observer's wording to `resolve_species`, which does an exact lookup against the taxonomy and a table of known nicknames and misspellings.
2. **When in doubt, flag. Never fabricate.** A blank location or an unrecognised species goes to the review queue, not onto the roster with a guessed value.

```
data/*.txt, *.json ──> intake_agent.py ──(tool calls)──> intake_server.py ──> clean_roster.json
   messy sources         model + loop                     rules + state       review_queue.json
```

### The tool server (`intake_server.py`)

- `Observation`: a Pydantic model that defines a clean record (positive count, ISO date, non-blank location).
- `validate()`: one function that says yes or no, with reasons. It checks the record's shape, that the date falls in the count week, that the species code exists, and that it is a single species and not a group such as "gull sp.".
- `Roster`: holds the run's state. It assigns record ids, finds duplicates (same species, day and place, ignoring case), and queues review items without ever queuing the same one twice.
- Four MCP tools, exposed with FastMCP: `resolve_species`, `validate_observation`, `commit_observation` and `flag_for_review`.

`commit_observation` is the only way onto the roster, and it does not trust that the earlier steps happened. Every call re-validates the record and checks for a duplicate. Models tend to batch their tool calls and do not behave identically on every run, so the rules are enforced at the one place a record becomes permanent.

Two choices keep the model's influence small:

- The commit tool takes a species **code**, and the server fills in the common and scientific names from the taxonomy. The model cannot attach the wrong name to a code.
- The flag tool only accepts a fixed list of reasons, and `possible_duplicate` is not on it. Only the server can declare a duplicate.

The taxonomy is also published as an MCP resource (`taxonomy://marrow-creek/species`), and running `python intake_server.py` serves the same tools over stdio for any MCP client.

### The agent (`intake_agent.py`)

- `load_mcp_tools()` reads the tools from the server and converts them to the OpenAI function-calling format.
- `IntakeAgent.run_source()` runs the usual loop: send the messages, execute any tool calls, append the results, repeat until the model answers in plain text. It is capped at 40 rounds per source.
- `main()` processes the sources in a fixed order (logbook, email, spreadsheet). The order matters: when two sources report the same sighting, the first one committed is kept and the later one goes to review.

## Running it

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project folder with your OpenAI key:

```
OPENAI_API_KEY=your-key
```

Then:

```bash
python intake_agent.py     # writes clean_roster.json and review_queue.json
python check_outputs.py    # checks the two files
```

The run makes a few dozen small calls to `gpt-4o-mini`. Set `INTAKE_MODEL` in `.env` to use a different model.

## Testing

Testing an agent is different from testing ordinary code, because the same input does not always give the same output. The project is checked in three layers.

**1. The deterministic core** (`tests/test_core.py`, no API key). Name lookup, validation, duplicate detection and the commit gate are plain Python and are tested exactly.

**2. The agent loop** (`tests/test_agent.py`, no API key). A scripted stand-in for the model checks that tools are exposed in the right format, that tool results are fed back, that malformed arguments do not crash the run, and that the loop stops at its limit.

**3. The data** (`tests/test_sources.py`, no API key). Replays the tool calls a careful clerk would make for the bundled sources, to confirm that every name resolves as intended and the gate reaches the expected totals: 22 committed records and 12 review items.

```bash
pytest
```

**4. A real run** (`check_outputs.py`, needs the output of `intake_agent.py`). This does not compare against one fixed answer. It checks properties that must hold on every run:

- every committed record passes validation, and no sighting is on the roster twice
- the made-up "Marsh Gryphon Wren" is flagged `unknown_species`
- "some kind of gull" and "a couple of hawks" are flagged `species_group`
- the geese reported in both the logbook and the spreadsheet are caught as a possible duplicate
- the committed total is between 20 and 23, and the review queue between 10 and 14

A few notes are borderline on purpose. "A flock of grackles (didn't count)" has no number, and "robins everywhere, call it 20" is an estimate with one. The ranges allow for the model reading such notes differently between runs.

## Data

Everything in `data/` was written for this project.

- `taxonomy.json`: 32 common eastern North American species and four group entries. Species codes and scientific names are written in the style of the eBird taxonomy and should be checked against the live list before being relied on; the group entries use local placeholder codes starting with `x-`.
- `aliases.json`: nicknames and misspellings mapped to codes ("butterbutt", "red tail", "Canda Goose").
- `source1_logbook.txt`, `source2_email.txt`, `source3_spreadsheet.json`: the three sources.

## Possible extensions

- Load the full taxonomy from the eBird API, keeping the bundled file as a fallback.
- Run the server as a separate process and connect the agent to it over stdio.
- Add fuzzy matching inside `resolve_species` for misspellings that are not in the alias table, with a similarity threshold and a review flag for near misses.

## License

The code is released under the [MIT License](LICENSE). Datasets keep the terms of their original sources, described above.
