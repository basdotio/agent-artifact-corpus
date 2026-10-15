export const meta = {
  name: 'group-subsystems',
  description: 'Phase 2 of header unification: one worktree agent per chunk of subsystems merges src files into subsystem files with include/<subsys>.h, keeping make compare matching',
  phases: [{ title: 'Group', detail: 'per chunk: merge files by subsystem, unify local types, headers, commit on branch' }],
}

const RESULT = {
  type: 'object',
  properties: {
    branch: { type: 'string' },
    commit: { type: 'string' },
    compare_ok: { type: 'boolean', description: 'true only if make clean && make -s -j12 compare printed OK on your final commit' },
    files_before: { type: 'integer' },
    files_after: { type: 'integer' },
    headers: { type: 'array', items: { type: 'string' } },
    renamed: { type: 'integer', description: 'functions given descriptive names' },
    notes: { type: 'string', description: 'what could not be merged/unified and why; subsystem boundary corrections; anything Phase 3 must handle' },
  },
  required: ['branch', 'commit', 'compare_ok', 'notes'],
}

const MAIN = args.repo

const prompt = c => `You are working on a matching decompilation of the GBA game ${args.game}: all game code is C that compiles byte-identically with agbcc (make compare prints "${args.rom}: OK"). Phase 1 created shared headers for the cross-cutting globals (${args.shared}). Now Phase 2: group the one-run-per-file sources (src/code_<addr>.c) into subsystem files.

You run in your own git worktree (current directory), a checkout of ${MAIN}. One-time setup in the worktree root:
  ln -s ${MAIN}/baserom.gba . ; ln -s ${MAIN}/tools/agbcc tools/agbcc ; python3 tools/split.py ; make -s -j12 compare
(it must print OK before you start).

Your chunk: subsystems ${c.rows} of docs/subsystems.md, address range 0x${c.start}-0x${c.end}. Only touch src files whose range lies inside it (splits.txt lists each file's range). Read docs/subsystems.md (the table and the notes for your subsystems) first.

For each subsystem in your chunk:
1. Merge its src files into src/<name>.c (the name from the table; drop "(?)" and pick a better name if the code makes the purpose clear). Functions stay in address order. A C file must be one contiguous range, so where an asm range (an unmatched function, kind asm in splits.txt, or the asm exceptions) sits inside a subsystem, make <name>.c and <name>_2.c around it. A file can only have one compiler flavour: splits.txt column 5 is o1 (-O1) or noiw (no interwork) or empty; split by flavour where needed. Update splits.txt (one line per new file, same format, column 5 kept), delete the old src files, run python3 tools/split.py.
2. Unify declarations inside the subsystem: one definition per struct type (local views of the same object become one struct with all fields; field names unk<hexoff>), one declaration per global. Scene-local globals (e.g. the scene state pointer gUnk_030000xx of a screen) get a canonical struct. Put shared types/externs/prototypes of the subsystem in include/<name>.h (include guard): prototypes of every function defined in the subsystem, with the exact signature of its definition. Calls into functions of OTHER subsystems keep their current local declarations for now (Phase 3 handles cross-subsystem prototypes); you may keep those in a block at the top of the .c file.
3. Do not edit the Phase 1 headers (${args.shared}) or global.h: other agents work in parallel. If one of them has a wrong field type for your code, keep a local cast and mention it in notes.
4. Descriptive names: you may rename sub_XXXXXXXX functions (docs/subsystems.md section 3 has proposals) ONLY if every reference is inside your chunk: check with grep -rlw sub_XXXXXXXX src asm include lib data. Rename the definition and all uses together.
5. Merging files can change the binary: an object's .rodata is placed right after its .text (see ld_script.ld), so if a file has const data or string literals, merging it with a following file moves that data; agbcc can also change code when declarations change (types of pointees, prototypes affecting argument conversion). Build often (make -s -j12 compare, about 1-2 min) and use tools/check_func.py FILE ADDR (prints MATCH or a diff; honours OPT=-O1 / OPT=-mno-thumb-interwork) for single functions. Never use inline asm. If two files cannot be merged without breaking the match, keep them as separate files of the same subsystem (<name>.c, <name>_2.c) and note why.
6. Commit after each subsystem (git add -A src include splits.txt objects.mk ld_script.ld asm; message "Group <name>" ending with the line "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"), only when make compare is OK. The final commit must pass make clean && make -s -j12 compare. Do NOT push and do NOT touch ${MAIN}.

Report branch, final commit, file counts before/after, headers created, number of renamed functions, and notes.`

const results = await parallel(args.chunks.map(c => () =>
  agent(prompt(c), { label: 'group-' + c.start, phase: 'Group', schema: RESULT, isolation: 'worktree', effort: 'high' })
    .then(r => r && { ...r, chunk: c.rows })))
return results.filter(Boolean)