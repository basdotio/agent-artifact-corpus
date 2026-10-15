#!/usr/bin/env node
// guiding-hand: recon brief, guide validation/rendering, and a post-implementation check.
// Zero dependencies, Node 18+. Output is compact: the orchestrator reads every byte.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

export const DIR = '.guiding-hand';
export const KINDS = ['bug', 'feature', 'change'];
export const ROLES = ['modify', 'create', 'test', 'check', 'reference'];
export const LEVELS = ['high', 'med', 'low'];
const MAX_FILES = 30;
const MAX_SNIPPET_LINES = 8;

const IGNORE_DIRS = new Set([
  'node_modules', '.git', 'dist', 'build', 'out', 'coverage', '.next', '.nuxt', '.turbo', '.cache', 'vendor',
  'target', '__pycache__', '.venv', 'venv', '.idea', '.vscode', DIR,
  '.claude', '.agents', '.codex', '.cursor', '.chaos-storm', '.signal-noise', '.devils-advocate',
]);
const TEXT = /\.(ts|tsx|js|jsx|mjs|cjs|py|go|rs|java|kt|rb|php|cs|swift|scala|vue|svelte|c|cc|cpp|h|hpp|sql|sh|ex|exs|dart|lua|prisma|graphql|gql|proto|json|ya?ml|toml|tf|md)$/;
const CODE = /\.(ts|tsx|js|jsx|mjs|cjs|py|go|rs|java|kt|rb|php|cs|swift|scala|vue|svelte|c|cc|cpp|h|hpp|sql|sh|ex|exs|dart|lua|prisma|graphql|proto|tf)$/;
const TEST = /(^|\/)(__tests__|tests?|spec)\/|\.(test|spec)\.[^.]+$|(^|\/)test_[^/]+\.py$|_test\.(go|py)$/;
const STOP = new Set(('a an and are as at be but by can do does for from has have how i if in into is it its make me my need needs '
  + 'new not now of on or our should so that the their them then there these this to up use using want we what when where which '
  + 'while who why will with would you your add adds adding fix fixes fixing bug bugs issue support supports change changes changing '
  + 'update updates feature code file files function functions work works working broken wrong instead also just like get set via '
  + 'please guide help me show walk through without writing write implement implementation able allow allows existing extend '
  + 'modify currently correctly properly same other some any all each every more less one two first last only still into '
  + 'well even though although show shows shown see seen able getting going always never sometimes').split(' '));

const toPosix = (p) => p.split(path.sep).join('/');
const trySh = (cmd, args, cwd) => { try { return execFileSync(cmd, args, { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], maxBuffer: 256 * 1024 * 1024 }); } catch { return null; } };
const readJson = (f, d = null) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return d; } };
const writeJson = (f, v) => { fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f, JSON.stringify(v, null, 2) + '\n'); };
const readText = (root, f) => { try { const s = fs.statSync(path.join(root, f)); return s.size > 400_000 ? '' : fs.readFileSync(path.join(root, f), 'utf8'); } catch { return ''; } };
export const slugify = (s) => String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40).replace(/-$/, '') || 'task';
const stem = (f) => path.posix.basename(f).replace(/\.[^.]+$/, '').replace(/\.(test|spec)$/, '').replace(/^test_|_test$/, '');
const lineCount = (t) => (t ? t.replace(/\n$/, '').split('\n').length : 0);

export function listFiles(root) {
  const out = trySh('git', ['ls-files', '-co', '--exclude-standard'], root);
  const keep = (f) => f && !f.split('/').some((seg) => IGNORE_DIRS.has(seg));
  if (out) { const files = out.split('\n').filter(keep); if (files.length) return files.sort(); }
  const files = [];
  const walk = (dir) => {
    for (const e of fs.readdirSync(path.join(root, dir), { withFileTypes: true })) {
      const p = dir ? `${dir}/${e.name}` : e.name;
      if (e.isDirectory()) { if (!IGNORE_DIRS.has(e.name)) walk(p); } else if (e.isFile()) files.push(p);
    }
  };
  walk('');
  return files.sort();
}

// ---------- terms ----------
/** Task text -> search terms: identifiers kept whole, plus meaningful words. */
export function extractTerms(task, extra = []) {
  const terms = new Set();
  const add = (t) => { const x = t.trim(); if (x.length >= 3 && !STOP.has(x.toLowerCase())) terms.add(x); };
  for (const m of String(task).matchAll(/`([^`]+)`/g)) add(m[1].replace(/[^\w./-]/g, ''));
  for (const w of String(task).split(/[^A-Za-z0-9_./-]+/)) {
    const clean = w.replace(/^[./-]+|[./-]+$/g, '');
    if (!clean) continue;
    if (/[a-z][A-Z]|_|\.[a-z]{1,4}$|^[A-Z]{2,}$/.test(clean)) add(clean); // identifier, file name or acronym: keep as written
    else add(clean.toLowerCase());
  }
  for (const e of extra) add(e);
  return [...terms].slice(0, 12);
}

/** Occurrences of a term. Short terms (<=4 chars) only count as whole words or camelCase parts, so "eur" never matches "Europe" or "neural". */
export function countTerm(text, term) {
  const esc = (x) => x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  if (term.length > 4) return (text.match(new RegExp(esc(term), 'gi')) || []).length;
  const low = term.toLowerCase();
  const cap = low[0].toUpperCase() + low.slice(1);
  const res = [new RegExp(`(?<![A-Za-z])${esc(low)}(?![a-z])`, 'gi'), new RegExp(`(?<=[a-z0-9])${esc(cap)}(?![a-z])`, 'g'), new RegExp(`(?<=[a-z0-9])${esc(low.toUpperCase())}(?![A-Z])`, 'g')];
  return res.reduce((n, re) => n + (text.match(re) || []).length, 0);
}

// ---------- import resolution ----------
const JS_EXT = ['.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.vue', '.svelte'];
const stripJsonComments = (s) => s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:"'])\/\/.*$/gm, '$1').replace(/,(\s*[}\]])/g, '$1');

function tsPaths(root, fromFile, cache) {
  let dir = path.dirname(path.join(root, fromFile));
  const key = dir;
  if (cache.has(key)) return cache.get(key);
  let found = null;
  while (!found) {
    for (const n of ['tsconfig.json', 'jsconfig.json']) {
      const cfg = (() => { try { return JSON.parse(stripJsonComments(fs.readFileSync(path.join(dir, n), 'utf8'))); } catch { return null; } })();
      const co = cfg?.compilerOptions;
      if (co?.paths || co?.baseUrl) { found = { base: path.join(dir, co.baseUrl || '.'), paths: co.paths || {} }; break; }
    }
    if (found || path.resolve(dir) === path.resolve(root)) break;
    const up = path.dirname(dir);
    if (up === dir) break;
    dir = up;
  }
  cache.set(key, found);
  return found;
}

function tryResolve(root, absNoExt, exts) {
  const cands = [absNoExt, ...exts.map((e) => absNoExt + e), ...exts.map((e) => path.join(absNoExt, 'index' + e))];
  if (/\.(m|c)?js$/.test(absNoExt)) { const b = absNoExt.replace(/\.(m|c)?js$/, ''); cands.push(...exts.map((e) => b + e)); }
  for (const c of cands) { try { if (fs.statSync(c).isFile()) return toPosix(path.relative(root, c)); } catch { /* next */ } }
  return null;
}

function workspacePackages(root, files) {
  const map = {};
  for (const f of files) {
    if (path.posix.basename(f) !== 'package.json' || f === 'package.json') continue;
    const pkg = readJson(path.join(root, f));
    if (pkg?.name) map[pkg.name] = { dir: path.posix.dirname(f), pkg };
  }
  return map;
}

/** Local files that `file` imports (JS/TS relative, tsconfig paths, workspace packages; Python relative and absolute). */
export function resolveDeps(root, file, ctx) {
  const src = readText(root, file);
  if (!src) return [];
  const abs = path.join(root, file);
  const out = new Set();
  const ext = path.extname(file);
  if (JS_EXT.includes(ext)) {
    const specs = new Set();
    for (const m of src.matchAll(/(?:import|export)\s[^'"]*?from\s*['"]([^'"]+)['"]/g)) specs.add(m[1]);
    for (const m of src.matchAll(/import\s*['"]([^'"]+)['"]/g)) specs.add(m[1]);
    for (const m of src.matchAll(/(?:require|import)\(\s*['"]([^'"]+)['"]\s*\)/g)) specs.add(m[1]);
    const ts = tsPaths(root, file, ctx.tsCache);
    for (const s of specs) {
      let r = null;
      if (s.startsWith('.')) r = tryResolve(root, path.resolve(path.dirname(abs), s), JS_EXT);
      if (!r && ts) {
        for (const [pat, targets] of Object.entries(ts.paths)) {
          const m = s.match(new RegExp('^' + pat.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace('*', '(.*)') + '$'));
          if (m) for (const t of targets) { r = tryResolve(root, path.join(ts.base, t.replace('*', m[1] || '')), JS_EXT); if (r) break; }
          if (r) break;
        }
      }
      if (!r) {
        const name = Object.keys(ctx.pkgs).find((n) => s === n || s.startsWith(n + '/'));
        if (name) {
          const { dir, pkg } = ctx.pkgs[name];
          const sub = s.slice(name.length).replace(/^\//, '');
          const entry = sub || (typeof pkg.exports === 'string' ? pkg.exports : pkg.exports?.['.']?.import || pkg.exports?.['.']?.default) || pkg.source || pkg.main || 'src/index';
          r = tryResolve(root, path.join(root, dir, entry), JS_EXT) || tryResolve(root, path.join(root, dir, 'src', sub || 'index'), JS_EXT);
        }
      }
      if (r && r !== file) out.add(r);
    }
  } else if (ext === '.py') {
    for (const m of src.matchAll(/^\s*from\s+(\.+)([\w.]*)\s+import\s+([\w, ]+)/gm)) {
      let dir = path.dirname(abs);
      for (let i = 1; i < m[1].length; i++) dir = path.dirname(dir);
      if (m[2]) { const mod = path.join(dir, ...m[2].split('.')); const r = tryResolve(root, mod, ['.py']) || tryResolve(root, path.join(mod, '__init__'), ['.py']); if (r) out.add(r); }
      else for (const n of m[3].split(',').map((x) => x.trim()).filter(Boolean)) { const r = tryResolve(root, path.join(dir, n), ['.py']); if (r) out.add(r); }
    }
    for (const m of src.matchAll(/^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))/gm)) {
      const mod = (m[1] || m[2]).split('.');
      for (const b of [root, path.join(root, 'src')]) {
        const r = tryResolve(root, path.join(b, ...mod), ['.py']) || tryResolve(root, path.join(b, ...mod, '__init__'), ['.py']);
        if (r) { out.add(r); break; }
      }
    }
  }
  return [...out].sort();
}

const isBarrel = (f) => /(^|\/)(index\.[jt]sx?|__init__\.py)$/.test(f);

/** Forward and reverse import graph over code files. Barrels (index.ts, __init__.py) are seen through. */
export function importGraph(root, files) {
  const ctx = { tsCache: new Map(), pkgs: workspacePackages(root, files) };
  const deps = {};
  for (const f of files) if (CODE.test(f)) deps[f] = resolveDeps(root, f, ctx);
  const through = (f, seen = new Set()) => {
    const out = new Set();
    for (const d of deps[f] || []) {
      if (seen.has(d)) continue;
      seen.add(d);
      out.add(d);
      if (isBarrel(d)) for (const x of through(d, seen)) out.add(x);
    }
    return out;
  };
  const fwd = {};
  const rev = {};
  for (const f of Object.keys(deps)) {
    fwd[f] = [...through(f)].sort();
    for (const d of fwd[f]) (rev[d] ||= []).push(f);
  }
  return { fwd, rev };
}

// ---------- scan ----------
function testsFor(file, files) {
  const s = stem(file);
  if (s === 'index' || s === '__init__') return [];
  const dir = path.posix.dirname(file);
  return files.filter((f) => f !== file && TEST.test(f) && stem(f) === s).sort((a, b) => Number(path.posix.dirname(b) === dir) - Number(path.posix.dirname(a) === dir));
}

function commandsFor(root, candidates) {
  const cmds = {};
  const dirs = new Set(['.']);
  for (const c of candidates.slice(0, 5)) { let d = path.posix.dirname(c.path); while (d && d !== '.') { dirs.add(d); d = path.posix.dirname(d); } }
  for (const d of [...dirs].sort((a, b) => a.length - b.length)) {
    const pkg = readJson(path.join(root, d, 'package.json'));
    for (const k of ['test', 'lint', 'typecheck', 'build']) if (pkg?.scripts?.[k] && !cmds[k]) cmds[k] = `${d === '.' ? '' : `(cd ${d} && `}npm run ${k}${d === '.' ? '' : ')'}`;
  }
  if (!cmds.test && (fs.existsSync(path.join(root, 'pytest.ini')) || fs.existsSync(path.join(root, 'pyproject.toml')))) cmds.test = 'pytest';
  if (!cmds.test && fs.existsSync(path.join(root, 'go.mod'))) cmds.test = 'go test ./...';
  if (!cmds.test && fs.existsSync(path.join(root, 'Cargo.toml'))) cmds.test = 'cargo test';
  return cmds;
}

export function scan(root, task, opts = {}) {
  const terms = extractTerms(task, opts.terms || []);
  if (!terms.length) throw new Error('no search terms: pass --terms a,b,c');
  const files = listFiles(root);
  const texts = files.filter((f) => TEXT.test(f)).slice(0, 5000);
  const hits = [];
  for (const f of texts) {
    const low = f.toLowerCase();
    const body = readText(root, f);
    let score = 0;
    const why = [];
    for (const t of terms) {
      const tl = t.toLowerCase();
      const inPath = t.length <= 4 ? countTerm(f, t) > 0 : low.includes(tl);
      const n = Math.min(5, countTerm(body, t));
      if (inPath || n) { score += (inPath ? 3 : 0) + n; why.push(`${t}×${n}${inPath ? '+path' : ''}`); }
    }
    if (score) hits.push({ path: f, score: score + why.length * 2 - (TEST.test(f) ? 2 : 0) - (/\.(md|json|ya?ml|toml)$/.test(f) ? 2 : 0), why, lines: lineCount(body) });
  }
  hits.sort((a, b) => b.score - a.score || a.path.localeCompare(b.path));
  const seeds = hits.filter((h) => CODE.test(h.path) && !TEST.test(h.path)).slice(0, opts.max || 8);
  const other = hits.filter((h) => !seeds.includes(h)).slice(0, 6);
  const { fwd, rev } = importGraph(root, files);
  const out = new Map();
  const put = (p, rel, extra = {}) => { if (!out.has(p)) out.set(p, { path: p, rel, lines: lineCount(readText(root, p)), ...extra }); };
  for (const s of seeds) put(s.path, 'seed', { score: s.score, why: s.why });
  for (const s of seeds) {
    for (const d of (fwd[s.path] || []).filter((d) => !isBarrel(d)).slice(0, 6)) put(d, `imported by ${s.path}`);
    for (const u of (rev[s.path] || []).filter((u) => !TEST.test(u)).slice(0, 8)) put(u, `imports ${s.path}`);
  }
  for (const c of [...out.values()]) {
    for (const t of [...testsFor(c.path, files), ...(rev[c.path] || []).filter((u) => TEST.test(u))].slice(0, 3)) put(t, `tests ${c.path}`);
  }
  for (const h of other) put(h.path, 'mention', { score: h.score, why: h.why });
  const candidates = [...out.values()].slice(0, 40);
  const churn = {};
  const log = trySh('git', ['log', '--format=', '--name-only', '-n', '300'], root) || '';
  for (const l of log.split('\n')) if (out.has(l)) churn[l] = (churn[l] || 0) + 1;
  for (const c of candidates) if (churn[c.path]) c.churn = churn[c.path];
  const slug = slugify(opts.slug || task);
  const brief = {
    version: 1, slug, task, terms, createdAt: new Date().toISOString(),
    head: (trySh('git', ['rev-parse', 'HEAD'], root) || '').trim() || null,
    searched: texts.length, candidates, commands: commandsFor(root, candidates),
  };
  writeJson(path.join(root, DIR, slug, 'scan.json'), brief);
  return brief;
}

export function renderScanText(b) {
  const L = [`scan ${DIR}/${b.slug}/scan.json | terms: ${b.terms.join(', ')} | ${b.searched} files searched`];
  const tag = { seed: 'seed', mention: 'ment' };
  for (const c of b.candidates) {
    const kind = tag[c.rel] || c.rel.split(' ')[0].replace('imported', 'dep').replace('imports', 'user').replace('tests', 'test');
    const note = c.why ? ` (${c.why.join(' ')})` : c.rel.includes(' ') ? ` ${c.rel.replace(/^(imported by|imports|tests) /, (m) => ({ 'imported by ': '<- ', 'imports ': '-> ', 'tests ': 'for ' }[m]))}` : '';
    L.push(`${kind.padEnd(4)} ${c.path}:${c.lines}${c.churn >= 3 ? ` ~${c.churn} commits` : ''}${note}`);
  }
  if (!b.candidates.length) L.push('no candidates: retry with --terms naming identifiers, routes, tables or UI text from the task');
  const cmds = Object.entries(b.commands).map(([k, v]) => `${k}: ${v}`);
  if (cmds.length) L.push(`cmds ${cmds.join(' | ')}`);
  return L.join('\n');
}

// ---------- guide validation ----------
const PLACEHOLDERS = [
  /\bTBD\b/, /\bTODO\b/, /\bFIXME\b/, /\bhandle (all |any |the )?(appropriate |relevant )?edge cases\b/i,
  /\badd (appropriate|proper|necessary) (error handling|validation|tests)\b/i, /\bas (needed|necessary|appropriate)\b/i,
  /\bsimilar to (step|task|file) \d+\b/i, /\betc\.?$/i, /\bupdate (the )?relevant (files|code)\b/i,
];

function strings(v, at, out = []) {
  if (typeof v === 'string') out.push([at, v]);
  else if (Array.isArray(v)) v.forEach((x, i) => strings(x, `${at}[${i}]`, out));
  else if (v && typeof v === 'object') for (const [k, x] of Object.entries(v)) strings(x, at ? `${at}.${k}` : k, out);
  return out;
}

const nonEmptyArray = (x) => Array.isArray(x) && x.length > 0;

export function validateGuide(root, g) {
  const e = [];
  if (!g || typeof g !== 'object') return ['not a JSON object'];
  if (!g.task || String(g.task).split(/\s+/).length < 4) e.push('"task": one line saying what the engineer will achieve');
  if (!KINDS.includes(g.kind)) e.push(`"kind" must be ${KINDS.join('|')}`);
  const goal = g.goal || {};
  if (!nonEmptyArray(goal.proposed)) e.push('"goal.proposed": what is true when the work is done (behaviour, not implementation)');
  if (!Array.isArray(goal.current) || (g.kind === 'bug' && !goal.current.length)) e.push('"goal.current": what happens today (required for bugs: the symptom)');
  if (!Array.isArray(goal.outOfScope)) e.push('"goal.outOfScope": array (may be empty) of what not to touch');
  if (!nonEmptyArray(g.files)) e.push('"files": the file map is required');
  else {
    if (g.files.length > MAX_FILES) e.push(`${g.files.length} files: over ${MAX_FILES}, slice the work into smaller guides`);
    const seen = new Set();
    g.files.forEach((f, i) => {
      const at = `files[${i}] ${f?.path || ''}`.trim();
      if (!f?.path) { e.push(`${at}: missing "path"`); return; }
      if (seen.has(f.path)) e.push(`${at}: listed twice`);
      seen.add(f.path);
      if (!ROLES.includes(f.role)) e.push(`${at}: "role" must be ${ROLES.join('|')}`);
      if (!f.why) e.push(`${at}: missing "why"`);
      if (['modify', 'create', 'test'].includes(f.role) && !f.change) e.push(`${at}: "change" says what to do in this file`);
      const exists = fs.existsSync(path.join(root, f.path));
      if (f.role === 'create' && exists) e.push(`${at}: already exists, use role "modify"`);
      if (f.role !== 'create' && f.role !== 'test' && !exists) e.push(`${at}: not found (typo, or role "create"?)`);
      if (f.role === 'test' && !exists && !f.new) e.push(`${at}: test file not found; set "new": true if the engineer creates it`);
      if (f.symbols !== undefined && !Array.isArray(f.symbols)) e.push(`${at}: "symbols" must be an array`);
      if (exists && Array.isArray(f.symbols)) {
        const src = readText(root, f.path);
        for (const s of f.symbols) if (!src.includes(s)) e.push(`${at}: symbol "${s}" not found in the file`);
      }
    });
    if (!g.files.some((f) => ['modify', 'create'].includes(f.role))) e.push('"files": at least one "modify" or "create" entry');
  }
  if (!nonEmptyArray(g.steps)) e.push('"steps": ordered plain-language steps');
  else if (g.steps.length > 12) e.push(`${g.steps.length} steps: keep to 12 or fewer`);
  if (!nonEmptyArray(g.guidance)) e.push('"guidance": lean, repo-specific coding guidance');
  if (!Array.isArray(g.watch)) e.push('"watch": array of risks (may be empty for trivial work)');
  else g.watch.forEach((w, i) => {
    if (!w?.risk || !w?.where) e.push(`watch[${i}]: needs "risk" and "where" (path, symbol or area)`);
    if (!LEVELS.includes(w?.level)) e.push(`watch[${i}]: "level" must be ${LEVELS.join('|')}`);
  });
  if (!nonEmptyArray(g.verify)) e.push('"verify": commands or checks that prove the work is done');
  if (g.open !== undefined && !Array.isArray(g.open)) e.push('"open" must be an array');
  (g.open || []).forEach((o, i) => { if (!o?.q || !o?.recommend) e.push(`open[${i}]: needs "q" and "recommend"`); });
  (g.decisions || []).forEach((d, i) => { if (!d?.q || !d?.a) e.push(`decisions[${i}]: needs "q" and "a"`); });
  for (const [at, s] of strings(g)) {
    for (const re of PLACEHOLDERS) if (re.test(s)) { e.push(`${at}: placeholder "${s.match(re)[0]}": name the specific thing`); break; }
    if (s.split('\n').length > MAX_SNIPPET_LINES) e.push(`${at}: ${s.split('\n').length} lines; guide, do not implement (signatures or <=${MAX_SNIPPET_LINES}-line snippets)`);
  }
  return e;
}

/** Files that import something the guide modifies but are not in the map: the blast radius the guide missed. */
export function unmappedImporters(root, g) {
  const mapped = new Set(g.files.map((f) => f.path));
  const targets = g.files.filter((f) => f.role === 'modify').map((f) => f.path);
  if (!targets.length) return [];
  const { rev } = importGraph(root, listFiles(root));
  const out = [];
  for (const t of targets) for (const u of rev[t] || []) if (!mapped.has(u)) out.push({ path: u, imports: t });
  return out;
}

// ---------- render ----------
const cell = (x) => String(x ?? '').replace(/\|/g, '\\|').replace(/\n/g, ' ');
const code = (p) => `\`${p}\``;
const ROLE_LABEL = { modify: 'modify', create: 'create', test: 'test', check: 'check only', reference: 'read, copy pattern' };

export function renderGuide(g, notes = []) {
  const count = (r) => g.files.filter((f) => f.role === r).length;
  const summary = ROLES.map((r) => (count(r) ? `${count(r)} ${r}` : '')).filter(Boolean).join(', ');
  const L = [`# Guiding hand: ${g.task}`, '', `**Kind:** ${g.kind} · **Files:** ${summary}`, '', '## Goal', ''];
  if (g.goal.current.length) L.push('**Now**', '', ...g.goal.current.map((x) => `- ${x}`), '');
  L.push('**When done**', '', ...g.goal.proposed.map((x) => `- ${x}`), '');
  if (g.goal.outOfScope.length) L.push('**Out of scope**', '', ...g.goal.outOfScope.map((x) => `- ${x}`), '');
  if (g.decisions?.length) L.push('## Decisions', '', ...g.decisions.map((d) => `- ${d.q} → **${d.a}**${d.by === 'default' ? ' _(default, not confirmed)_' : ''}`), '');
  L.push('## File map', '', 'Work top to bottom.', '', '| # | File | Role | Why | What to do |', '|--:|---|---|---|---|');
  g.files.forEach((f, i) => {
    const sym = f.symbols?.length ? `<br>${f.symbols.map(code).join(', ')}` : '';
    L.push(`| ${i + 1} | ${code(f.path)}${sym} | ${ROLE_LABEL[f.role]}${f.new ? ' (new)' : ''} | ${cell(f.why)} | ${cell(f.change || '')} |`);
  });
  L.push('');
  if (notes.length) L.push('Also imports a file you will modify (not reviewed for this guide):', '', ...notes.map((n) => `- ${code(n.path)} → ${code(n.imports)}`), '');
  L.push('## Approach', '', ...g.steps.map((s, i) => `${i + 1}. ${s}`), '');
  L.push('## Coding guidance', '', ...g.guidance.map((x) => `- ${x}`), '');
  if (g.watch.length) {
    const order = { high: 0, med: 1, low: 2 };
    L.push('## Watch out for', '', ...[...g.watch].sort((a, b) => order[a.level] - order[b.level]).map((w) => `- **${w.level}** ${w.risk} (${/[/.#]/.test(w.where) ? code(w.where) : w.where})`), '');
  }
  L.push('## Verify', '', ...g.verify.map((v) => `- [ ] ${v}`), '');
  if (g.open?.length) L.push('## Open questions', '', ...g.open.map((o) => `- ${o.q} Recommended: ${o.recommend}`), '');
  L.push('_Guidance for the engineer doing the work. When done, `guiding-hand check` compares your changes with this map._', '');
  return L.join('\n');
}

export function cmdRender(root, slug) {
  const dir = path.join(root, DIR, slug);
  const g = readJson(path.join(dir, 'guide.json'));
  if (!g) return { errors: [`cannot read ${DIR}/${slug}/guide.json (missing or invalid JSON)`] };
  const errors = validateGuide(root, g);
  if (errors.length) return { errors };
  const notes = unmappedImporters(root, g);
  fs.writeFileSync(path.join(dir, 'guide.md'), renderGuide(g, notes));
  return { errors: [], guide: g, notes, file: `${DIR}/${slug}/guide.md` };
}

// ---------- check (after the engineer has done the work) ----------
export function cmdCheck(root, slug, base) {
  const dir = path.join(root, DIR, slug);
  const g = readJson(path.join(dir, 'guide.json'));
  if (!g) throw new Error(`no ${DIR}/${slug}/guide.json`);
  const ref = base || readJson(path.join(dir, 'scan.json'))?.head || 'HEAD';
  const diff = trySh('git', ['diff', '--name-only', ref], root);
  if (diff == null) throw new Error(`git diff against ${ref} failed`);
  const untracked = trySh('git', ['ls-files', '-o', '--exclude-standard'], root) || '';
  const changed = new Set([...diff.split('\n'), ...untracked.split('\n')].filter((f) => f && !f.split('/').some((s) => IGNORE_DIRS.has(s))));
  const planned = g.files.filter((f) => ['modify', 'create', 'test'].includes(f.role));
  const done = planned.filter((f) => changed.has(f.path));
  const untouched = planned.filter((f) => !changed.has(f.path));
  const mapped = new Set(g.files.map((f) => f.path));
  const checkOnly = g.files.filter((f) => ['check', 'reference'].includes(f.role) && changed.has(f.path));
  const unplanned = [...changed].filter((f) => !mapped.has(f)).sort();
  return { ref, planned: planned.length, done: done.length, untouched, checkOnly, unplanned };
}

// ---------- CLI ----------
const HELP = `guiding-hand <command>
  scan "<task>" [--terms a,b] [--slug s] [--max 8]   recon brief -> ${DIR}/<slug>/scan.json
  render <slug>                                        validate guide.json -> guide.md
  check <slug> [--base ref]                            compare the engineer's changes with the map`;

function main() {
  const argv = process.argv.slice(2);
  const opt = (k) => { const i = argv.indexOf(`--${k}`); return i >= 0 ? argv.splice(i, 2)[1] : undefined; };
  const terms = opt('terms');
  const slug = opt('slug');
  const max = opt('max');
  const base = opt('base');
  const [cmd, arg] = argv;
  const root = process.cwd();
  const say = (s) => process.stdout.write(s + '\n');
  if (cmd === 'scan') {
    if (!arg) throw new Error('usage: scan "<task>"');
    say(renderScanText(scan(root, arg, { terms: terms ? terms.split(',') : [], slug, max: max ? Number(max) : undefined })));
  } else if (cmd === 'render') {
    if (!arg) throw new Error('usage: render <slug>');
    const r = cmdRender(root, arg);
    if (r.errors.length) { for (const e of r.errors) say(`error: ${e}`); process.exitCode = 1; return; }
    const n = (role) => r.guide.files.filter((f) => f.role === role).length;
    say(`${r.file} | ${r.guide.kind} | ${r.guide.files.length} files: ${ROLES.filter(n).map((x) => `${n(x)} ${x}`).join(', ')} | ${r.guide.watch.length} watch | ${(r.guide.open || []).length} open`);
    for (const x of r.notes) say(`note: ${x.path} imports ${x.imports} but is not in the map (add as "check" if the change can break it)`);
  } else if (cmd === 'check') {
    if (!arg) throw new Error('usage: check <slug>');
    const r = cmdCheck(root, arg, base);
    say(`check vs ${r.ref.slice(0, 12)} | ${r.done}/${r.planned} planned files changed`);
    for (const f of r.untouched) say(`  untouched: ${f.path} (${f.role})`);
    for (const f of r.checkOnly) say(`  changed but marked ${f.role}: ${f.path}`);
    for (const f of r.unplanned) say(`  unplanned: ${f}`);
  } else { say(HELP); if (cmd && cmd !== 'help') process.exitCode = 1; }
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  try { main(); } catch (e) { process.stderr.write(`guiding-hand: ${e.message}\n`); process.exitCode = 1; }
}
