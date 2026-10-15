#!/usr/bin/env node
// hot-seat helper: mode detection, session state, round validation, page build, ledger export.
// Zero dependencies (Node >= 18). The skill's SKILL.md says when to call each command.
//
//   node hot-seat.mjs preflight [--cwd DIR]
//   node hot-seat.mjs init      [--cwd DIR] [--mode me|docs] [--slug NAME]
//   node hot-seat.mjs record    --state FILE --poll FILE
//   node hot-seat.mjs next      --state FILE --patch FILE
//   node hot-seat.mjs ledger    --state FILE [--out FILE | --brief]
//   node hot-seat.mjs check     --state FILE
//   node hot-seat.mjs build     --state FILE   (re-render the page from state)

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SHELL = path.join(HERE, '..', 'assets', 'hot-seat.html');

// ---------------------------------------------------------------- contract
// Canonical rule list. The page renders it verbatim on its Contract tab, so the user can
// see which rules this session runs under (the "did the skill load its dependencies" check).
const CONTRACT = {
  version: '1',
  rules: [
    { id: 'I1', group: 'Interview', src: 'grilling', text: 'Interview until we share one understanding. The decisions are yours; I never decide for you.' },
    { id: 'I2', group: 'Interview', src: 'grilling', text: 'The plan is a design tree: every decision branches into the decisions that hang off it.' },
    { id: 'I3', group: 'Interview', src: 'grilling', text: 'Each round is the whole frontier: every decision whose prerequisites are settled, asked at once. A question that depends on another open one waits for a later round.' },
    { id: 'I4', group: 'Interview', src: 'grilling', text: 'Every question is numbered and carries my recommended answer and the reason for it.' },
    { id: 'I5', group: 'Interview', src: 'grilling', text: 'Facts are my job, never yours: I look them up (or send a sub-agent) instead of asking. A running lookup only blocks the questions downstream of it.' },
    { id: 'I6', group: 'Interview', src: 'grilling', text: 'I wait for your answers, then recompute the frontier. Done when the frontier is empty, nothing silently assumed. I do not act until you confirm the shared understanding.' },
    { id: 'S1', group: 'Steering', src: 'aihero.dev/skills-grill-me', text: 'Push back. Scope corrections and pushback are input, and I acknowledge them next round. "I don\'t know" is a real answer. Agreeing with everything means you did not need a session.' },
    { id: 'S2', group: 'Steering', src: 'aihero.dev/skills-grill-me', text: 'Some questions cannot be answered by talking (how it should feel, one form or three pages). Flag them "needs a prototype" instead of guessing.' },
    { id: 'D1', group: 'Paper trail (codebase mode)', src: 'domain-modeling', text: 'I challenge your terms against CONTEXT.md, sharpen fuzzy language, stress-test with concrete scenarios, and check your claims against the code.' },
    { id: 'D2', group: 'Paper trail (codebase mode)', src: 'domain-modeling', text: 'A term is written to CONTEXT.md the moment it resolves, not batched. CONTEXT.md is a glossary only: no implementation detail, no spec. Files are created lazily.' },
    { id: 'D3', group: 'Paper trail (codebase mode)', src: 'domain-modeling', text: 'An ADR is offered only when all three hold: hard to reverse, surprising without context, a real trade-off. Otherwise none.' },
    { id: 'L1', group: 'Ledger', src: 'hot-seat', text: 'Every answer of every round stays on this page and is exported at the end as a decisions ledger you can hand to a spec. Stateless mode writes nothing into your workspace.' },
  ],
};

// ---------------------------------------------------------------- helpers
const die = (msg, code = 1) => { console.error(msg); process.exit(code); };
const readJSON = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const writeAtomic = (p, s) => { const t = p + '.tmp'; fs.writeFileSync(t, s); fs.renameSync(t, p); };
const writeJSON = (p, o) => writeAtomic(p, JSON.stringify(o, null, 2) + '\n');
// shell: true on Windows so npm-style .cmd shims (lavish-axi.cmd, npx.cmd) resolve
const sh = (cmd, args, opts = {}) => spawnSync(cmd, args, { encoding: 'utf8', timeout: 15000, shell: process.platform === 'win32', ...opts });
// Read a text file that a shell may have redirected as UTF-16 (Windows PowerShell 5 `>`) or with a BOM.
function readTextFile(p) {
  const b = fs.readFileSync(p);
  if (b.length >= 2 && b[0] === 0xff && b[1] === 0xfe) return b.slice(2).toString('utf16le');
  if (b.length >= 3 && b[0] === 0xef && b[1] === 0xbb && b[2] === 0xbf) return b.slice(3).toString('utf8');
  return b.toString('utf8');
}
const now = () => new Date().toISOString();
const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);

function parseArgs(argv) {
  const a = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const t = argv[i];
    if (t.startsWith('--')) {
      const k = t.slice(2);
      const v = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
      a[k] = v;
    } else a._.push(t);
  }
  return a;
}

const SKIP_DIRS = new Set(['node_modules', '.git', '.next', 'dist', 'build', '.lavish', '.claude', '.agents', '.github', '.scratch', '.venv', 'venv', 'vendor', 'target', '.turbo', 'coverage']);
const SRC_EXT = /\.(ts|tsx|js|jsx|mjs|cjs|py|go|rs|java|kt|cs|rb|php|swift|c|cc|cpp|h|hpp|scala|sql|sh|vue|svelte|dart|lua|ex|exs|zig)$/i;

function walk(root, visit, { maxDepth = 6, maxFiles = 20000 } = {}) {
  let seen = 0;
  const rec = (dir, depth) => {
    if (depth > maxDepth || seen > maxFiles) return;
    let ents;
    try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const e of ents) {
      if (e.isDirectory()) { if (!SKIP_DIRS.has(e.name)) rec(path.join(dir, e.name), depth + 1); }
      else if (e.isFile()) { seen++; visit(path.join(dir, e.name)); }
    }
  };
  rec(root, 0);
}

// ---------------------------------------------------------------- preflight
function detect(cwd) {
  const g = sh('git', ['rev-parse', '--show-toplevel'], { cwd });
  const gitRoot = g.status === 0 ? g.stdout.trim() : null;
  const root = gitRoot || cwd;
  const contextFiles = [];
  for (const base of new Set([cwd, root])) {
    for (const f of ['CONTEXT-MAP.md', 'CONTEXT.md']) {
      const p = path.join(base, f);
      if (fs.existsSync(p) && !contextFiles.includes(p)) contextFiles.push(p);
    }
  }
  let srcCount = 0;
  if (gitRoot) {
    const ls = sh('git', ['ls-files'], { cwd: root, maxBuffer: 64 * 1024 * 1024 });
    if (ls.status === 0) srcCount = ls.stdout.split('\n').filter((f) => SRC_EXT.test(f)).length;
  } else {
    walk(cwd, (f) => { if (SRC_EXT.test(f)) srcCount++; }, { maxDepth: 4 });
  }
  const signals = [];
  if (gitRoot) signals.push(`git repository at ${gitRoot}`); else signals.push('not inside a git repository');
  signals.push(`${srcCount} source file${srcCount === 1 ? '' : 's'}`);
  signals.push(contextFiles.length ? `domain docs present: ${contextFiles.map((f) => path.relative(root, f) || f).join(', ')}` : 'no CONTEXT.md / CONTEXT-MAP.md');
  const docs = contextFiles.length > 0 || (!!gitRoot && srcCount > 0);
  const reason = docs
    ? (contextFiles.length ? 'A CONTEXT.md / CONTEXT-MAP.md is present' : 'A git repository with source files')
    : (gitRoot ? 'A git repository with no source files and no CONTEXT.md' : 'No codebase here: not a git repository, no source files, no CONTEXT.md');
  return { mode: docs ? 'docs' : 'me', reason, signals, gitRoot, root, contextFiles, srcCount };
}

function findLavish() {
  const v = sh('lavish-axi', ['--version']);
  if (v.status === 0) return { runner: 'lavish-axi', verified: true, version: (v.stdout || '').trim() };
  const n = sh('npx', ['--no-install', 'lavish-axi', '--version'], { timeout: 20000 });
  if (n.status === 0) return { runner: 'npx --no-install lavish-axi', verified: true, version: (n.stdout || '').trim() };
  const npx = sh('npx', ['--version']);
  if (npx.status === 0) return { runner: 'npx -y lavish-axi', verified: false, note: 'not installed; would be fetched from npm on first use (needs network). If the first open fails, use the chat fallback.' };
  return { runner: null, verified: false, note: 'lavish-axi not found and npx unavailable: use the chat fallback' };
}

function findUpstream(cwd, root) {
  const home = os.homedir();
  const dirs = [];
  for (const b of new Set([cwd, root])) for (const d of ['.claude/skills', '.agents/skills', '.github/skills']) dirs.push(path.join(b, d));
  for (const d of ['.claude/skills', '.agents/skills', '.copilot/skills']) dirs.push(path.join(home, d));
  const found = [];
  for (const name of ['grilling', 'domain-modeling']) {
    for (const d of dirs) {
      const p = path.join(d, name, 'SKILL.md');
      if (fs.existsSync(p)) { found.push({ name, path: p }); break; }
    }
  }
  return found;
}

function preflight(args) {
  const cwd = path.resolve(args.cwd || process.cwd());
  const d = detect(cwd);
  const ignored = d.gitRoot ? sh('git', ['check-ignore', '-q', '.lavish'], { cwd: d.root }).status === 0 : null;
  const out = {
    cwd, mode: d.mode, reason: d.reason, signals: d.signals,
    repoRoot: d.root, gitRoot: d.gitRoot, contextFiles: d.contextFiles,
    lavish: findLavish(),
    upstream: findUpstream(cwd, d.root),
    lavishDirIgnored: ignored,
    node: process.version,
    contract: { source: 'inline', version: CONTRACT.version, rules: CONTRACT.rules.length },
    note: 'upstream skills are optional: the contract is inline in SKILL.md and on the page Contract tab',
  };
  console.log(JSON.stringify(out, null, 2));
}

// ---------------------------------------------------------------- docs snapshot + diff
function isDocFile(rel) {
  const b = path.basename(rel);
  return b === 'CONTEXT.md' || b === 'CONTEXT-MAP.md' || /(^|\/)docs\/adr\/[^/]+\.md$/.test(rel.split(path.sep).join('/'));
}
function snapshotDocs(root) {
  const snap = {};
  walk(root, (f) => {
    const rel = path.relative(root, f);
    if (isDocFile(rel)) snap[rel.split(path.sep).join('/')] = fs.readFileSync(f, 'utf8');
  });
  return snap;
}
function lineDiff(a, b, ctx = 2) {
  const A = a.split('\n'), B = b.split('\n');
  const n = A.length, m = B.length;
  if (n * m > 4_000_000) return { text: '(file too large to diff line by line)', added: m, removed: n };
  const L = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) L[i][j] = A[i] === B[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  const ops = [];
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (A[i] === B[j]) { ops.push([' ', A[i]]); i++; j++; }
    else if (L[i + 1][j] >= L[i][j + 1]) ops.push(['-', A[i++]]);
    else ops.push(['+', B[j++]]);
  }
  while (i < n) ops.push(['-', A[i++]]);
  while (j < m) ops.push(['+', B[j++]]);
  const keep = new Array(ops.length).fill(false);
  ops.forEach(([t], k) => { if (t !== ' ') for (let x = Math.max(0, k - ctx); x <= Math.min(ops.length - 1, k + ctx); x++) keep[x] = true; });
  const lines = [];
  let skipped = false;
  ops.forEach(([t, s], k) => {
    if (keep[k]) { if (skipped) lines.push('@@'); lines.push(t + s); skipped = false; } else skipped = true;
  });
  return { text: lines.join('\n'), added: ops.filter((o) => o[0] === '+').length, removed: ops.filter((o) => o[0] === '-').length };
}
function diffSnapshots(prev, cur) {
  const writes = [];
  const files = new Set([...Object.keys(prev), ...Object.keys(cur)]);
  for (const f of [...files].sort()) {
    const kind = /(^|\/)docs\/adr\//.test(f) ? 'adr' : 'glossary';
    if (!has(prev, f)) {
      const lines = cur[f].split('\n');
      writes.push({ file: f, kind, status: 'added', added: lines.length, removed: 0, diff: lines.slice(0, 80).map((l) => '+' + l).join('\n') + (lines.length > 80 ? `\n@@ (+${lines.length - 80} more lines)` : '') });
    } else if (!has(cur, f)) writes.push({ file: f, kind, status: 'deleted', added: 0, removed: prev[f].split('\n').length, diff: '' });
    else if (prev[f] !== cur[f]) { const d = lineDiff(prev[f], cur[f]); writes.push({ file: f, kind, status: 'modified', added: d.added, removed: d.removed, diff: d.text }); }
  }
  return writes;
}

// ---------------------------------------------------------------- state
const statePathOf = (args) => path.resolve(args.state || die('--state FILE required'));
const loadState = (args) => { const p = statePathOf(args); return { p, s: readJSON(p) }; };
const snapPathOf = (s) => path.join(s.workdir, 'docs-snapshot.json');
const htmlPathOf = (s) => s.htmlPath || path.join(s.workdir, 'hot-seat.html');

function intakeQuestions(s) {
  const detectedLabel = s.mode.detected === 'docs' ? 'codebase' : 'stateless';
  return [
    { id: 'Q1', node: 'd0', kind: 'free', required: true, noRecommendation: true, prefill: s.invokedTopic || '', title: 'What do you want to put in the hot seat?',
      body: 'A plan, a decision, a feature, a piece of writing, a business call. Loose is fine: vagueness is what this session eats. A sentence or two.' },
    { id: 'Q2', node: 'dm', kind: 'choice', title: 'Which kind of session is this?',
      body: `I looked at where I was started: ${s.mode.signals.join('; ')}.\n\n**Codebase** also keeps a paper trail: resolved terms go into CONTEXT.md as they resolve, hard decisions become ADRs under docs/adr/. **Stateless** writes nothing into your workspace: terms and decisions live on this page and in the exported ledger.`,
      choices: [
        { id: 'docs', label: 'Codebase session', detail: 'Read the code, challenge my terms against CONTEXT.md, write terms and ADRs as they resolve.' },
        { id: 'me', label: 'Stateless session', detail: 'No repository involved (or I do not want files touched). Nothing is written to the workspace.' },
      ],
      recommended: s.mode.detected, why: `${s.mode.reason}, so this reads as a ${detectedLabel} session.` },
    { id: 'Q3', node: 'd0', kind: 'free', noRecommendation: true, title: 'Anything I should know before the first real round?',
      body: 'Scope limits, what is already decided, files or docs to read, who this is for. Optional.' },
  ];
}

function init(args) {
  const cwd = path.resolve(args.cwd || process.cwd());
  const d = detect(cwd);
  const detected = d.mode;
  const mode = args.mode === 'me' || args.mode === 'docs' ? args.mode : detected;
  const slug = String(args.slug || new Date().toISOString().replace(/[-:T]/g, '').slice(0, 12));
  const session = crypto.randomBytes(3).toString('hex');
  const workdir = mode === 'docs'
    ? path.join(d.root, '.lavish', `hot-seat-${slug}`)
    : path.join(os.tmpdir(), `hot-seat-${slug}-${session}`);
  fs.mkdirSync(workdir, { recursive: true });
  const s = {
    schema: 'hot-seat/1', session, createdAt: now(), updatedAt: now(),
    topic: '', title: '', invokedTopic: args.topic && args.topic !== true && !args.chat ? String(args.topic) : '', theme: 'dim',
    mode: { value: mode, detected, reason: d.reason, signals: d.signals, overridden: mode !== detected },
    repo: { cwd, root: d.root, gitRoot: d.gitRoot, contextFiles: d.contextFiles.map((f) => path.relative(d.root, f) || f) },
    contract: { source: 'inline', version: CONTRACT.version, rules: CONTRACT.rules, upstream: findUpstream(cwd, d.root) },
    lavish: findLavish(),
    workdir, htmlPath: args.html && args.html !== true ? path.resolve(args.html) : null, round: 1, status: 'asking',
    tree: [
      { id: 'd0', parent: null, title: 'What are we deciding?', state: 'frontier' },
      { id: 'dm', parent: 'd0', title: 'Session mode', state: 'frontier' },
    ],
    facts: [], glossary: [], adrs: [], corrections: [],
    rounds: [],
  };
  s.rounds.push({ n: 1, note: 'First page. Two things before any interview: what to grill, and whether this touches a codebase. Steer any time, in the steer box or by annotating the page.', questions: intakeQuestions(s), writes: [], warnings: [], builtAt: now() });
  if (mode === 'docs') fs.writeFileSync(snapPathOf(s), JSON.stringify(snapshotDocs(d.root)));
  if (args.chat && args.topic && args.topic !== true) {
    // chat fallback: the intake happened in chat, so pre-answer it and skip the page round
    const r = s.rounds[0];
    r.questions.find((q) => q.id === 'Q1').answer = { text: String(args.topic), choice: null, choices: [], stance: 'own-words' };
    r.questions.find((q) => q.id === 'Q2').answer = { choice: mode, choices: [], text: '', stance: mode === detected ? 'agreed' : 'differed' };
    if (args.context && args.context !== true) r.questions.find((q) => q.id === 'Q3').answer = { text: String(args.context), choice: null, choices: [], stance: 'own-words' };
    intakeFollowUp(s, r, []);
    s.round = 1;
  }
  const p = path.join(workdir, 'state.json');
  if (s.htmlPath) fs.mkdirSync(path.dirname(s.htmlPath), { recursive: true });
  writeJSON(p, s);
  build(s);
  console.log(`session ${session} created (mode: ${mode}${mode !== detected ? `, overriding detected ${detected}` : ''})`);
  console.log(`state: ${p}`);
  console.log(`page:  ${htmlPathOf(s)}`);
  console.log(`lavish: ${s.lavish.runner || 'NOT AVAILABLE - use the chat fallback'}${s.lavish.verified ? '' : ' (unverified)'}`);
}

// ---------------------------------------------------------------- record (poll -> answers)
function extractPayloads(text) {
  const out = [];
  const re = /HOTSEAT:v1:([A-Za-z0-9+/=_-]+)/g;
  let m;
  while ((m = re.exec(text))) {
    try { out.push(JSON.parse(Buffer.from(m[1], 'base64').toString('utf8'))); } catch { /* ignore torn payload */ }
  }
  return out;
}
const arr = (x) => (Array.isArray(x) ? x : x == null || x === '' ? [] : [x]);
const sameSet = (a, b) => a.length === b.length && a.every((x) => b.includes(x));

function stanceOf(q, a) {
  if (!a) return 'open';
  if (a.skip) return 'skipped';
  if (a.dontKnow) return 'unsure';
  const chosen = arr(a.choices).length ? arr(a.choices) : arr(a.choice);
  const text = (a.text || '').trim();
  if (q.kind === 'confirm') return chosen.length ? 'answered' : 'open';
  if (q.kind === 'free') return text ? (q.recommended && text === String(q.recommended).trim() ? 'agreed' : 'own-words') : a.prototype ? 'prototype' : 'open';
  if (!chosen.length && !text) return a.prototype ? 'prototype' : 'open';
  if (!chosen.length) return 'own-words';
  const reco = arr(q.recommended);
  return sameSet(chosen, reco) ? 'agreed' : 'differed';
}

// Minimal reader for lavish-axi poll output (TOON). We only need: ended?, waiting?, and prompts that are not round payloads.
function readPoll(text) {
  const endedBy = (text.match(/ended_by:\s*(\S+)/) || [])[1];
  const ended = /session_ended:\s*true/.test(text) || /status:\s*ended/.test(text);
  const waiting = /status:\s*waiting/.test(text) || !text.trim();
  const others = [];
  const re = /^\s{2}"[^"]*","((?:[^"\\]|\\.)*)",(.*)$/gm;
  let m;
  while ((m = re.exec(text))) {
    let prompt = m[1];
    try { prompt = JSON.parse('"' + m[1] + '"'); } catch { /* keep raw */ }
    if (/HOTSEAT:v1:/.test(prompt)) continue;
    const rest = m[2].split(',');
    others.push({ prompt, tag: rest[rest.length - 2], text: (rest[rest.length - 1] || '').replace(/^"|"$/g, '') });
  }
  return { ended, endedBy, waiting, others };
}
function record(args) {
  const { p, s } = loadState(args);
  const pollText = readTextFile(path.resolve(args.poll || die('--poll FILE required')));
  const payloads = extractPayloads(pollText);
  const info = readPoll(pollText);
  const lines = [];
  if (info.ended && info.endedBy === 'agent') lines.push('SESSION ENDED by an AGENT (`lavish-axi end` or a server stop), not by the user. Nothing was lost: if you still need answers, reopen the page with `lavish-axi <page>` and poll again.');
  else if (info.ended) lines.push(`SESSION ENDED by the user (${info.endedBy || 'user'}): this is the last feedback. Do not poll again and do not reopen the page.`);
  if (info.waiting && !payloads.length && !info.others.length) {
    console.log('The poll returned no feedback (status: waiting / empty file). Re-run the poll; nothing is lost.');
    return;
  }
  for (const o of info.others) lines.push(`OTHER FEEDBACK (${o.tag || 'no tag'}${o.text ? ': ' + o.text : ''}) - treat as steering and answer it in your next \`note\`:\n      ${o.prompt.slice(0, 1200).replace(/\n/g, '\n      ')}`);
  if (!payloads.length) {
    console.log(lines.join('\n') || 'no hot-seat round payload in that poll output (plain chat or annotations only).');
    if (info.ended && info.endedBy !== 'agent') console.log('\nnext: stop polling. Print `ledger --brief` (NOT CONFIRMED header) and stop.');
    return;
  }
  for (const pl of payloads) {
    if (pl.session !== s.session) { lines.push(`skipped payload for another session (${pl.session})`); continue; }
    const r = s.rounds.find((x) => x.n === pl.round);
    if (!r) { lines.push(`skipped payload for unknown round ${pl.round}`); continue; }
    const stale = pl.round !== s.round;
    r.receivedAt = now();
    if (pl.steer && pl.steer.trim()) r.steer = (r.steer ? r.steer + '\n' : '') + pl.steer.trim();
    for (const a of pl.answers || []) {
      const q = r.questions.find((x) => x.id === a.id);
      if (!q) { lines.push(`skipped answer for unknown question ${a.id}`); continue; }
      q.answer = { choice: a.choice ?? null, choices: a.choices ?? [], text: a.text || '', dontKnow: !!a.dontKnow, prototype: !!a.prototype, skip: !!a.skip, at: now() };
      q.answer.stance = stanceOf(q, q.answer);
    }
    const c = {};
    for (const q of r.questions) { const st = q.answer ? q.answer.stance : 'open'; c[st] = (c[st] || 0) + 1; }
    lines.push(`recorded round ${pl.round}${pl.final === false ? ' (DRAFT: the user had not pressed send, e.g. Send & End)' : ''}${stale ? ' (STALE: not the current round)' : ''}: ${Object.entries(c).map(([k, v]) => `${v} ${k}`).join(', ')}`);
    for (const q of r.questions) {
      const a = q.answer || {};
      const lab = (id) => (q.choices || []).find((x) => x.id === id)?.label || id;
      const chosen = arr(a.choices).length ? arr(a.choices) : arr(a.choice);
      let line = `${q.id} [${a.stance || 'open'}] ${q.title}`;
      if (chosen.length) line += ` -> ${chosen.map((x) => `(${x}) ${lab(x)}`).join(' + ')}`;
      if (a.text) line += `\n      words: ${JSON.stringify(a.text)}`;
      if (a.prototype) line += '\n      flag: needs a prototype';
      if (a.skip) line += '\n      flag: OUT OF SCOPE for the user (park the node, reason: out of scope)';
      lines.push('  ' + line);
    }
    if (r.steer) lines.push(`  steer: ${JSON.stringify(r.steer)}`);
    if (pl.round === 1) intakeFollowUp(s, r, lines);
  }
  s.updatedAt = now();
  writeJSON(p, s);
  console.log(lines.join('\n'));
  const nextQ = s.rounds.reduce((n, r) => n + r.questions.length, 0) + 1;
  console.log(`the next round's questions will be numbered from Q${nextQ}.`);
  const last = s.rounds[s.rounds.length - 1];
  const conf = last.questions.find((q) => q.kind === 'confirm');
  if (info.ended && info.endedBy !== 'agent') console.log('\nnext: stop polling. `ledger --brief` and print it in chat (it carries a NOT CONFIRMED header unless a confirm was answered yes).');
  else if (conf && conf.answer) console.log(conf.answer.choice === 'yes' ? '\nnext: confirmed. Build `{"finish": true, "summary": "..."}`, then `ledger`, print it, `lavish-axi end`.' : '\nnext: NOT confirmed. Reopen the tree from what the user said (unsettle nodes, ask what is off), then `next`.');
  else console.log('\nnext: settle answered nodes (tree patch), park skipped / unsure / prototype ones, add follow-ups, do the paper trail in codebase mode, then `next`.');
}

function intakeFollowUp(s, r, lines) {
  const q1 = r.questions.find((q) => q.id === 'Q1'), q2 = r.questions.find((q) => q.id === 'Q2'), q3 = r.questions.find((q) => q.id === 'Q3');
  const topic = (q1?.answer?.text || '').trim();
  if (topic) {
    s.topic = topic;
    const n = s.tree.find((x) => x.id === 'd0');
    Object.assign(n, { state: 'settled', decision: `Topic: ${topic}${q3?.answer?.text ? ` | Context: ${q3.answer.text.trim()}` : ''}`, title: 'Topic and scope' });
  } else lines.push('  WARNING: Q1 (the topic) is empty. Ask again in the next round.');
  const mv = arr(q2?.answer?.choice)[0];
  if (mv === 'docs' || mv === 'me') {
    if (mv !== s.mode.value) {
      s.mode.value = mv; s.mode.overridden = mv !== s.mode.detected;
      lines.push(`  MODE CHANGED to ${mv} (detected ${s.mode.detected}).`);
      if (mv === 'docs' && !fs.existsSync(snapPathOf(s))) fs.writeFileSync(snapPathOf(s), JSON.stringify(snapshotDocs(s.repo.root)));
    }
    const dm = s.tree.find((x) => x.id === 'dm');
    Object.assign(dm, { state: 'settled', decision: `Mode: ${mv === 'docs' ? 'codebase (writes CONTEXT.md / ADRs)' : 'stateless (writes nothing to the workspace)'}${s.mode.overridden ? ' - user overrode the detected mode' : ''}` });
  }
}

// ---------------------------------------------------------------- next (merge + validate + build)
function upsertBy(list, items, key) {
  for (const it of items || []) {
    const i = list.findIndex((x) => x[key] === it[key]);
    if (i >= 0) list[i] = { ...list[i], ...it }; else list.push({ ...it });
  }
}

function nodeSettledish(n) { return n && (n.state === 'settled' || n.state === 'parked'); }

function validateAndAdvance(s, patch) {
  const errors = [], warnings = [];
  const prevRound = s.rounds[s.rounds.length - 1];
  if (patch.answers && prevRound) {
    // chat fallback only: answers came as chat text, not through a page payload
    for (const [id, a] of Object.entries(patch.answers)) {
      const q = prevRound.questions.find((x) => x.id === id);
      if (!q) { errors.push(`answers: unknown question ${id}`); continue; }
      q.answer = { choice: a.choice ?? null, choices: a.choices ?? [], text: a.text || '', dontKnow: !!a.dontKnow, prototype: !!a.prototype, at: now() };
      q.answer.stance = stanceOf(q, q.answer);
    }
  }
  upsertBy(s.tree, patch.tree, 'id');
  upsertBy(s.facts, patch.facts, 'id');
  upsertBy(s.glossary, patch.glossary, 'term');
  for (const g of s.glossary) if (!['resolved', 'proposed', 'conflict', 'existing', 'rejected'].includes(g.status)) errors.push(`glossary "${g.term}": bad status "${g.status}" (resolved | proposed | conflict | existing | rejected)`);
  s.assumptions ||= [];
  for (const t of [...arr(patch.assumptions), ...arr(patch.confirm && patch.confirm.assumptions)]) s.assumptions.push({ round: s.round + 1, text: String(t) });
  upsertBy(s.adrs, patch.adrs, 'title');
  if (patch.corrections) s.corrections.push(...arr(patch.corrections).map((t) => ({ round: prevRound?.n, text: String(t) })));
  if (patch.topic) s.topic = patch.topic;
  if (patch.title) s.title = String(patch.title).slice(0, 80);
  if (!s.title && !patch.finish) errors.push('patch needs `title`: a short name for this topic (under 60 characters, your wording, no jargon the glossary rejects). The page header and the ledger heading use it.');
  if (patch.mode === 'docs' || patch.mode === 'me') { s.mode.value = patch.mode; s.mode.overridden = patch.mode !== s.mode.detected; }
  const byId = (id) => s.tree.find((n) => n.id === id);

  for (const n of s.tree) {
    if (!['settled', 'frontier', 'blocked', 'running', 'parked'].includes(n.state)) errors.push(`tree ${n.id}: bad state "${n.state}"`);
    if (n.parent && !byId(n.parent)) errors.push(`tree ${n.id}: unknown parent ${n.parent}`);
    for (const b of arr(n.blockedOn)) if (!byId(b)) errors.push(`tree ${n.id}: blockedOn unknown node ${b}`);
    if (n.state === 'settled' && !n.decision) errors.push(`tree ${n.id} "${n.title}": settled without a \`decision\` (state the decision precisely: numbers, ordering, negatives)`);
    if (n.state === 'parked' && !n.parkedReason) errors.push(`tree ${n.id} "${n.title}": parked without a \`parkedReason\``);
  }
  const running = new Set(s.facts.filter((f) => f.state === 'running').flatMap((f) => arr(f.feeds)));

  // previous round's answered questions must lead somewhere (settled, or a follow-up)
  const nextQs = arr(patch.questions);
  const nextNodes = new Set(nextQs.map((q) => q.node));
  if (prevRound) for (const q of prevRound.questions) {
    const a = q.answer;
    if (a && ['agreed', 'differed', 'own-words'].includes(a.stance)) {
      const n = byId(q.node);
      if (n && n.state === 'frontier' && !nextNodes.has(n.id)) warnings.push(`${q.id} was answered but node ${n.id} "${n.title}" is still frontier: settle it (with a decision) or ask a follow-up`);
    }
    if (a && a.stance === 'unsure') { const n = byId(q.node); if (n && n.state === 'frontier' && !nextNodes.has(n.id)) warnings.push(`${q.id} was "I don't know": ask a smaller question, send a fact-finder, or park node ${n.id}`); }
    if (a && a.stance === 'skipped') { const n = byId(q.node); if (n && n.state === 'frontier' && !nextNodes.has(n.id)) warnings.push(`${q.id} was marked out of scope by the user: park node ${n.id} with parkedReason "out of scope (user)" and drop its children`); }
    if (a && a.stance === 'prototype') { const n = byId(q.node); if (n && n.state === 'frontier' && !nextNodes.has(n.id)) warnings.push(`${q.id} was flagged "needs a prototype": park node ${n.id} with a parkedReason, or build the prototype`); }
  }

  const round = { n: s.round + 1, note: patch.note || '', questions: [], writes: [], warnings, builtAt: now() };
  if (patch.confirm) {
    const open = s.tree.filter((n) => !nodeSettledish(n));
    if (open.length) errors.push(`cannot confirm: ${open.length} node(s) not settled or parked (${open.map((n) => n.id).join(', ')}). The frontier is not empty.`);
    if (nextQs.length) errors.push('a confirm round takes no other questions');
    round.summary = patch.confirm.summary || '';
    if (!round.summary) errors.push('confirm.summary is required: state the shared understanding in your own words');
    round.questions = [{
      id: `Q${(s.rounds.flatMap((r) => r.questions).length) + 1}`, node: 'd0', kind: 'confirm', noRecommendation: true,
      title: 'Is this the shared understanding?',
      body: 'Read the summary and the ledger. Confirm only if you could defend each decision to someone who was not here. Otherwise say what is off.',
      choices: [{ id: 'yes', label: 'Yes, we are aligned', detail: 'End the session. Nothing has been acted on.' }, { id: 'no', label: 'Not yet', detail: 'Reopen the tree. Tell me what is wrong below.' }],
    }];
  } else {
    if (!nextQs.length && !patch.finish) errors.push('patch has no `questions`. If the frontier is empty use `confirm: {summary}`; if the session is confirmed use `finish: true`.');
    let counter = s.rounds.flatMap((r) => r.questions).length;
    for (const raw of nextQs) {
      const q = { kind: 'choice', ...raw };
      q.id = `Q${++counter}`;
      const where = `${q.id} "${q.title || '?'}"`;
      if (!q.title || !q.body) errors.push(`${where}: title and body are required`);
      const node = byId(q.node);
      if (!node) errors.push(`${where}: unknown node "${q.node}" (add it to the tree patch)`);
      else {
        const blockers = arr(node.blockedOn).filter((b) => !nodeSettledish(byId(b)));
        if (blockers.length) errors.push(`${where}: node ${node.id} depends on unsettled ${blockers.join(', ')}. It belongs to a later round.`);
        if (running.has(node.id)) errors.push(`${where}: node ${node.id} is fed by a fact-finder still running. Ask it after the fact lands.`);
      }
      if (q.kind === 'choice') {
        const ids = arr(q.choices).map((c) => c.id);
        if (ids.length < 2) errors.push(`${where}: a choice question needs at least 2 choices`);
        if (new Set(ids).size !== ids.length) errors.push(`${where}: duplicate choice ids`);
        for (const c of arr(q.choices)) if (!c.id || !c.label) errors.push(`${where}: every choice needs id and label`);
        if (!q.noRecommendation) {
          const reco = arr(q.recommended);
          if (!reco.length || !reco.every((r) => ids.includes(r))) errors.push(`${where}: \`recommended\` must name a choice id (${ids.join('/')}). Every question carries a recommendation.`);
          if (!q.why) errors.push(`${where}: \`why\` is required: the reason for the recommendation`);
        }
      } else if (q.kind === 'free') {
        if (!q.noRecommendation && (!q.recommended || !String(q.recommended).trim())) errors.push(`${where}: a free-text question needs a \`recommended\` answer text`);
        if (!q.noRecommendation && !q.why) errors.push(`${where}: \`why\` is required`);
      } else errors.push(`${where}: bad kind "${q.kind}"`);
      round.questions.push(q);
    }
    const ask = new Set(round.questions.map((q) => q.node));
    for (const n of s.tree) {
      if (ask.has(n.id) && n.state !== 'settled') n.state = 'frontier';
      if (n.state === 'frontier' && !ask.has(n.id) && !patch.finish) warnings.push(`node ${n.id} "${n.title}" is frontier but has no question this round: ask it or mark it blocked/running`);
      if (n.state === 'blocked' && arr(n.blockedOn).every((b) => nodeSettledish(byId(b))) && arr(n.blockedOn).length && !ask.has(n.id)) warnings.push(`node ${n.id} "${n.title}" is unblocked (all prerequisites settled) but not asked: the round must be the WHOLE frontier`);
    }
    if (s.tree.length > 40) warnings.push(`the tree has ${s.tree.length} nodes: past about 40 this is wayfinder-scale. Offer the user to split it and grill one slice`);
    if (round.questions.length > 12) warnings.push(`${round.questions.length} questions in one round is a lot: split the tree or trim the frontier`);
    if (patch.finish) {
      if (prevRound?.questions?.[0]?.kind !== 'confirm' || prevRound.questions[0].answer?.choice !== 'yes') errors.push('`finish` needs the user to have answered "yes" on a confirm round');
    }
  }

  // glossary / ADR consistency against the files on disk
  const docsMode = s.mode.value === 'docs';
  const snapPath = snapPathOf(s);
  const prevSnap = fs.existsSync(snapPath) ? JSON.parse(fs.readFileSync(snapPath, 'utf8')) : {};
  const curSnap = docsMode ? snapshotDocs(s.repo.root) : prevSnap;
  if (docsMode) {
    round.writes = diffSnapshots(prevSnap, curSnap);
    const ctxText = Object.entries(curSnap).filter(([f]) => /CONTEXT\.md$/.test(f)).map(([, t]) => t).join('\n');
    const termRe = (t) => new RegExp('\\*\\*' + String(t).replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\*\\*', 'i');
    const addedLines = [...s.rounds, round].flatMap((r) => (r.writes || []).filter((w) => w.kind === 'glossary').map((w) => w.diff)).join('\n').split('\n').filter((l) => l.startsWith('+')).join('\n');
    for (const g of s.glossary) {
      const inFile = termRe(g.term).test(ctxText);
      if (g.written && !inFile) errors.push(`glossary "${g.term}" is marked written but **${g.term}** is not in any CONTEXT.md`);
      else if (g.written && !g.edited && !termRe(g.term).test(addedLines)) errors.push(`glossary "${g.term}" is marked written but this session never added it (it was already there). Use status "existing"; if you edited its definition in place, add \`edited: true\`.`);
      if (g.status === 'existing' && !inFile) errors.push(`glossary "${g.term}" is marked existing but **${g.term}** is not in any CONTEXT.md`);
      if (g.status === 'resolved' && !g.written) warnings.push(`glossary "${g.term}" is resolved but not written to CONTEXT.md: write it now (inline, not batched)`);
    }
    const addedAdrs = round.writes.filter((w) => w.kind === 'adr' && w.status === 'added').map((w) => w.file);
    for (const f of addedAdrs) {
      const rec = s.adrs.find((a) => a.file === f);
      if (!rec) errors.push(`ADR file ${f} was written but has no \`adrs\` record with its three gates`);
    }
    for (const a of s.adrs) {
      const gates = a.gates || {};
      const met = ['hardToReverse', 'surprising', 'tradeoff'].every((k) => gates[k] && gates[k].met === true);
      a.allGates = met;
      if (a.status === 'written' && !met) errors.push(`ADR "${a.title}" is marked written but not all three gates are met (${['hardToReverse', 'surprising', 'tradeoff'].filter((k) => !(gates[k] && gates[k].met)).join(', ')}). Delete the file or drop the ADR.`);
      if (a.status === 'written' && a.file && !curSnap[a.file]) errors.push(`ADR "${a.title}" points at ${a.file} which does not exist`);
    }
  } else {
    if (s.glossary.some((g) => g.written || g.status === 'existing')) errors.push('stateless mode: there is no CONTEXT.md, so no glossary term can be `written` or `existing`');
    for (const a of s.adrs) if (a.status === 'written') errors.push(`stateless mode: ADR "${a.title}" cannot be written`);
    for (const g of s.glossary) if (g.status === 'resolved') g.session = true;
  }

  if (errors.length) return { errors, warnings };
  s.rounds.push(round);
  s.round = round.n;
  s.status = patch.confirm ? 'confirming' : patch.finish ? 'done' : 'asking';
  if (patch.finish) { s.rounds[s.rounds.length - 1].questions = []; s.rounds[s.rounds.length - 1].summary = patch.summary || 'Session confirmed.'; }
  if (docsMode) fs.writeFileSync(snapPath, JSON.stringify(curSnap));
  return { errors, warnings, round };
}

function next(args) {
  const { p, s } = loadState(args);
  const patch = readJSON(path.resolve(args.patch || die('--patch FILE required')));
  const before = JSON.stringify(s);
  const snap = fs.existsSync(snapPathOf(s)) ? fs.readFileSync(snapPathOf(s), 'utf8') : null;
  const res = validateAndAdvance(s, patch);
  if (res.errors.length) {
    if (snap !== null) fs.writeFileSync(snapPathOf(s), snap);
    console.error('REFUSED. The round was not built (nothing was changed):\n- ' + res.errors.join('\n- '));
    if (res.warnings.length) console.error('\nwarnings:\n- ' + res.warnings.join('\n- '));
    process.exit(2);
  }
  s.updatedAt = now();
  build(s); // page first, state second: a watcher of state.json never sees a round whose page is not ready
  writeJSON(p, s);
  void before;
  const r = res.round;
  const c = {};
  for (const n of s.tree) c[n.state] = (c[n.state] || 0) + 1;
  console.log(`round ${r.n} built: ${r.questions.length} question(s)${r.questions.length ? ` (${r.questions[0].id}-${r.questions[r.questions.length - 1].id})` : ''}, status ${s.status}`);
  console.log(`tree: ${s.tree.length} nodes (${Object.entries(c).map(([k, v]) => `${v} ${k}`).join(', ')})`);
  if (r.writes.length) console.log('written to the workspace: ' + r.writes.map((w) => `${w.file} (${w.status} +${w.added} -${w.removed})`).join(', '));
  if (res.warnings.length) console.log('warnings (shown on the page too):\n- ' + res.warnings.join('\n- '));
  console.log(`page: ${htmlPathOf(s)}`);
}

// ---------------------------------------------------------------- ledger
function ledgerMarkdown(s) {
  const L = [];
  const qs = s.rounds.flatMap((r) => r.questions.map((q) => ({ ...q, round: r.n })));
  const settled = s.tree.filter((n) => n.state === 'settled' && n.id !== 'dm');
  const parked = s.tree.filter((n) => n.state === 'parked');
  const open = s.tree.filter((n) => !['settled', 'parked'].includes(n.state));
  const confirmed = s.status === 'done' || s.rounds.some((r) => r.questions.some((q) => q.kind === 'confirm' && q.answer?.choice === 'yes'));
  L.push(`# Decisions ledger: ${s.title || (s.topic ? s.topic.slice(0, 70) : '(topic not set)')}`, '');
  L.push(`Source: hot-seat session ${s.session} - mode: ${s.mode.value === 'docs' ? 'codebase' : 'stateless'} - ${s.rounds.length} round(s) - ${confirmed ? 'shared understanding CONFIRMED by the user' : 'NOT CONFIRMED (session ended before the user confirmed: treat as a draft)'}`, '');
  const labelOf = (q, id) => (q.choices || []).find((c) => c.id === id)?.label || id;
  L.push('## Settled decisions', '');
  if (!settled.length) L.push('_None yet._', '');
  settled.forEach((n) => {
    L.push(`### ${n.id}. ${n.title}`, '', `- Decision: ${n.decision}`);
    for (const q of qs.filter((x) => x.node === n.id && x.answer && x.kind !== 'confirm')) {
      const a = q.answer;
      const chosen = arr(a.choices).length ? arr(a.choices) : arr(a.choice);
      const parts = [];
      if (chosen.length) parts.push(`chose ${chosen.map((c) => `"${labelOf(q, c)}"`).join(' + ')}`);
      if (a.text) parts.push(`said: "${a.text.replace(/\n/g, ' ')}"`);
      if (a.dontKnow) parts.push('said "I don\'t know"');
      if (a.prototype) parts.push('flagged: needs a prototype');
      const reco = arr(q.recommended).map((r) => labelOf(q, r)).join(' + ');
      L.push(`- ${q.id} (round ${q.round}): ${parts.join('; ') || 'no answer'}${q.kind === 'choice' && reco ? ` - recommended was "${reco}" (${a.stance})` : ''}`);
      const alts = arr(q.choices).filter((c) => !chosen.includes(c.id));
      if (q.kind === 'choice' && alts.length) L.push(`- Alternatives not taken: ${alts.map((c) => c.label).join('; ')}`);
    }
    L.push('');
  });
  if (parked.length) { L.push('## Parked (not decided)', ''); for (const n of parked) L.push(`- ${n.id}. ${n.title}: ${n.parkedReason}`); L.push(''); }
  if (open.length) { L.push('## Still open (session ended with these unvisited)', ''); for (const n of open) L.push(`- ${n.id}. ${n.title} (${n.state})`); L.push(''); }
  if (s.facts.length) { L.push('## Facts established by lookup (never asked)', ''); for (const f of s.facts) L.push(`- ${f.title}: ${f.state === 'done' ? f.result : '(lookup did not finish)'}`); L.push(''); }
  if (s.corrections.length) { L.push('## Corrections and pushback from the user', ''); for (const c of s.corrections) L.push(`- (round ${c.round}) ${c.text}`); L.push(''); }
  const steers = s.rounds.filter((r) => r.steer);
  if (steers.length) { L.push('## Steering, verbatim', ''); for (const r of steers) L.push(`- (round ${r.n}) "${r.steer.replace(/\n/g, ' ')}"`); L.push(''); }
  if (s.glossary.length) {
    L.push(s.mode.value === 'docs' ? '## Glossary' : '## Terms resolved this session (stateless: not written anywhere)', '');
    const tag = (g) => (g.status === 'existing' ? ' [already in CONTEXT.md, unchanged]' : g.status === 'rejected' ? ' [considered, not added]' : g.status === 'conflict' ? ' [CONFLICT, unresolved]' : g.status === 'proposed' ? ' [proposed]' : s.mode.value === 'docs' ? (g.written ? ` [written to ${g.file || 'CONTEXT.md'}]` : ' [not written]') : '');
    for (const g of s.glossary) L.push(`- **${g.term}**${g.fr ? ` (fr: ${g.fr})` : ''}: ${g.definition}${g.avoid && g.avoid.length ? ` _Avoid_: ${g.avoid.join(', ')}` : ''}${tag(g)}${g.note ? ` - ${g.note}` : ''}`);
    L.push('');
  }
  if (s.adrs.length) {
    L.push(s.mode.value === 'docs' ? '## ADRs' : '## ADR candidates (stateless: none written)', '');
    for (const a of s.adrs) {
      const g = a.gates || {};
      const mark = (k) => (g[k] && g[k].met ? 'yes' : 'no');
      L.push(`- ${a.title}: ${a.status}${a.file ? ` (${a.file})` : ''}${a.skipReason ? ` - skipped${a.skippedBy ? ' by ' + a.skippedBy : ''}: ${a.skipReason}` : ''} - agent's gate assessment: hard to reverse ${mark('hardToReverse')}, surprising without context ${mark('surprising')}, real trade-off ${mark('tradeoff')}`);
    }
    L.push('');
  }
  if ((s.assumptions || []).length) { L.push('## Derived by the agent, not said by the user (check these)', ''); for (const a of s.assumptions) L.push(`- (round ${a.round}) ${a.text}`); L.push(''); }
  const conf = [...s.rounds].reverse().find((r) => r.summary && r.questions.some((q) => q.kind === 'confirm'));
  if (conf) { L.push('## Shared understanding (agent summary shown at the confirm round)', '', conf.summary, ''); }
  const writes = s.rounds.flatMap((r) => r.writes.map((w) => ({ ...w, round: r.n })));
  if (writes.length) { L.push('## Files written to the workspace', ''); for (const w of writes) L.push(`- (round ${w.round}) ${w.file}: ${w.status} +${w.added} -${w.removed}`); L.push(''); }
  L.push('---', 'Hand this whole block to whatever comes next (a spec, tickets, a plan, a memo). Re-read the result against these answers: precise answers get softened downstream.');
  return L.join('\n');
}

function ledgerBrief(s, fullPath) {
  const confirmed = s.status === 'done' || s.rounds.some((r) => r.questions.some((q) => q.kind === 'confirm' && q.answer?.choice === 'yes'));
  const L = [`# Decisions ledger (brief): ${s.title || s.topic.slice(0, 70)}`, `${s.mode.value === 'docs' ? 'codebase' : 'stateless'} session, ${s.rounds.length} round(s), ${confirmed ? 'CONFIRMED by the user' : 'NOT CONFIRMED: treat as a draft'}`, ''];
  for (const n of s.tree.filter((x) => x.state === 'settled' && x.id !== 'dm')) L.push(`- ${n.id} ${n.title}: ${n.decision}`);
  const parked = s.tree.filter((x) => x.state === 'parked'), open = s.tree.filter((x) => !['settled', 'parked'].includes(x.state));
  if (parked.length) { L.push('', 'Parked:'); for (const n of parked) L.push(`- ${n.id} ${n.title}: ${n.parkedReason}`); }
  if (open.length) { L.push('', 'Still open:'); for (const n of open) L.push(`- ${n.id} ${n.title} (${n.state})`); }
  if ((s.assumptions || []).length) { L.push('', 'Inferred by the agent, not said by the user:'); for (const a of s.assumptions) L.push(`- ${a.text}`); }
  if (fullPath) L.push('', `Full ledger (quotes, alternatives, terms, ADRs, files): ${fullPath}, and the Ledger tab of the page.`);
  return L.join('\n');
}

function ledger(args) {
  const { s } = loadState(args);
  if (args.brief) { console.log(ledgerBrief(s, args.full && args.full !== true ? path.resolve(args.full) : path.join(s.workdir, 'ledger.md'))); return; }
  const md = ledgerMarkdown(s);
  if (args.out && args.out !== true) { fs.writeFileSync(path.resolve(args.out), md + '\n'); console.log(`ledger written to ${path.resolve(args.out)}`); } else console.log(md);
}

// ---------------------------------------------------------------- build
function build(s) {
  const shell = fs.readFileSync(SHELL, 'utf8');
  const view = { ...s, ledgerMd: ledgerMarkdown(s) };
  const json = JSON.stringify(view).replace(/</g, '\\u003c').replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029');
  const title = `hot-seat${(s.title || s.topic) ? ' - ' + (s.title || s.topic).slice(0, 60).replace(/[<>&"]/g, '') : ''}`;
  let html = shell.replace(/<script id="hs-state" type="application\/json">[\s\S]*?<\/script>/, () => `<script id="hs-state" type="application/json">${json}</script>`);
  html = html.replace(/<title>[\s\S]*?<\/title>/, () => `<title>${title}</title>`);
  html = html.replace(/<html lang="en" data-theme="[^"]*"/, () => `<html lang="en" data-theme="${s.theme || 'dim'}"`);
  writeAtomic(htmlPathOf(s), html);
}

function check(args) {
  const { s } = loadState(args);
  const r = s.rounds[s.rounds.length - 1];
  console.log(`session ${s.session}: round ${s.round}, status ${s.status}, mode ${s.mode.value}, ${s.tree.length} nodes, ${r.questions.length} question(s) in the current round`);
  console.log(`page: ${htmlPathOf(s)}`);
}

// ---------------------------------------------------------------- main
const args = parseArgs(process.argv.slice(2));
const cmd = args._[0];
const rebuild = (a) => { const { s } = loadState(a); build(s); console.log(`page rebuilt: ${htmlPathOf(s)}`); };
const table = { preflight, init, record, next, ledger, check, build: rebuild };
const USAGE = `usage: hot-seat.mjs <command> [options]
  preflight [--cwd DIR]                       mode detection, Lavish check, upstream skills found (JSON)
  init [--topic TEXT] [--slug NAME] [--mode me|docs] [--html PATH] [--chat]
                                              create the session and the first page (chat: pre-answered intake)
  record --state FILE --poll FILE             read a poll output: answers, other feedback, session-ended
  next --state FILE --patch FILE              validate + merge a patch, build the next round (refuses on contract breaks)
  ledger --state FILE [--brief | --out FILE]  decisions ledger (markdown), full or one line per decision
  build --state FILE                          re-render the page from state
  check --state FILE                          one-line status
(see SKILL.md and references/patch-format.md)`;
if (args.help) { console.log(USAGE); process.exit(0); }
if (!cmd || !table[cmd]) { console.error(USAGE); process.exit(1); }
table[cmd](args);
