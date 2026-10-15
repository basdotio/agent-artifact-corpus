---
name: gba-matching-decomp
description: Run a complete matching decompilation of a Game Boy Advance ROM to C that rebuilds byte-identically with agbcc. Covers ROM splitting, agent-driven function matching with model/effort bandits, near-miss retries and the permuter, header unification and subsystem grouping, naming and comments, extra game versions from the same source, decomp.dev progress reports, and making the repo safe to publish. Use when the user wants to decompile a GBA game, continue such a project, or reproduce the Medabots AX pipeline on another ROM.
---

# GBA matching decompilation

A playbook for taking a GBA ROM to 100% matching C, grouped by subsystem, named and commented. It is distilled from a full run on Medabots AX (Metabee + Rokusho): about 1,700 functions in 2.5 days of wall time, using agent workflows. `reference/STRATEGY.md` is the full log of what worked and what didn't. Read it before starting, and read its "Gotchas" when something fails.

What's bundled:
- `templates/tools/`: every tool used. Copy it into the new repo's `tools/` and adapt it using `templates/PORTING.md`.
- `templates/`: the Makefile, `aliases.s`, `global.h`, the CI progress workflow, and the LICENSE used for the tools.
- `workflows/`: Workflow scripts for each multi-agent phase. Pass them to the Workflow tool with `script` (read the file) or `scriptPath`.
- `reference/matching_tips.md`: agbcc matching tricks, graded by how often they helped. Many of them carry over to any agbcc game.

## Ground rules (never break these)

1. **Never commit the ROM or game assets.** Gitignore `*.gba`, `*.sav` and `*.zip`. Data and the Nintendo logo come in through `.incbin "baserom.gba", ...` at build time.
2. **`make compare` must pass before every commit.** Gate commits with `&&` on a clean build: `make clean && make -s -j12 compare && git commit ...`. Never use `;` and never pipe make's output, because both hide its exit status. This mistake happened twice.
3. **Track header dependencies.** Use `-MMD -MP` in the Makefile from the start. Stale objects can make `make compare` lie after a header change.
4. **No inline asm.** Only code that can't come from agbcc stays as named `.s` files, and each one is listed in PROGRESS.md with its reason: the header, crt0, BIOS SWI stubs and libgcc.
5. **Commit and push after each batch** and add a dated line to PROGRESS.md. Keep `docs/STRATEGY.md` updated with new findings.

## Phase 0: Scaffold (about half a day)

1. Identify the ROM: game code and SHA1. Install pret's agbcc into `tools/agbcc`, plus arm-none-eabi binutils.
2. Run a Ghidra headless pass (Ghidra 11.x, Java 17) with the scripts in `templates/ghidra/` (copy them to `tools/scripts/`). Cap the analysis at about 40 minutes; the project is saved even when it times out:
   ```sh
   analyzeHeadless ghidra_proj game -import baserom.gba -loader BinaryLoader \
     -loader-baseAddr 0x08000000 -processor ARM:LE:32:v4t -scriptPath tools/scripts \
     -preScript GbaSetup.py -analysisTimeoutPerFile 2400 \
     -postScript ExportFuncs.py "$PWD/decomp/functions.csv"
   ```
   To re-export from the saved project, without re-analyzing:
   ```sh
   analyzeHeadless ghidra_proj game -process -noanalysis -readOnly -scriptPath tools/scripts \
     -postScript ExportFuncs.py "$PWD/decomp/functions.csv"
   ```
   For per-function C drafts that agents start from, run the same command with `-postScript DumpDrafts.py ADDRFILE "$PWD/decomp/drafts"` (ADDRFILE has one hex address per line). Agents look for `decomp/drafts/ADDR.c`, and `tools/collect_notes.py` writes their earlier notes to `decomp/notes/ADDR.txt`. Keep `decomp/` gitignored except `functions.csv`. Find the code region: everything that `bl` instructions and code pointers land in. Ghidra "functions" after it are false positives in data.
3. Run the splitter (`tools/split.py`). It writes `asm/*.s` from objdump with labels; anything that doesn't round-trip is emitted raw, and data becomes `.incbin`. Get `make compare` to OK on all-asm. Gotchas:
   - objdump decodes Thumb-2 even with `-marmv4t`.
   - ld pads each object to 4 bytes with a nop, so file boundaries must be 4-aligned.
   - Absolute function symbols need `.thumb_set`, or ld emits interworking veneers.
4. Add `splits.txt`, the C/asm ranges. Its 5th column is the compiler flavour: `o1` = -O1, `noiw` = no interwork. `objects.mk` and `ld_script.ld` are generated from it. Then `tools/progress.py` and PROGRESS.md.
5. **Try `-fprologue-bugfix` globally on day one.** In Medabots AX, every "old_agbcc" function was really agbcc with `-fprologue-bugfix`: a bare `bx lr` leaf means that flag. Check also for `-O1` library code (Nintendo flash/EEPROM/timer libraries, the sound driver) and newlib built without `-mthumb-interwork` (`pop {..,pc}` with no `bx`).

## Phase 1: Agent matching (most of the time)

The pipeline, all under `flock .decomp.lock`:
- `tools/claim.py` hands out the next unclaimed function. `tools/retry_claim.py` hands out near-misses, largest first, with a retry cap.
- `tools/check_func.py FILE ADDR` compiles one function and diffs it against the ROM (about 0.3 s). Env vars: `OPT`, `CC1`, `END` (span several functions) and `VERSION`.
- `tools/integrate_one.sh ADDR FILE NAME` re-checks, merges the function into src/ (`add_funcs.py`), runs make compare, records progress, commits and pushes.

Run `workflows/decomp-stream.js` with args `{repo, game, rom, scratch, agents, perAgent, mode: 'retry'?, configs, noIntegrate?, projectNotes}`. Each agent loops: claim, read the asm and the Ghidra draft, write C, check_func, integrate. Keep each workflow under 10 agents.

Between runs:
- **`tools/post_run.py TRANSCRIPT_DIR`.** TRANSCRIPT_DIR is the workflow run's directory: the Workflow tool prints it as "Transcript dir" (under `~/.claude/projects/<project>/<session>/subagents/workflows/wf_*`), and it holds `journal.jsonl`. It ingests "missed start" and "bogus start" reports into `starts.txt` / `ignore_starts.txt`, releases skipped claims, appends agent tips, records bandit stats and queues near-misses for the permuter. For retry runs, set `BANDIT_CONTEXT=retry`, plus `DECOMP_SCRATCH`.
- **Model/effort selection with `tools/bandit.py next N`.** It is Thompson sampling on committed bytes per cost (list price as the proxy), with decay. Arms with less than MIN_HOURS of data are capped at a few slots, and replacement slots go only to proven arms. Keep separate contexts for fresh and retry work.
- **Tips:** curate `docs/matching_tips.md` when post_run prints CURATION DUE. Use a cheap subagent for this. Never retire a tip that has helped, and don't call a tip a duplicate when it is the inverse trick.
- **Function boundaries:**
  - Fake starts: agbcc uses `bl` as a long branch inside functions over about 2 KB. List the fake start in `ignore_starts.txt`.
  - GCC nested functions: integrate the pair as one unit, with the `END` span.
- **Permuter:** keep `tools/permute_all.sh` running on near-misses. It must also take functions in retry status.
- **After adding a compiler flavour,** run `tools/flavour_sweep.py SCRATCH` over all saved attempts before spending agents on them. In one run this matched about 20 functions unchanged.

**Endgame** (the last 1-2% of functions):
- Use one agent per function, at medium or high effort only; low-effort agents quit too early.
- Raise the retry cap step by step: 3, 6, 10, 15, 25.
- Every last win came from **instrumenting agbcc and reading its dumps**, not from more C variants:
  - put an fprintf in reload1.c `allocate_reload_reg` and in global.c `find_reg`;
  - read the `-da`, `-dg` and `-dL` dumps, especially the global-alloc priorities (refs, live_length) in the .greg file.
- The tricks that won are in STRATEGY and matching_tips:
  - a code-free set that combine later deletes;
  - a `while` loop instead of a hand-written `goto` loop, so jump.c duplicates the exit test;
  - an empty `do {} while (0);` to stop regmove's forward rename;
  - one variable reused for two unrelated values, to win a global-alloc priority race;
  - `x = x;` to lengthen a rival pseudo's life.

## Phase 2: Shared headers and subsystem grouping

One file per function leaves every global with dozens of partial "view" structs. In Medabots AX, the main game-state global had 145 views. Unify them in phases, using git worktrees: each agent symlinks in `baserom.gba` and `tools/agbcc`, then commits on its own branch.

1. **Cross-cutting globals** (`workflows/unify-globals.js`, args `{repo, game, rom, globals: [{name, header, hint}]}`). Each agent builds the canonical struct from all views and converts every user file.
2. **Plan** (one read-only agent). It writes `docs/subsystems.md`: subsystem ranges in address order, with no gaps and no file split. Use scene state pointers, call-graph locality, and flavour boundaries.
3. **Group** (`workflows/group-subsystems.js`, one agent per contiguous chunk). It merges files into `src/<subsys>.c` plus `include/<subsys>.h`. It renames only functions whose every reference is inside its own chunk, which keeps merges clean.
4. **Prototypes** (`workflows/unify-prototypes.js`). Replace cross-subsystem local prototypes with header includes. Integer parameter and return widths change call-site code; pointer types never do. `tools/use_headers.py` does the trivial cases.
5. **Merge the branches serially:**
   - `git -c merge.conflictStyle=diff3 merge --no-commit --no-ff BRANCH`;
   - then `tools/resolve_decl_conflicts.py FILES`, then `tools/tokmerge.py FILES` (token-level 3-way merge);
   - fix the rest by hand, and rebuild from clean before each commit.
   - If agents make inconsistent choices about shared declarations (which header owns a global), hand the merge to an agent with explicit rules.

Watch for:
- **TBAA:** turning raw `u8 *` accesses into struct fields can reorder loads, so convert one function at a time.
- **fold_truthop:** it merges adjacent-field `&&` compares.

## Phase 3: Names and comments

Renames never change code, so `make compare` verifies them.

1. **Propose names** (`workflows/name-symbols.js`). First run `python3 tools/ownership.py CHUNKS.json SCRATCH/ownership.json` with the same chunks as the workflow: read-only agents, one per chunk, propose names for the functions and globals their chunk owns. The owner is the chunk with the most uses. Each writes a JSON map with one-line comments.
2. **Apply** with `tools/rename.py MAP.json`. Data symbols lose their address suffix, so they go into `symbols.txt`, which `syms.py` and check_func read. **Never rename functions defined in asm/**: split.py regenerates their labels.
3. **Fields, locals and comments** (`workflows/name-fields-locals.js`): worktree agents, one per chunk, rename subsystem-header fields and locals and add comments. They mark shapes that exist only to match with `/* matching: ... */`.
4. **Shared-header fields** (`workflows/name-shared-fields.js`): one worktree agent per shared header. It renames, then fixes only what the compiler flags, because names like `unk4` exist in many structs.

Merge caveat: tokmerge can keep both versions of a line where one side renamed a field and the other renamed a local. Rebuild such files token by token, taking each name from whichever side changed it, and check comments too, since the compiler can't.

## Phase 4: Other versions of the game (about 1 hour)

1. Run `tools/version_align.py OTHER.gba` (needs a fresh base build). It aligns all functions, masking `bl` immediates and pool pointers. Medabots Rokusho: 1,679 of 1,688 identical, 8 different.
2. Run `tools/make_version.py NAME OTHER.gba`. It writes the header asm (logo via incbin), the data incbin from the shifted code end, the shifted library aliases, and `symbols_NAME.ld`, which maps data symbols through literal-pool pairs.
3. Build with `make VERSION=NAME`, into `build_NAME/` with `-DVERSION_NAME`. Check functions with `VERSION=NAME python3 tools/check_func.py`. Put differences behind `#ifdef` / `GAME_VERSION`.
4. Two gotchas:
   - raw ROM-address integers in C must become `VER(a, b)` or symbols;
   - version-indexed tables can map to the wrong pool entry, so fix those by hand.

## Phase 5: Publish

- **Progress reports for decomp.dev.** Use `tools/objdiff_report.py` plus `templates/github/progress.yml`. It needs no ROM, because it works from `splits.txt` and the committed address tables in `versions/`. CI uploads `<version>_report` with `report.json` (objdiff v2). Validate it with `objdiff-cli report changes A B`. The labeled `[asm]` units count as matched and complete, the same convention other GBA decomps use.
  - Once CI runs on `main`, register at decomp.dev/manage/new.
  - "No workflows found" means decomp.dev's view of the repo is stale or the repo is still private. Sign out and in again.
- **Before making the repo public:**
  - keep the Nintendo logo out of the files (incbin it);
  - scrub local paths from committed stats;
  - check the whole history for `.gba` / `.pyc` / logo bytes and for the email.
  - If something needs removing, use `git filter-repo` with a blob callback and a mailmap, after making a backup bundle, then force-push.
- **License:** the usual convention is no license on the decompiled code, plus a README disclaimer (unofficial, no affiliation, no ROM or assets, bring your own copy). `templates/LICENSE.tools` is an MIT license that covers only `tools/` and `docs/`.

## Workflow arguments

Each script reads `args` (pass a JSON object, not a string). Common keys:
- `repo`: absolute path of the project, e.g. `"/home/me/mygame"`.
- `game`: the game title, e.g. `"Medabots AX - Metabee Ver. (USA)"`.
- `about`: one line about the game for naming agents, e.g. `"robot battle RPG: parts, medals, story map, link play"`.
- `rom`: the output ROM name, e.g. `"mygame.gba"`.
- `scratch`: a scratch directory for agent files, outside the repo.
- `shared`: the shared Phase-2 headers as one string, e.g. `"include/game_state.h, battle.h, global.h"`.

Per script:
- `decomp-stream.js`: `{repo, game, scratch, agents: 8, perAgent: 10, mode: "retry" (optional), configs: [{model, effort}, ...] (from bandit.py next), noIntegrate: false, projectNotes: "- memcpy resolves to sub_XXXXXXXX ...\n- ..."}`
- `unify-globals.js`: `{repo, game, rom, globals: [{name: "gUnk_03001A6C", header: "game_state.h", hint: "main game state, ~145 files"}, ...]}`
- `group-subsystems.js`, `name-fields-locals.js`: `{repo, game, rom, shared, chunks: [{rows: "#1-#8", start: "08000258", end: "08009604"}, ...]}`, where `rows` are the row numbers of the docs/subsystems.md table.
- `unify-prototypes.js`: `{repo, game, rom, shared, chunks, foldPrompt (optional: a game-specific job that folds struct views into one shared type), skipBattle}`
- `name-symbols.js`: `{repo, game, about, scratch, chunks}`, after `tools/ownership.py` has written `SCRATCH/ownership.json`.
- `name-shared-fields.js`: `{repo, game, about, rom, headers: [{file: "battle.h", what: "struct Battle, the 0x18C entity struct, ..."}, ...]}`

## Running it unattended

Drive the agent phases with `/loop` in dynamic mode. On each wakeup:
1. If a workflow is running, only check progress.
2. Otherwise:
   - post-process the finished run and release the claims of dead agents;
   - run split, then a clean `make compare`;
   - commit and push, update STRATEGY;
   - launch the next run with the bandit configs.
3. Keep the permuter alive.

Session limits pause work silently, so on resume always post-process whatever finished.
