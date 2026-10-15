export const meta = {
  name: 'name-shared-fields',
  description: 'Rename unk fields of the shared headers (one agent per header, in worktrees) and fix every use; make compare must stay OK',
  phases: [{ title: 'Fields', detail: 'one shared header per agent' }],
}

const RESULT = {
  type: 'object',
  properties: {
    branch: { type: 'string' },
    commit: { type: 'string' },
    compare_ok: { type: 'boolean', description: 'true only if make clean && make -s -j12 compare printed OK on your final commit' },
    fields_renamed: { type: 'integer' },
    fields_left: { type: 'integer' },
    notes: { type: 'string' },
  },
  required: ['branch', 'commit', 'compare_ok', 'notes'],
}

const MAIN = args.repo

const prompt = h => `You are in your own git worktree (current directory), a checkout of ${MAIN}: a complete matching decompilation of the GBA game ${args.game} (${args.about}). Functions, globals, subsystem-local struct fields and locals already have descriptive names. One-time setup in the worktree root:
  ln -s ${MAIN}/baserom.gba . ; ln -s ${MAIN}/tools/agbcc tools/agbcc ; python3 tools/split.py ; make -s -j12 compare
(must print "${args.rom}: OK" first).

Your header: include/${h.file} (${h.what}). Rename its struct fields named unk<off> (in every struct the header defines) to descriptive names wherever the purpose is clear from how the code uses them, keeping the offset in a trailing comment (e.g. "s16 posX; /* 0x0AE */"). Arrays and sub-structs too. Fields with unclear purpose keep their unk name; padding stays padNNN. Many src files already contain comments describing what these fields mean (grep for the field name, e.g. "unk1CBD"; battle_ai.c, battle_attack_obj.c and battle_physics.c have glossaries at the top): use them, and update or delete those comments once the field has a real name.
Method: rename a field in the header, run make -s -j12 compare, and fix each "has no member named" error (src/*.c and include/*.h, any subsystem). Be careful that a field name like unk4 also exists in other structs: only change accesses that the compiler flags. Only names and comments may change; no types, expressions or statement/declaration order (they affect the generated code). Do not edit other shared headers' structs (other agents rename those in parallel): ${h.others}.
Build often; commit in steps when OK (git add -A src include; message ending with "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"). Final commit must pass make clean && make -s -j12 compare. Do NOT push; do not touch ${MAIN}.`

const ALL = args.headers.map(h => h.file)
const results = await parallel(args.headers.map(h => () =>
  agent(prompt({ ...h, others: ALL.filter(x => x !== h.file).join(', ') }), { label: 'fields-' + h.file, phase: 'Fields', schema: RESULT, isolation: 'worktree', effort: 'high' })
    .then(r => r && { ...r, header: h.file })))
return results.filter(Boolean)