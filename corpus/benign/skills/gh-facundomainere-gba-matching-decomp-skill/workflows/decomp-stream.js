export const meta = {
  name: 'decomp-stream',
  description: 'Stream-decompile ${args.game} functions: 8 agents each claim, match, and commit functions one at a time',
  phases: [{ title: 'Decompile', detail: 'each agent loops claim -> match -> integrate/commit' }],
}

const RESULT = {
  type: 'object',
  properties: {
    functions: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          addr: { type: 'string' },
          committed: { type: 'boolean', description: 'true only if tools/integrate_one.sh exited 0 for it' },
          name: { type: 'string' },
          notes: { type: 'string', description: 'what it does; if not committed, why (what still differs)' },
          tips_tried: { type: 'array', items: { type: 'string' }, description: 'IDs (e.g. T07) of matching_tips.md tips you applied at any point for this function' },
          tips_helped: { type: 'array', items: { type: 'string' }, description: 'IDs of tips that are in your final code and were needed for the MATCH (empty if not matched)' },
          tip: { type: 'string', description: 'optional: one line describing a NEW general agbcc matching trick you discovered (not specific to this function and not already in docs/matching_tips.md), else empty' },
        },
        required: ['addr', 'committed', 'name', 'notes'],
      },
    },
  },
  required: ['functions'],
}

const REPO = args.repo
const S = args.scratch

const prompt = i => `You are one of several agents decompiling the GBA game ${args.game}, USA) to C that compiles BYTE-IDENTICALLY with agbcc (pret's GCC 2.95-era GBA compiler, -O2 -mthumb-interwork). Repo: ${REPO}.

Loop, up to ${args.perAgent} functions:
1. Claim: cd ${REPO} && flock .decomp.lock python3 tools/${args.mode === 'retry' ? 'retry_claim.py' : 'claim.py'}
   Prints "ADDR END SIZE" (hex start, hex end, bytes incl. literal pool), or nothing when the queue is empty (then stop).
2. Read its disassembly: grep -n "^sub_ADDR:" ${REPO}/asm/*.s and read to the next "sub_" label. If ${REPO}/decomp/drafts/ADDR.c exists, it is Ghidra's decompilation of the function: use it for control flow and constants, but rewrite types, structs, and names in this project's style (Ghidra's types and boundaries are unreliable). src/*.c has already-matched neighbors for reference (types, globals).
3. Write C in ${S}/ADDR.c (only there; never edit repo files yourself) and check:
   cd ${REPO} && python3 tools/check_func.py ${S}/ADDR.c ADDR
   It prints MATCH, or original vs. compiled disassembly side by side (* = differs). A check takes ~0.3 s.
${args.noIntegrate ? '4. On MATCH: do NOT integrate (another agent is editing src/ right now). Save the matching file as ' + S + '/ADDR.c, report committed=false and put "MATCHED, not integrated" plus the exact env used (OPT / CC1 / END) at the start of notes. Ignore the integrate_one.sh lines below.\n' : ''}4. On MATCH: cd ${REPO} && tools/integrate_one.sh ADDR ${S}/ADDR.c NAME
   Never wrap integrate_one.sh in a timeout and never redo its steps by hand: it may wait for the lock behind other agents, and killing it midway can leave a half-applied integration.
   (NAME = descriptive name if the purpose is clear, else sub_ADDR; the C function itself must stay named sub_ADDR.) It re-checks, adds it to src/, runs make compare, records progress, commits and pushes. Exit 0 = committed. If it fails, report the output in notes and move on.
${args.mode === 'retry' ? 'RETRY MODE: every function you claim was already attempted by earlier agents and not matched (usually large and hard). Before starting one, read the previous closest attempt at ' + S + '/ADDR.c (if it exists, start from it: copy it, then improve) and every earlier agent note in ' + REPO + '/decomp/notes/ADDR.txt (what still differed and what was already tried). Do not repeat variants the notes say were tried. Time-box per function: ~40 minutes or ~50 check_func attempts instead of 15/25. If still not matched, save your best version back to ' + S + '/ADDR.c and report precisely what still differs.\n' : ''}0. Before your first function, read ${REPO}/docs/matching_tips.md (known agbcc tricks and struct layouts for this game). When you find a new general trick that isn't in it, put one line in that function's 'tip' field (the file is updated from these after the run). For every function, report honestly which tip IDs you tried (tips_tried) and which ones are in the final matching code and were needed (tips_helped); tips that never help get removed.
5. Time-box: if there is no MATCH after ~15 minutes or ~25 check_func attempts on one function, stop. Leave the claim as is and report your closest result (save it as ${S}/ADDR.c) and what differs. A retry pass handles near-misses later.
   Attempt every function you claim, whatever its size; never claim more than you will attempt. Don't claim past the limit.

C rules:
- One function per file plus #include "global.h" (u8/u16/u32/s8/s16/s32) and needed extern declarations / struct definitions.
- Name externals by address: functions sub_XXXXXXXX (bl targets), data gUnk_XXXXXXXX (addresses from the literal pool; IWRAM/EWRAM/ROM). Hardware registers: ((volatile u16 *)0x04000XXX) casts or gUnk_04000XXX.
${args.projectNotes || ''}
- Big functions (over ~2KB) use bl as a long branch internally. If the claimed range looks truncated (it ends in the middle of code, or the next src file starts later than the claimed end), report 'bogus start at XXXXXXXX' for each fake split point in notes.
- Shared globals: before declaring a global (e.g. a gUnk_03xxxxxx state pointer), grep src/*.c and reuse the same declaration/struct the neighbors use, so files can merge. If yours must differ, that's OK (it goes in its own file).
- Function-end padding is handled (both ROM and build zero-pad); check_func.py is authoritative.
- Some files were built with old_agbcc. The tell: a leaf that ends in a bare "bx lr" (no push {lr}) while it has a conditional branch or uses ip; new agbcc always pushes lr there. If neighbours in the same range need agbcc, it's a file boundary (report the missed start). If stuck, try CC1=${REPO}/tools/agbcc/bin/old_agbcc python3 tools/check_func.py ... ; if that MATCHES, integrate with the same prefix: CC1=${REPO}/tools/agbcc/bin/old_agbcc tools/integrate_one.sh ...
- If the claimed range clearly contains two functions (an unlabeled function start after a return), put both in the one file if they match with one compiler. If they need different compilers, don't integrate: report "missed start at XXXXXXXX" in notes.
- No inline asm, no asm(), no naked functions. Pure C.
- agbcc tips: statement order, integer types (lsl+lsr = zero-extend, lsl+asr = sign-extend), temporaries, loop forms, if/else vs ternary, declaration order affects register allocation; inline expressions vs locals can swap registers.
- Scratch files: the final attempt goes in ${S}/ADDR.c; put any other experiment files in a private subdirectory ${S}/a${i}/ (generic names like t.c or base.c in the shared dir get overwritten by other agents).
- Keep brute-force searches small (under ~40 variants per command) and run them in the foreground; never leave a background job running and wait on it.

You are agent ${i}. Return every function you claimed.`

// args.configs: optional per-agent [{model, effort}] for A/B tests; else args.model for all
const cfg = i => (args.configs && args.configs[i]) || (args.model ? { model: args.model } : {})
const tag = c => [c.model || 'default', c.effort || 'default'].join('-')
const results = await parallel(Array.from({ length: args.agents }, (_, i) => () =>
  agent(prompt(i), { label: `stream-${i}-${tag(cfg(i))}`, phase: 'Decompile', schema: RESULT, ...cfg(i) })
    .then(r => r && { ...r, functions: r.functions.map(f => ({ ...f, agent: i, config: tag(cfg(i)) })) })))
const fns = results.filter(Boolean).flatMap(r => r.functions)
log(`${fns.filter(f => f.committed).length}/${fns.length} claimed functions committed`)
return fns