<p align="center"><a href="README.md">中文</a> | <b>English</b></p>

# Buffett & Munger Evidence Skill v0.3.1

A Claude Code / Claude Agent Skill that answers investment, business and life questions the way Warren Buffett and Charlie Munger reason about them, using their **primary sources** (shareholder letters, annual-meeting Q&A, speeches, interviews) as evidence. It first decides whether they would take the question at all, then applies their filters to reach "yes / no / too hard", and ends with verifiable citations to the original text.

**This is retrieval over a local library, not a distilled model, and it does not speak for either man.** Not finding something does not mean they never said it; every inference is labelled as such. The skill's instructions and references are written in Chinese and answers default to Chinese.

## What it does

- **Two-layer answers**: first the persona layer (Buffett gives a conclusion, the deciding factors and one real case; Munger gives a sharp one-line judgment, then cross-checks it with as many mental models from different disciplines as the question needs and, for investment questions, against the best opportunity already at hand), then the evidence layer (full-sentence quotation + Chinese rendering + source link + note on applicability).
- **Evidence discipline**: quotes only complete sentences that were actually opened and checked; distinguishes original writing, publisher transcripts, third-party notes, biographies and translations; separates the period a text covers from its publication date; never puts words in Munger's mouth about events after his death (2023-11-28).
- **Local hybrid retrieval**: SQLite FTS5/BM25 + local ONNX multilingual E5 embeddings + cross-encoder reranking, all offline; source text is never sent to an external service.
- **Tools**: annual-meeting Q&A unit search (`qa.py`), source-backed topic/case Wiki (`wiki.py`), full-sentence quote extraction (`quote.py`), speaker attribution review (`attribution.py`), blind evaluation (`evaluate.py`), and collectors for public sources such as the Berkshire Hathaway website and CNBC's Warren Buffett Archive.

## What it does not include

This repository ships **no source texts, ebooks, videos or indexes**. The library lives outside the skill directory and you build it on your own machine from public sources with the collector scripts. Copyrighted books can only be imported from copies you legally own, and must not be redistributed.

## Version

Current version **v0.3.1** (preview: a fresh install collects only part of the material automatically; see "Building the library"). The name and URL never change; the version lives in `metadata.version` in `SKILL.md` and in [Releases](https://github.com/muhaibao/buffett-munger-evidence-skill/releases). A local install whose version equals the latest Release is that release.

## Install

```sh
git clone https://github.com/muhaibao/buffett-munger-evidence-skill ~/.claude/skills/buffett-munger-evidence
```

**Let an AI agent install it**: give the agent the repository URL and tell it to follow [INSTALL.md](INSTALL.md). It has copy-paste commands, measured run times and what to report back; no human steps are needed.

## Building the library

```sh
SKILL=~/.claude/skills/buffett-munger-evidence
DATA=~/buffett-munger-data
PY="$DATA/runtime/bin/python"

# Isolated Python environment (needs uv)
uv venv --python 3.12 "$DATA/runtime"
uv pip install --python "$PY" -r "$SKILL/scripts/requirements-retrieval.txt" pypdf lxml brotli

# Collect every public source, merge, download models, build the semantic index and Q&A units (resumable)
"$PY" "$SKILL/scripts/bootstrap.py" --data "$DATA"
```

`bootstrap.py` runs every automated collector in a fixed order (Berkshire shareholder letters, Wesco letters, annual and quarterly reports, CNBC annual-meeting transcripts 1994–2024, the Stripe Press edition of *Poor Charlie's Almanack*), merges the staged batches, downloads and verifies the models, builds the semantic index and Q&A units, runs one hybrid-search smoke test each for Buffett and Munger, and prints a JSON report (also saved as `$DATA/bootstrap-report.json`). Measured run time: about 80 minutes, plus a 270 MB model download. If it is interrupted or fails, rerun the same command; finished collectors are not redone. Step-by-step manual commands are in [references/local-library.md](references/local-library.md), [references/collection.md](references/collection.md) and [references/retrieval.md](references/retrieval.md) (Chinese).

Then ask in Claude Code, for example "How would Buffett look at a consumer-electronics company whose technology changes fast?", or invoke `/buffett-munger-evidence`.

### Known limitations (measured on an empty directory, 2026-10-16)

Running `bootstrap.py` on an empty directory on an Apple M5 Pro gave the following (per-step times are in [INSTALL.md](INSTALL.md)):

- **What a fresh library contains**: 279 documents, 86,096 passages. 48 Berkshire shareholder letters (1977–2024), 13 Wesco letters (1997–2009), 31 annual reports (1995–2025), 92 quarterly reports (1996–2026), 62 CNBC annual-meeting transcripts (1994–2024) and 33 Stripe Press *Poor Charlie's Almanack* documents (the 11 talks, plus later addenda, a separate Q&A and editorial material). Of the speaker-labelled passages, 38,617 are Buffett's and 7,616 are Munger's; reports, questioners and editorial material are attributed to no one.
- **Munger is clearly thinner**: interviews, Daily Journal meetings, Wesco meeting notes, the 1983–1996 Wesco letters, the partnership letters, OCR of early annual reports and the Worldly archive's Munger articles have no collector, so a fresh library does not have them. The maintainer's library includes these hand-curated batches and is richer.
- **Source gaps**: the first run had two transient download failures (a corrupt 2020 annual-report PDF and a dropped connection on the 2015 Q1 report). Rerunning the same command filled both, leaving zero gaps; it added exactly one document and re-imported none of the 217 already present. Adding a document triggers a full semantic-index rebuild (about 16 minutes measured).
- **Attribution map**: `assets/attribution_map.json` keeps only three Munger documents that can be fetched byte-for-byte from their URLs; they take effect after you import them with `library.py fetch` using the listed `url`. Collector-built documents already label every personal passage, so `attribution.py propose` finds nothing to add and `--attribution author` returns the same results as `strict`.
- **The topic / case Wiki is not shipped**: `wiki.py check` hashes metadata that includes capture time and local paths, so it can never match a library someone else builds. Checking the maintainer's 25 pages against the fresh library: 103 of 118 evidence links point at passages whose text, source file and speaker are identical, yet every metadata hash differs; the other 15 cite material that has no collector. A fresh library's Wiki is therefore empty, and the Wiki step of the answer protocol returns nothing.
- **Passage IDs depend on the pypdf version**: the same PDF extracted with pypdf 6.21 and 6.10 is sometimes split differently. In 25 of 61 letters the passage IDs differ, and in 22 of those the text is identical and only the splits moved. Chunk IDs from libraries built at different times are not interchangeable; cite by URL, source SHA and locator.
- **Network**: the models (about 270 MB) come from huggingface.co and the download does not resume. During the test the connection dropped to about 30 KB/s, at which point the model download becomes the slowest step.
- **Platform**: tested on Apple Silicon macOS only; the reranker is an arm64-optimised quantised model, and other platforms are untested.

## Tests

```sh
cd ~/.claude/skills/buffett-munger-evidence/scripts
"$PY" -m unittest discover -p 'test_*.py'
```

## Layout

| Path | Contents |
|---|---|
| `SKILL.md` | Skill entry point: answer protocol, output format, evidence floor |
| `INSTALL.md` | Unattended install steps and report template for AI agents |
| `references/` | Reasoning order (`cognition.md`), evidence rules, retrieval, collection, Wiki, evaluation, source map |
| `scripts/` | One-command build (`bootstrap.py`); library, retrieval, Q&A, Wiki, quoting, attribution, evaluation and collector scripts with tests |
| `assets/` | Verified source entry points, the reviewed attribution map, recorded speech chapter links |

## Disclaimer

Not affiliated with or endorsed by Berkshire Hathaway, Warren Buffett, Charlie Munger, their families or agents. Output is not investment advice. Quoted source texts remain the copyright of their respective owners.

## License

Code and documentation are released under the [MIT License](LICENSE).
