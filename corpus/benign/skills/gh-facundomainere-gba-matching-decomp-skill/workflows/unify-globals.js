export const meta = {
  name: 'unify-globals',
  description: 'Phase 1 of header unification: one agent per cross-cutting global builds its canonical struct header and converts every src file to it, in its own worktree',
  phases: [{ title: 'Unify', detail: 'canonical struct + convert all users, make compare in worktree, commit on branch' }],
}

const RESULT = {
  type: 'object',
  properties: {
    branch: { type: 'string', description: 'git branch of your worktree (git rev-parse --abbrev-ref HEAD)' },
    commit: { type: 'string', description: 'final commit hash on that branch (empty if nothing committed)' },
    header: { type: 'string', description: 'header file you created, e.g. include/game_state.h' },
    struct_name: { type: 'string' },
    files_changed: { type: 'integer' },
    compare_ok: { type: 'boolean', description: 'true only if make clean && make compare printed OK on your final commit' },
    notes: { type: 'string', description: 'layout decisions, unions kept and why, anything left unconverted and why' },
  },
  required: ['branch', 'commit', 'header', 'compare_ok', 'notes'],
}

const MAIN = args.repo

const prompt = g => `You are working on a matching decompilation of the GBA game ${args.game}. All game code is already C that compiles byte-identically with agbcc (GCC 2.95). The goal now is shared headers: each global must have ONE canonical type in include/*.h instead of the many partial "view" structs scattered across src/*.c.

You run in your own git worktree (your current directory), a checkout of ${MAIN}. One-time setup in the worktree root:
  ln -s ${MAIN}/baserom.gba . ; ln -s ${MAIN}/tools/agbcc tools/agbcc ; python3 tools/split.py ; make -s -j12 compare
(it must print "${args.rom}: OK" before you start).

Your global: ${g.name} (${g.hint}).

Task:
1. Find every view: grep -n "${g.name}" src/*.c. Each file declares it with its own local struct (e.g. "struct A6C_9F8 { u8 pad0[0x378]; u16 unk378; };" plus "extern struct A6C_9F8 *${g.name};"), or as a raw u8 * / array with casts. Field names follow the convention unk<hex offset>, and padding is padNNN.
2. Build the canonical layout from all views: every field at its offset with its type and array size. Choose a descriptive struct name if the purpose is clear (else struct Unk_${g.name.slice(5)}), keep unk<off> field names unless a purpose is obvious. Use nested structs / arrays of structs where views show repeated records (e.g. arrays of 12-byte entries). Where views disagree on a field's type (u8 vs s8, u16 vs s16, scalar vs array), pick the type that most files use and fix the other files at the access site so the generated code stays identical (an explicit cast often changes codegen, so check; a union member is acceptable when nothing else works, document it). Put the struct and the extern declaration in a new header include/${g.header} (with an include guard), and include it from global.h ONLY if it is needed nearly everywhere; otherwise include it from each user file.
3. Convert every file that uses ${g.name}: delete its local view struct and extern line for this global, include the header, and adjust code where field names/types changed. Do not change other globals' views (other agents handle those in parallel) except where unavoidable; keep diffs minimal so branches merge cleanly.
4. Verify often with make -s -j12 compare (a full build takes about 1-2 minutes; tools/check_func.py FILE ADDR checks one function quickly: it prints MATCH or a diff). The final state must pass "make clean && make -s -j12 compare" with OK. Never use inline asm.
5. Commit on your worktree branch (git add -A src include && git commit -m "Unify ${g.name} into include/${g.header}" with the line "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" at the end of the message). Do NOT push and do NOT touch ${MAIN} itself (only read from it).

If a few files cannot be converted without breaking the match within your time, leave those files on their old view, still commit the rest (compare must pass), and list them in notes. Report the branch, commit, header, and notes.`

const GLOBALS = args.globals
const results = await parallel(GLOBALS.map(g => () =>
  agent(prompt(g), { label: 'unify-' + g.name, phase: 'Unify', schema: RESULT, isolation: 'worktree', effort: 'high' })
    .then(r => r && { ...r, global: g.name })))
return results.filter(Boolean)