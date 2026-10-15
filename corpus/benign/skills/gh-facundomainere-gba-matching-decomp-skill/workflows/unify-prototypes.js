export const meta = {
  name: 'unify-prototypes',
  description: 'Phase 3 of header unification: optional type fold, and replace cross-subsystem local prototypes with header includes, in worktrees',
  phases: [{ title: 'Phase3', detail: 'battle struct fold + per-chunk prototype unification' }],
}

const RESULT = {
  type: 'object',
  properties: {
    branch: { type: 'string' },
    commit: { type: 'string' },
    compare_ok: { type: 'boolean', description: 'true only if make clean && make -s -j12 compare printed OK on your final commit' },
    remaining_local_prototypes: { type: 'integer', description: 'cross-subsystem local prototypes still left in your files' },
    notes: { type: 'string' },
  },
  required: ['branch', 'commit', 'compare_ok', 'notes'],
}

const MAIN = args.repo
const SETUP = `You run in your own git worktree (current directory), a checkout of ${MAIN}. One-time setup in the worktree root:
  ln -s ${MAIN}/baserom.gba . ; ln -s ${MAIN}/tools/agbcc tools/agbcc ; python3 tools/split.py ; make -s -j12 compare
(it must print "${args.rom}: OK" before you start). The project is a matching decompilation of the GBA game ${args.game}: every change must keep make compare OK (a full build is about 1-2 min; tools/check_func.py FILE ADDR checks one function, honouring OPT=-O1 / OPT=-mno-thumb-interwork). Never use inline asm. Commit on your worktree branch in steps, only when make compare is OK; messages end with the line "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>". Do NOT push and do NOT touch ${MAIN}. The final commit must pass make clean && make -s -j12 compare.
Source layout: src/<subsystem>.c files (see docs/subsystems.md), each with include/<subsystem>.h holding the prototypes of the functions it defines (exact definition signatures) and its types. Phase 1 headers for cross-cutting globals: ${args.shared}.h, battle.h, gfx_regs.h, scene_1544.h, fx.h, input.h, sprite_slots.h.`

// optional game-specific type-fold job (e.g. fold every entity-struct view into one header type)
const battlePrompt = args.foldPrompt ? SETUP + '\n\n' + args.foldPrompt : null

const protoPrompt = c => `${SETUP}

Task (Phase 3b, prototypes) for the subsystems in address range 0x${c.start}-0x${c.end} (${c.rows} of docs/subsystems.md): their src files still declare functions of OTHER subsystems locally (extern/prototype lines whose definition lives in another src file). Replace them with #include of the callee's header (include/<callee subsystem>.h), so that every function has exactly one prototype, in its own subsystem's header. Including a header brings all its prototypes, so local declarations that differ from the definition's signature become compile errors ("conflicting types"): resolve each so the generated code stays identical, e.g. change the caller's argument expression or add a cast at the call (check with make compare: integer parameter/return widths change truncation code, pointer types never change code), and if the definition's own signature is clearly wrong-but-equivalent you may change it in its header and source ONLY if that source is in your range. Also replace local extern declarations of globals that a header already declares with the header (same rules). Only edit src files in your range and the headers of your range's subsystems; if a header of another subsystem is wrong, keep a local cast and note it. tools/use_headers.py (replaces local prototypes that already match the header) is a useful first pass: python3 tools/use_headers.py src/<file>.c ... then make compare. Report how many cross-subsystem local prototypes remain in your files and why.`

const jobs = [
  ...(args.skipBattle || !battlePrompt ? [] : [() => agent(battlePrompt, { label: 'phase3a-battle', phase: 'Phase3', schema: RESULT, isolation: 'worktree', effort: 'high' }).then(r => r && { ...r, job: 'battle' })]),
  ...args.chunks.map(c => () => agent(protoPrompt(c), { label: 'phase3b-' + c.start, phase: 'Phase3', schema: RESULT, isolation: 'worktree', effort: 'high' }).then(r => r && { ...r, job: c.rows })),
]
return (await parallel(jobs)).filter(Boolean)