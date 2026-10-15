# Agent-driven matching decompilation: strategy and findings

How this project goes from a GBA ROM to matching C with LLM agents, written to be reused
on other ROMs. Updated as we learn. Project-specific numbers are from Medabots AX (USA).

## Pipeline overview

1. **Scaffold a matching build first** (whole ROM as one `.incbin`, SHA1 check), so every
   later step can be verified with `make compare`.
2. **Find functions** with Ghidra headless (BinaryLoader, ARM:LE:32:v4t, base 0x08000000),
   export `start,end,thumb,name` to CSV (`tools/scripts/ExportFuncs.py`).
3. **Find the real code region**: only code reachable by `bl` / function pointers counts.
   Ghidra finds thousands of "functions" in data; here 8591 found, only 1671 in code
   (0x08000000-0x08056536, ~345 KB of an 8 MB ROM). Everything after is `.incbin` data.
4. **Split into round-tripping asm** (`tools/split.py --verify`): disassemble each function,
   rebuild, diff against the ROM, demote mismatching instructions to raw `.2byte`, repeat
   until byte-identical.
5. **Fix function boundaries** before decompiling (fragments merged, literal pools owned by
   their function, missed starts added in `starts.txt`).
6. **Decompile with agents through a claim queue**, one function at a time, each verified
   in isolation and then in the full build before it is committed.
7. **Retry near-misses with decomp-permuter** (CPU search over C variants).
8. **Consolidate** into subsystem files with shared headers (in progress).

## Tools (all in `tools/`)

| Tool | Purpose |
|---|---|
| `split.py` | ROM -> `asm/*.s` + `data/data.s`, link order from `splits.txt`; `--verify` loop |
| `check_func.py FILE.c ADDR` | compile one function with agbcc, link at its address, diff vs ROM (~0.3 s) |
| `claim.py` | hands out the next unclaimed function under `flock .decomp.lock` |
| `integrate_one.sh ADDR FILE.c NAME` | re-check, add to `src/`, `make compare`, record progress, commit, push (serialized) |
| `add_funcs.py` | integration core: merges consecutive matches into one file, falls back to separate files on conflicting declarations, rolls back on failure |
| `syms.py` | generates `build/syms.ld` defining `gUnk_XXXXXXXX` data symbols at their address |
| `progress.py [--record]` | % of code bytes in C (excluding `asm` exceptions) + ETA from `progress_history.csv` |
| `post_run.py RUNDIR` | after a workflow run: ingest reported missed starts, release skipped claims, record bandit stats |
| `bandit.py` | per model/effort throughput stats; picks next run's agent configs |
| `permute.py ADDR FILE.c [secs]` / `permute_all.sh` | decomp-permuter on near-misses |

Config files: `splits.txt` (`start end c|asm name [old]`), `starts.txt` (extra function
starts), `claims.txt` (queue state), `lib/aliases.s` (library names agbcc emits itself).

## Agent loop

Each worker agent loops up to N functions: claim -> read asm -> write C in scratch ->
`check_func.py` until MATCH -> `integrate_one.sh` -> next. Rules that mattered:
- Agents never edit repo files directly; only `integrate_one.sh` does, under a lock.
- Name externals by address (`sub_XXXXXXXX`, `gUnk_XXXXXXXX`) so the checker and the build
  resolve them without a symbol database.
- Time-box near-misses (~15 min / ~25 attempts), then save the closest attempt and move on.
- Attempt every claimed function; never claim beyond the limit (some agents skipped large
  functions and left them claimed).
- Agents report "missed start at XXXXXXXX" in notes; `post_run.py` ingests these.
- Agents read `docs/matching_tips.md` first (compiler-specific tricks, known struct layouts).
  Verified from transcripts: every agent reads it once at start. But a shared knowledge file
  only grows if something feeds it: agents can't edit repo files, so they report new tricks
  in a `tip` result field and `post_run.py` appends them (curate periodically). It sat
  unchanged for several runs before this was added.
- Tips have IDs; agents report `tips_tried` / `tips_helped` per function and
  `tools/tip_stats.py` tallies exposure/tried/helped to flag tips to purge (no help after 150
  functions of exposure, or <10% help rate after 10 tries). Purges are reviewed, not automatic.

Streaming beats batches: 8 long-lived agents each claiming the next function avoids
waiting for the slowest agent of a batch.

## Model / effort selection (bandit)

Score = committed code bytes per **cost unit** (API list-price dollars, used as a proxy for
subscription quota: on a quota plan the binding constraint is the usage limit, which counts
heavier models more; list prices per model: input, output, cache
write at 1.25x input, cache read; usage taken once per API message from agent transcripts).
Bytes per agent-hour is still reported. Cache reads dominate agent traffic (~23M cache-read vs
~0.3M other tokens for one agent), so a token count that skips them badly misstates cost.
Slots are assigned by **Thompson sampling**: per slot, draw each arm's score around its mean
with spread ~1/sqrt(agent-hours) (untested arms get a wide prior) and give the slot to the
highest draw. The most-sampled arm keeps 2 slots as a floor until a challenger has 1 agent-hour.
(Replaced a greedy "6 to the leader, 2 explore" rule that needed several runs to promote a
challenger 3.7x better on cost.)
First Thompson run (run 20, 4 Sonnet-medium agents): Sonnet-medium's 3.7x lead collapsed from
~1880 to ~580 bytes per cost unit once it had 4 agents of data -- the early number was one lucky
agent. Opus-medium took the lead (~780) with Sonnet-medium and Opus-default close behind. Expect
small-sample leads to regress; Thompson sampling limits the damage to one run.
Decay + Thompson has a side effect: arms that are rarely picked lose evidence every run, look
permanently uncertain, and keep winning draws (run 22's raw draw gave 4 of 8 slots to the two
weakest arms). Fix: arms whose mean is < 60% of the best share at most one slot per run.
**Function size confounds bytes-based scores across runs**: run 22 hit a stretch of tiny
dispatch functions, so Opus-medium (6 of its agents) dropped to 320 bytes per cost unit while
doing as well as the others in that run. Scores are now normalised per run (each arm's cost
weighted by its run's overall bytes per cost unit), giving a relative score where 1.0 is the
run average. With that, Opus medium (1.07) and default (1.04) are tied; Sonnet medium is 0.78.
They were tied because they were the same arm: an agent with no effort set inherits the session
effort, and the transcripts show "default" Opus agents ran at `effort: medium`. Merged into one
arm. Check what "default" resolves to before treating it as a separate setting.
**Fresh vs retry are different contexts.** On small fresh functions Opus medium/low are cheapest
per byte; on large retried near-misses Opus high wins clearly (relative 1.05 vs medium 0.79,
~3450 vs ~2450 bytes/agent-hour). Retry runs keep separate stats (`BANDIT_CONTEXT=retry`).
Untested arms get an optimistic prior in Thompson sampling, so with few tested arms they would win
most draws; they now share at most one slot per run. Earlier design: 6 of 8 agents use the best setting, 2 explore
the least-sampled others.

Current standings (auto-generated):

<!-- bandit:start -->
| Setting | Decayed agent-hours | Committed / claimed | Relative score (1.0 = run avg) | Bytes per cost unit | Bytes / agent-hour | Cost units / agent-hour |
|---|---|---|---|---|---|---|
| default-high | 1.48 | 2.7 / 6.6 | 1.01 | 93 | 734 | 7.93 |
| default-medium | 0.12 | 0.1 / 0.5 | 0.99 | 112 | 822 | 7.37 |
| default-low | 0.01 | 0.0 / 0.1 | 0.72 | 146 | 860 | 5.90 |
| sonnet-high | 0.00 | 0.0 / 0.0 | 0.06 | 9 | 90 | 10.40 |
| sonnet-medium | 0.00 | 0.0 / 0.0 | 0.00 | 0 | 0 | 13.19 |
| sonnet-low | 0.00 | 0.0 / 0.0 | 0.00 | 0 | 0 | 14.42 |

_Cost unit = API list-price dollars, used as a proxy for subscription quota (heavier models consume quota faster); not an actual bill. 29 runs recorded; older runs decayed x0.7 per run; updated by post_run.py._
<!-- bandit:end -->

History: the first A/B (runs 10-12, easy early functions) had Opus default at ~4000-4900
bytes/agent-hour vs Sonnet low ~2600, high ~2300, medium ~1900. By 50% done every arm had slowed
(harder functions), and Sonnet medium overtook Opus on recent data.

Sonnet agents tended to skip large functions, which flatters their per-function rates.

**The problem is non-stationary.** Address-order claiming leaves harder functions for later,
so every arm's throughput falls over time (Opus default went from ~4000 to ~2300 bytes/h by
40%). A plain cumulative mean then favors arms sampled early on easy functions: after run 15
the bandit wanted Sonnet-low (0.6 agent-hours, mostly run 10) over Opus (17.7 h). Fix: decay
older runs (x0.7 per recorded run) and require >= 1 agent-hour before an arm can be exploited.
(First tried 2 h: an explore arm gets ~0.5 agent-hours per run, so with decay it plateaus at
0.5/(1-0.7) = 1.7 h and could never be exploited. Explore slots now go first to arms beating the
leader, so a promising arm accumulates evidence quickly.)

**Tip usage reports are noisy.** T06 (zero temporary) was flagged for purge (1 help in 11
tries) although 47 matched files use that exact pattern; agents under-credit tips. Cross-check
a purge candidate against the matched source before removing it. Most tips are situational
(only some functions need them): a 150-function zero-help threshold flagged 26 of ~60 tips after
two runs, so it was raised to 400.
- **Review policy:** every flagged tip gets a decision, recorded in the file: retire it (moved to
  "## Retired" with a reason) or tag it `(keep: reason)`, which suppresses re-flagging. Tracking
  without decisions let T28 sit flagged for 3 runs. T28 was redundant with the agent prompt
  (which already says when to try old_agbcc), so agents credited the prompt, not the tip.
- **Classification cadence:** agent tips land unsorted in "Reported by agents"; when more than 10
  pile up, `post_run.py` prints CURATION DUE and a curation pass merges them into sections
  (keeping the lowest ID of merged duplicates so stats stay attached).
  By ~56% the file is saturating: curation 3 merged 12 of 13 new agent tips into existing ones.
- **ID allocation bug:** new tip IDs were taken from the highest *line-start* ID, so IDs that
  only survived inside "(merges ...)" notes got reused (T117-T126 collided). Allocate from the
  highest T-number anywhere in the file; colliding tips were renumbered T134-T139 (no stats lost).
- **First curation (at 50%)**: 99 -> 47 active tips (26 merged groups, 4 retired). The refreshed
  style analysis (893 functions) overturned an early claim: byte-offset access to globals does
  match in many files (343 `u8 *` externs vs 504 struct-pointer externs), so early "rules" from a
  small sample need re-checking as the corpus grows. Rules that tell the agent which compiler to
  use belong in the agent prompt, not the tips file.
- **Function starts can be off by a few bytes** (a reported start 4 bytes late, inside the
  prologue). Agents notice when their C matches bytes shifted by N; trust check_func's diff.
Opus low/medium effort (run 13): ~2450 bytes/agent-hour each, below Opus default (~3300 cumulative); default effort stays the main arm.

## Gotchas found (GBA / agbcc / binutils)

- **objdump 2.40 decodes Thumb-2/v6 even with `-marmv4t`** (and for ELF input). On ARMv4T the
  only 32-bit Thumb encoding is a `bl` pair: split any other 32-bit decode and treat
  post-v4T mnemonics (`sxth`, `cbz`, `it`, ...) and empty register lists as raw data.
- **`adds rX, rX, #imm3`**: GAS picks the imm8 encoding; emit the original as raw.
- **ld pads each object to 4 bytes with a Thumb nop**: object (file) boundaries must be
  4-aligned or the ROM shifts.
- **Function-end padding**: the original zero-pads (`.align 2, 0` of the next function in
  the same file) in 209/212 cases; append `.align 2, 0` to agbcc output.
- **Absolute function symbols need `.thumb_set`**: with `--defsym` ld treats the target as
  ARM and inserts an interworking veneer instead of a direct `bl`.
- **Data symbols** in the full build: generate a linker script assigning each
  `gUnk_XXXXXXXX` its address (functions are defined by asm/C, never there).
- **Mixed compilers**: some files were built with `old_agbcc` (tell: leaf functions with
  branches ending in plain `bx lr`, where agbcc emits `push {lr}`/`pop`). Support a
  per-file compiler column in `splits.txt`.
- **agbcc emits `memcpy` by name** for struct copies/initializers: alias it to the ROM's
  copy routine (`lib/aliases.s`, and in the checker).
- **libgcc in ROM**: `__divsi3`, `__modsi3`, `__udivsi3`, `__umodsi3`, `_call_via_rN`;
  find them early and tell agents.
- **Ghidra boundary errors**: (a) unreferenced Thumb starts without `push {..,lr}` are usually
  fragments of the previous function (merge them); (b) but small unreferenced leaf
  functions do exist and get merged wrongly. Auto-detecting them from `bl` targets did NOT
  work (216 candidates, mostly bogus, none of the real misses) -- agent reports did.
- **Fake starts inside big functions**: agbcc emits `bl` as a long branch inside functions over
  ~2KB; Ghidra treats the targets as functions, truncating the real one so it can never match
  (sub_08012FA0: real 3440 bytes, split into 7). The "2-mod-4 aligned functions" once listed as an
  asm exception were these fake starts. Fix: `ignore_starts.txt` merges them back; agents report
  "bogus start at X". A heuristic over all bl targets was far too noisy (159 hits, mostly real).
- **GCC nested functions**: a function that saves r9 (static chain) and whose only caller does
  `mov r9, sp` before each call is a nested function defined inside that caller; both compile into
  one object. Merge the caller's start into the nested function's range (`ignore_starts.txt`) and
  integrate them as one unit (sub_08054318 inside sub_0805435C).
- **-O1 library code**: the EEPROM/timer save library near 0x08055270-0x0805546C matches only at
  -O1 (no gcse PRE). Solved with the per-file `o1` marker in splits.txt (column 5, set by
  `OPT=-O1 tools/integrate_one.sh`). The nested pair sub_0805509C inside sub_080550DC was
  integrated as one C range via the END span.
- **libgcc names**: agbcc emits `__divsi3` etc. by name for `/` and `%`; alias them (like memcpy)
  or agents must call the sub_ directly, which orders operand loads differently and can't match.
- **Literal pools**: Ghidra often counts them as code; the splitter emits them inside the
  function. Tools that build comparison targets must rebuild pools from relocations.
- **Conflicting guessed declarations**: two agents type the same global differently; merged
  files fail to compile. Test-compile merges and fall back to separate files; consolidate
  headers later (better: early -- see Open ideas).
- **Integration lock is the bottleneck** once agents are fast: every integration ran a full split + rebuild (~2 min queue with 5 agents waiting). Writing only changed files lets make rebuild incrementally (~10 s per no-op cycle).
- **Agents phrase reports differently** ("missed start at", "unlabeled start at"); parsers of agent notes need several patterns, or better, a dedicated structured field.
- **`;` in a commit chain hides failures too**: `make clean; make compare; git commit` committed a
  non-matching tree (reverted within minutes). Gate commits with `&&` on the clean build itself.
- **Shell pipelines hide exit codes** (`make ... | tail` always "succeeds"): one broken commit
  was pushed this way. Check `$?` of the command itself, never of a pipeline.

- libgcc's `_call_via_rN` thunks (`bx rN; nop`) and lib1funcs division routines sit right before newlib's memcpy/memset/strlen at the end of the code region. They are hand-written asm: mark them `asm` in splits.txt early so agents don't burn claims on them, and alias them (lib/aliases.s + check_func ALIASES) so C indirect calls `fn(args)` link as `bl _call_via_rN`. A real indirect call can allocate registers differently than an explicit `sub_0805616C(args, fn)`.
- A leaf with a bare `bx lr` next to -O1 library code can need old_agbcc while its neighbour needs new agbcc -O1: it is a separate file (report the missed start), since one file has one compiler flavour.

- Per-file compiler flavours (splits.txt 5th column, set by integrate_one env): `old` (CC1=old_agbcc), `o1` (OPT=-O1, flash/EEPROM/timer library), `noiw` (OPT=-mno-thumb-interwork: newlib memcpy/memset/strlen end in `pop {..,pc}`), `bugfix` (OPT=-fprologue-bugfix: leaves with a bare `bx lr` next to normal functions, which may explain some ranges first attributed to old_agbcc). Tells: a bare `bx lr` leaf means old or bugfix. `pop {..,pc}` with no `bx` means noiw.
- The last function in the code region owns the tail padding up to where data starts (CODE_END=0x08056538 here, not Ghidra's 0x08056536).
- integrate_one.sh takes END=XXXXXXXX for one C file spanning several functions (missed leaves inside a range).

- Wrong compiler flavour is a cheap near-miss to rule out: run 41 matched ~20 saved attempts unchanged once `-fprologue-bugfix` existed. Agents had often misdiagnosed these as old_agbcc. After adding a flavour, run `tools/flavour_sweep.py SCRATCH` over all saved attempts before spending agents on them.

- Endgame (last ~10 functions, all retried 5+ times): low-effort agents stop after a few variants ("earlier passes tried ~30 variants") and add nothing. Use medium/high only. One agent per function with perAgent=1, and raise the retry cap step by step (3 -> 6 -> 10). Most of the late wins came from dumping agbcc's RTL (-da / -dL / -dG / .greg) to read allocation priorities, not from trying more variants.

- Header unification (goal: shared types in include/*.h, files grouped by subsystem). One-function-per-file matching leaves every global with many partial "view" structs: here gUnk_03001A6C had 145 views, `struct Obj` 144 variants, and 4215 of 5387 local prototypes disagreed with the definitions. The plan:
  - Phase 1: one agent per cross-cutting global, each in its own git worktree with baserom.gba and tools/agbcc symlinked in. It builds the canonical struct from all views, converts every user file, gets `make clean && make compare` to OK, and commits on its branch.
  - Merge: I merge the branches serially and resolve conflicts, which are mostly adjacent extern lines.
  - Phase 2: one agent per subsystem (address range) handles scene-local globals and tags, merges files into a subsystem .c, and writes include/<subsys>.h with prototypes.
  - Phase 3: callers use the callee subsystems' headers instead of local prototypes.
  - Start it only after matching has wound down, so integrations don't race the refactor.
  - Phase 3b merge: the Makefile has no header dependencies, so an incremental `make compare` after a merge that only edits headers keeps stale .o files and prints OK while the clean build fails (branch 1 had dropped a battle_load.h declaration still used by opponent_intro.c). Check every merge with `make clean` (~6 s here).
  - Parallel branches that each drop one of two duplicate declarations of a global leave it declared nowhere. Agree on the surviving header before fanning out. Widening a header prototype to s16 (sprite_group.h, battle_damage.h) often lets other files drop their local copies.

- Merging parallel unification branches: declaration-only hunks resolve mechanically with `tools/resolve_decl_conflicts.py` (diff3 conflict style, line-position 3-way merge). Where both sides rewrote the same code line for different globals, first rewrite the base and branch sides of the hunk into HEAD's form for HEAD's globals, then run `git merge-file`, which applies only the branch's other edits. Afterwards check that each side's uses of its own global survived exactly.

- **Build flags (big simplification).** Every default-flavour file (1168) compiles byte-identically with and without `-fprologue-bugfix`. Every old_agbcc file (45) matches new agbcc plus `-fprologue-bugfix`, and the -O1 files ignore the flag. So the original build was a single agbcc `-O2 -fprologue-bugfix` (plus -O1 for the Nintendo flash/EEPROM/timer libraries and the sound driver, and no-interwork for newlib). The flag is now global in the Makefile and check_func, and only `o1` and `noiw` remain as per-file flavours. **For the next ROM: try `-fprologue-bugfix` globally on day one.** A bare `bx lr` leaf (no `push {lr}`) is that flag, not old_agbcc.
- Phase 1 header unification is done: 7 shared headers (game_state.h with 430 files, battle.h with 246, gfx_regs.h, scene_1544.h, fx.h, input.h, sprite_slots.h). Every agent produced a matching branch.
  - Merging needed three tools in order: `resolve_decl_conflicts.py` (declaration hunks), then `tokmerge.py` (token-level 3-way merge for lines where both sides edited different globals), then a hand fix for the few left (about 3 of 60 files).
  - Agents' notes:
    - Quick per-file checks must use the same flags as the build. The agents saw `push {lr}` appear in old/bugfix files when they checked them without those files' objects.mk overrides.
    - GCC fold_truthop merges `a.x == c && a.y == d` on adjacent struct fields into a single ldrh, so some raw-offset accesses must stay raw (u8 *) to match.
    - Unions are needed where files read the same bytes as different widths (OAM attr as bitfields, u16 or s8).
- Phase 2 plan: docs/subsystems.md (62 C subsystems plus 4 asm).
- Phase 3a (battle types): 15 Medabot views, 11 attack-object views and 8 part-record views folded into `struct Medabot`, `struct AttackObj` and `struct PartStats` in battle.h, with no unions. What made it quick:
  - **Ask the compiler which view fields are used:** blank a view's body (`u8 zz[SIZE];`), compile its users, and collect the "no member named" errors. Only used fields need to agree, which cut 35 declared conflicts to about 20 real ones.
  - **Compare per file, not per ROM:** keep the baseline `build/src/*.s`, recompile one file (under 1 s for all battle files) and diff the .s per function, ignoring `.LCB` label numbers (an extra RTL insn shifts them without changing any bytes).
  - **Pick each signedness by experiment:** flip one field's type, recompile everything, and count the functions that start or stop matching. Majority by views or by access counts was often wrong (unkB4/B6/16C/4A). Then fix the minority sites with an rvalue cast (`(u16)s->unk1C`, `(s16)p->unk8A[n]`, `(u8)p->unk6[j]`), which matched every time it was needed here.
  - Where a view used scalars and the merge chose an array, scalar uses that still compile (`if (p->unkA <= 0)` on an array) silently change the code. The .s diff catches them.
  - Redundant casts and prototypes: remove each `(struct X *)` cast on its own and keep the removal only if the .s and the diagnostics are unchanged. Raw offsets like `(u8 *)gUnk_030010A0 + 8 + i * 396` mostly became `&gUnk_030010A0->ents[i]` the same way. Battle_DebugMenu's `+8` view (StageMedabotX) did not: operand order changed.

- Phase 2 (grouping) result: 8 worktree agents, one per contiguous chunk of docs/subsystems.md, about 90 minutes. They turned 1253 files into 66 subsystem files (a `_2.c` only where an unmatched asm range or a flavour forces a split) and wrote 62 headers. They renamed 406 functions, but only where every reference was inside the agent's own chunk, which kept the merges conflict-free. The only merge conflicts were in splits.txt (rebuild each chunk's lines from its branch) and in the generated objects.mk/ld_script.ld (regenerate). No file in the game had .rodata, so merging files never moved data.
  - Agents kept local struct copies wherever a Phase 1 header lacked fields or had the wrong signedness; Phase 3 folds these back.
  - TBAA matters: agbcc -O2 uses type-based alias analysis, so turning raw `u8 *` accesses into struct fields can reorder loads and stores. Convert one function at a time and keep the raw form where it must stay.
- Phase 3 (prototypes): including a callee's header brings in all its prototypes, so every differing local declaration in the includer becomes a "conflicting types" error. `tools/use_headers.py` handles only the files where every declaration already matches. The rest is agent work, because integer parameter and return widths change call-site code.

- **Track header dependencies once headers carry real types.** Without them, an incremental `make compare` reuses stale objects after a header changes and can print OK on a broken tree; this happened in a Phase 3b merge. The fix is the preprocessor flags `-MMD -MP -MF build/src/X.d`, plus `-include build/src/*.d` in the Makefile.

- **Endgame result (Medabots AX):** 100% in about 2.5 days of wall time. The last 4 functions (0.4%) took about 15 agent rounds. Every final fix was a compiler-internals trick, found by instrumenting agbcc (fprintf in reload1.c allocate_reload_reg and global.c find_reg) and reading the -da/-dg dumps, not by trying more C variants:
  - packed 1-byte struct locals, plus a code-free set that combine later deletes, to make combine forget a register's nonzero bits;
  - a `while` loop instead of a hand-written goto loop, so the loop-entry copy of the exit test (duplicate_loop_exit_test) uses up one reload register and is then cross-jumped away;
  - an empty `do {} while (0);`, whose loop notes stop regmove's forward rename;
  - one variable holding two unrelated values, to win a global-alloc priority race (REG_EQUIV doubles the live length of pseudos set from constants);
  - code-free self-copies (`x = x;`) to lengthen a rival pseudo's life.
  - For the next ROM: give endgame agents the instrumented compiler from the start, and run one agent per function with a long time box.

- **Naming pass (after 100%).** Renames never change code, so `make compare` checks every step. The order that worked:
  1. Read-only agents, one per chunk, propose names for the functions and globals their chunk owns (owner = chunk with the most uses). Each writes a JSON map with one-line function comments.
  2. `tools/rename.py` applies all maps in one pass. Data symbols lose their address suffix, so they get a `symbols.txt` entry, which syms.py and check_func read. Never rename functions defined in asm/: split.py regenerates their labels.
  3. Worktree agents, one per chunk, rename subsystem-header fields and locals, and add comments. Shapes kept only to match get `/* matching: ... */`.
  4. One worktree agent per shared header renames its fields. It renames the header, then fixes only what the compiler flags, because names like unk4 exist in many structs.
- **Merging rename branches:** tokmerge can keep both versions of a line where one side renamed a field and the other renamed a local, which leaves stale duplicate lines. The compiler catches them in code but not in comments. After a merge, rebuild each conflicted file token by token: for every name, take whichever side changed it relative to the merge base.

- **Second version from the same source (Rokusho), about 1 hour.** Paired GBA versions usually share almost all code.
  1. `tools/version_align.py OTHER.gba` aligns every function, comparing bytes with `bl` immediates and literal-pool pointers masked. Here 1679 of 1688 functions were identical and 8 differed (about 4 KB).
  2. `tools/make_version.py NAME OTHER.gba` writes the per-version files:
     - the header asm;
     - the data incbin from the shifted code end;
     - library aliases moved by the end delta;
     - `symbols_NAME.ld`, which maps every data symbol through literal-pool pairs taken from the identical functions.
  3. `make VERSION=NAME` builds into `build_NAME/`, compiling with `-DVERSION_NAME`; `check_func.py` with `VERSION=NAME` checks a function against the other ROM.
  4. Differences go behind `#ifdef`. Here they were small: a version index into two-entry tables (save magic, banner palette), one extra palette load in the link menus, and one extra CpuSet on the title screen.
  - Gotcha: raw ROM-address constants in C (callback pointers, table addresses written as integers) do not follow the data. Wrap them in `VER(base, other)`, or better, turn them into symbols.
  - Gotcha: a table indexed by version can map to the wrong entry in the pool-derived symbol map (here `gHeaderBannerPal` mapped to entry [1]); fix those by hand.

## decomp-permuter setup (agbcc)

- Compile script: `cpp | agbcc | append ".align 2, 0" | as` (`tools/permuter_compile.sh`).
- Preprocess `base.c` with the project's include paths first (the permuter runs a bare cpp).
- Build `target.o` from ROM bytes, not from asm text: `.inst.n` per halfword, symbolic
  `bl sub_X`, and `.4byte SYM` wherever the compiled base has an ABS32 reloc whose name
  matches the ROM word. Otherwise the base score includes every pool word (605 vs 5).
- Run in its own process group and kill the group on timeout (workers outlive the parent).
- First result: a function an agent gave up on after exhausting its variants matched in under 5 seconds.

## Throughput history (Medabots AX)

| Date | Code in C | Rate | Note |
|---|---|---|---|
| 2026-10-01 | 0.2% | | first batch (barrier) |
| 2026-10-01 | 7% | ~12.6 KB/h | streaming queue |
| 2026-10-01 | 22% | ~17 KB/h | |
| 2026-10-02 | 35% | ~13 KB/h avg | session limit cost ~hours; bandit + permuter added |

## Open ideas / next steps

- **Shared headers early** (known struct layouts in `include/*.h`) so agents start from them and
  neighbours can merge into subsystem files. Not started yet; needed for goal item 5. Do it as a
  dedicated pass between runs (touches every src file).
- **Ghidra drafts** (done at 50%): `tools/scripts/DumpDrafts.py` on the already-analysed project
  wrote 717/725 drafts in minutes into `decomp/drafts/ADDR.c` (gitignored). The agent prompt points
  agents at them for control flow/constants only. Effect on throughput: to be measured.
- **Permuter on every near-miss** (done): `permute_all.sh` runs continuously from
  `permuter/queue.txt`; `post_run.py` queues each run's near-misses (needs DECOMP_SCRATCH).
  First 91 tried: 5 matches.
