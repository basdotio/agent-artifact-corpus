export const meta = {
  name: 'name-symbols',
  description: 'Phase A of naming: one read-only agent per chunk proposes descriptive names and one-line comments for the functions and globals it owns',
  phases: [{ title: 'Name', detail: 'read code, write a JSON name map per chunk' }],
}

const RESULT = {
  type: 'object',
  properties: {
    map_file: { type: 'string', description: 'path of the JSON name map you wrote' },
    functions_named: { type: 'integer' },
    globals_named: { type: 'integer' },
    notes: { type: 'string', description: 'naming themes / anything uncertain' },
  },
  required: ['map_file', 'functions_named', 'globals_named'],
}

const MAIN = args.repo
const S = args.scratch

const prompt = (i, c) => `Read-only naming task in ${MAIN}, a complete matching decompilation of the GBA game ${args.game} (${args.about}). Do NOT modify any file in the repo and do not run make or git; other work may run concurrently.

Your chunk: subsystems ${c.rows} of docs/subsystems.md (address range 0x${c.start}-0x${c.end}). The functions and globals you own are listed in ${S}/ownership.json under key "${i}" ("functions": sub_XXXXXXXX defined in your chunk; "globals": gUnk_XXXXXXXX mostly used in your chunk). Read docs/subsystems.md (section 3 has name proposals), the src files of your subsystems, their include/*.h, and callers/users elsewhere (grep) as needed.

For EVERY owned function and global whose purpose you can determine from the code, propose a name; skip only those that are truly unclear (keep those as is). Conventions (pret style):
- Functions: PascalCase with a subsystem prefix where helpful, e.g. Battle_UpdateCamera, Snd_PlaySong, Title_Main, WorldMap_HandleInput. Be specific about what it does (verb first after the prefix).
- RAM globals (gUnk_02xxxxxx / gUnk_03xxxxxx): gCamelCase, e.g. gBattleState, gFadeLevel, gKeysHeld. ROM data (gUnk_08xxxxxx): gCamelCase too, e.g. gPartStatsTable, gTitleBgGfx.
- Names must be unique, valid C identifiers, and must not collide with existing names (grep -rw NAME src include before choosing).
Also give each function a one-line comment (what it does, in plain words, max ~100 chars).

Write the result as a JSON array to ${S}/names_${i}.json: [{"old":"sub_08012FA0","new":"Ai_ChooseMoveDirection","comment":"Picks the CPU bot's next move direction from the current AI state."}, {"old":"gUnk_030010A0","new":"gBattle"}, ...] (globals need no comment). Use python to write it so it is valid JSON. Report the file path and counts.`

const results = await parallel(args.chunks.map((c, i) => () =>
  agent(prompt(i, c), { label: 'name-' + c.start, phase: 'Name', schema: RESULT, effort: 'medium' })
    .then(r => r && { ...r, chunk: i })))
return results.filter(Boolean)