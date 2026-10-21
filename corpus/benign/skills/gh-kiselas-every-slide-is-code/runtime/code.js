/*! deck-kit code plugin · optional · MIT · reference: 14-code-slides.md
 * Code blocks for technical talks: Shiki highlighting, magic-move between code states,
 * line focus, diffs, deterministic typing; slide layouts (code-full, code-side, code-over,
 * terminal, filetree). Everything is a pure function of the build progress the runtime hands
 * over, so rest frames, jumps, PDF and video stay exact.
 * Load after runtime/deck.js and before the deck's own Deck.slide() calls. */
(function () {
'use strict';
const D = window.Deck;

/* A setup mistake must be visible in the page, not only in the console: a red bar over the deck says what to fix. */
function fail(msg) {
  console.error(`deck-kit code: ${msg}`);
  const put = () => {
    let bar = document.getElementById('dk-code-fail');
    if (!bar) {
      bar = document.createElement('div'); bar.id = 'dk-code-fail'; bar.setAttribute('role', 'alert');
      bar.style.cssText = 'position:fixed;left:0;right:0;top:0;z-index:2147483647;margin:0;padding:12px 24px;background:#b00020;color:#fff;'
        + 'font:600 20px/1.4 system-ui,sans-serif;letter-spacing:0;text-transform:none;white-space:normal';
      document.body.append(bar);
    }
    const row = document.createElement('div'); row.textContent = `deck-kit code plugin: ${msg}`; bar.append(row);
  };
  document.body ? put() : document.addEventListener('DOMContentLoaded', put);
}
if (!D) { fail('runtime/deck.js must load first (move <script id="deck-kit-code-js"> below <script id="deck-kit-js">)'); return; }
const { ease, clamp, lerp, seg } = D;
const CFG = { shiki: '3.13.0', hosts: ['jsdelivr', 'esm'], timeout: 10000, dim: .38, dur: .9, minSize: 24 };
const $$ = (r, s) => [...r.querySelectorAll(s)];
const num = (v, d) => (v == null || v === '' || !isFinite(+v) ? d : +v);
const r2 = v => Math.round(v * 100) / 100;   // computed layout values are rounded: no 575.9999999 in styles on any platform

/* ───────────────────────── ready gate ─────────────────────────
 * The exporter waits for window.__ready; the runtime sets it to true after fonts and images.
 * The plugin adds its own condition (highlighting settled) without touching the runtime. */
let codeReady = false, coreReady;
Object.defineProperty(window, '__ready', { configurable: true, get: () => coreReady === true && codeReady, set: v => { coreReady = v; } });

/* ───────────────────────── theme for Shiki ─────────────────────────
 * Colours are CSS variables (--dk-code-*, defined in code.css from the deck's own variables),
 * so the highlighted code always matches the deck and can change with the theme without re-highlighting. */
const V = r => `var(--dk-code-${r})`;
const rule = (role, ...scope) => ({ scope, settings: { foreground: V(role) } });
const THEME = { name: 'deck', type: 'dark', colors: { 'editor.foreground': V('fg'), 'editor.background': V('bg') }, tokenColors: [
  rule('fg', 'variable', 'meta.embedded', 'source'),
  rule('comment', 'comment', 'punctuation.definition.comment'),
  rule('string', 'string', 'punctuation.definition.string', 'markup.inline.raw'),
  rule('number', 'constant.numeric'),
  rule('const', 'constant', 'variable.language', 'support.constant', 'constant.language'),
  rule('keyword', 'keyword', 'storage', 'keyword.control', 'keyword.operator.new', 'keyword.operator.expression', 'keyword.operator.delete',
    'keyword.operator.logical.python', 'keyword.operator.word', 'keyword.other'),
  rule('punct', 'punctuation', 'meta.brace', 'keyword.operator', 'meta.delimiter', 'keyword.operator.type.annotation'),
  rule('prop', 'variable.other.property', 'variable.other.object.property', 'variable.other.constant.property', 'meta.object-literal.key',
    'support.type.property-name', 'entity.name.tag.yaml', 'meta.property-name'),
  rule('function', 'entity.name.function', 'support.function', 'variable.function', 'meta.function-call entity.name.function'),
  rule('type', 'entity.name.type', 'entity.name.class', 'support.type', 'support.class', 'entity.other.inherited-class', 'storage.type.primitive'),
  rule('param', 'variable.parameter'),
  rule('tag', 'entity.name.tag', 'support.class.component'),
  rule('attr', 'entity.other.attribute-name'),
  rule('ins', 'markup.inserted'), rule('del', 'markup.deleted'),
] };
const ALIAS = { ts: 'typescript', js: 'javascript', py: 'python', rs: 'rust', sh: 'shellscript', bash: 'shellscript', shell: 'shellscript', zsh: 'shellscript',
  yml: 'yaml', golang: 'go', 'c++': 'cpp', 'c#': 'csharp', cs: 'csharp', rb: 'ruby', kt: 'kotlin', md: 'markdown', dockerfile: 'docker', text: '', txt: '', plain: '' };

/* ───────────────────────── fallback highlighter ─────────────────────────
 * Used when Shiki cannot load (offline, blocked CDN, unknown language). Coarse but coloured. */
const KW = new Set(('abstract as assert async await break case catch class const continue debugger def default defer del delete do elif else enum except export extends '
  + 'finally fn for from func function global go if implements import in instanceof interface is lambda let loop match mod module mut namespace new nonlocal of package '
  + 'pass pub raise return select self static struct super switch throw trait try type typeof use var void while with yield public private protected readonly '
  + 'and or not impl where then begin end').split(' '));
const SQL = new Set('select from where group by order having limit offset join left right inner outer on as and or not in is null insert into values update set delete create table index drop alter add primary key foreign references union all distinct case when then else end between like exists count sum avg min max'.split(' '));
const CONST = new Set('true false null undefined None True False nil NaN Infinity this self'.split(' '));
function mini(text, lang) {
  const hash = /^(py|python|sh|bash|shell|shellscript|zsh|yaml|yml|toml|ruby|rb|docker|dockerfile)$/.test(lang), dash = /^(sql|lua)$/.test(lang);
  const sql = lang === 'sql', kv = /^(json|yaml|yml|toml)$/.test(lang), n = text.length, role = new Array(n).fill('fg');
  const set = (a, b, r) => { for (let k = a; k < b; k++) if (text[k] !== '\n') role[k] = r; };
  for (let i = 0; i < n;) {
    const c = text[i], rest = text.slice(i, i + 3);
    if ((!hash && !dash && rest.startsWith('//')) || (hash && c === '#') || (dash && rest.startsWith('--'))) {
      let j = text.indexOf('\n', i); if (j < 0) j = n; set(i, j, 'comment'); i = j; continue;
    }
    if (!hash && !dash && rest.startsWith('/*')) { let j = text.indexOf('*/', i + 2); j = j < 0 ? n : j + 2; set(i, j, 'comment'); i = j; continue; }
    if (c === '"' || c === "'" || c === '`') {
      const q = (lang === 'py' || lang === 'python') && rest === c + c + c ? c + c + c : c;
      let j = i + q.length;
      while (j < n && !text.startsWith(q, j) && (q.length === 3 || q === '`' || text[j] !== '\n')) j += text[j] === '\\' ? 2 : 1;
      j = Math.min(n, j + q.length);
      let k = j; while (text[k] === ' ') k++;
      set(i, j, kv && text[k] === ':' ? 'prop' : 'string'); i = j; continue;
    }
    if (/\d/.test(c) && !/[\w$]/.test(text[i - 1] || '')) {
      const m = /^(0x[\da-f]+|\d[\d_]*(\.\d+)?(e[+-]?\d+)?)/i.exec(text.slice(i, i + 40)); set(i, i + m[0].length, 'number'); i += m[0].length; continue;
    }
    if (/[A-Za-z_$]/.test(c)) {
      const m = /^[A-Za-z_$][\w$]*/.exec(text.slice(i, i + 80)), w = m[0], j = i + w.length;
      let k = j; while (text[k] === ' ') k++;
      let p = i - 1; while (text[p] === ' ') p--;
      const r = (sql ? SQL.has(w.toLowerCase()) : KW.has(w)) ? 'keyword' : CONST.has(w) ? 'const' : text[k] === '(' ? 'function'
        : /[A-Z]/.test(w[0]) ? 'type' : text[p] === '.' ? 'prop' : 'fg';
      set(i, j, r); i = j; continue;
    }
    if (/[{}()[\];,.:<>=+\-*/%!&|^~?@]/.test(c)) role[i] = 'punct';
    i++;
  }
  const out = []; let line = [];
  for (let i = 0; i < n; i++) { if (text[i] === '\n') { out.push(line); line = []; } else line.push(role[i]); }
  out.push(line);
  return out;
}

/* ───────────────────────── Shiki from a CDN ───────────────────────── */
let shikiP = null, hl = null, engine = '';
const langP = {}, langM = {};
// every module is requested from all configured hosts at once; the first to answer wins (a CDN that is slow or blocked costs nothing)
const URLS = {
  jsdelivr: { pkg: (m, v) => `https://cdn.jsdelivr.net/npm/${m}@${v}/+esm`, lang: (id, v) => `https://cdn.jsdelivr.net/npm/@shikijs/langs@${v}/dist/${id}.mjs` },
  esm: { pkg: (m, v) => `https://esm.sh/${m}@${v}`, lang: (id, v) => `https://esm.sh/@shikijs/langs@${v}/${id}` },
};
const any = (kind, name) => Promise.any(CFG.hosts.filter(h => URLS[h]).map(h => import(URLS[h][kind](name, CFG.shiki))));
function loadShiki() {
  return shikiP || (shikiP = (async () => {
    const [core, eng] = await Promise.all([any('pkg', '@shikijs/core'), any('pkg', '@shikijs/engine-javascript')]);
    hl = await core.createHighlighterCore({ themes: [THEME], langs: [], engine: eng.createJavaScriptRegexEngine({ forgiving: true }) });
    return hl;
  })());
}
// the grammar module downloads in parallel with the core; it is registered once both are there
function loadLang(id) {
  const mod = langM[id] || (langM[id] = any('lang', id));
  return langP[id] || (langP[id] = Promise.all([mod, loadShiki()]).then(([m]) => hl.loadLanguage(m.default)));
}
const settle = (p, ms) => Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error(`timed out after ${ms} ms`)), ms))]);
let warned = false;
const warn = msg => { if (!warned) { warned = true; console.warn(`deck-kit code: ${msg}; using the built-in highlighter (coloured, less precise)`); } };

/* Pre-highlighted cache: a JSON script with id deck-kit-code-cache maps "lang\ntext" to one string per line,
 * one letter per character (a = ROLES[0] ...). Written by `sync-runtime.mjs --code-cache deck.html` after a run with Shiki.
 * A deck whose every block hits the cache never touches the network, so `bundle` gives an offline file with Shiki colours. */
const ROLES = ['fg', 'comment', 'keyword', 'string', 'number', 'const', 'function', 'type', 'prop', 'punct', 'param', 'tag', 'attr', 'ins', 'del',
  'prompt', 'cmd', 'out'];   // the last three are set by the terminal and filetree parsers, never by Shiki; new roles go at the end (cache keys)
const enc = roles => roles.map(row => row.map(r => String.fromCharCode(97 + Math.max(0, ROLES.indexOf(r)))).join(''));
const dec = lines => lines.map(s => [...s].map(c => ROLES[c.charCodeAt(0) - 97] || 'fg'));
let cache = {};
try { cache = JSON.parse(document.getElementById('deck-kit-code-cache')?.textContent || '{}'); } catch (e) { console.warn('deck-kit code: unreadable highlight cache'); }
const used = {};   // entries produced by Shiki or the cache in this run: what dump() writes back

// roles[line][col] for one state's text
// late: a second try after the timeout (live mode only), without a deadline; null when it fails again
async function highlight(text, lang, late) {
  const id = ALIAS[lang] ?? lang, key = `${lang}\n${text}`;
  if (!id) return text.split('\n').map(l => new Array(l.length).fill('fg'));
  if (cache[key]) { used[key] = cache[key]; engine = engine === 'fallback' ? engine : 'cache'; return dec(cache[key]); }
  if (CFG.shiki) {
    try {
      const ready = loadLang(id);
      await (late ? ready : settle(ready, CFG.timeout));
      const lines = hl.codeToTokensBase(text, { lang: id, theme: 'deck' }), out = []; let off = 0;
      const src = text.split('\n');
      lines.forEach((toks, li) => {
        const row = new Array((src[li] || '').length).fill('fg');
        for (const t of toks) {
          const m = /--dk-code-([a-z]+)\)/.exec(t.color || ''), r = m ? m[1] : 'fg';
          for (let k = 0; k < t.content.length; k++) row[t.offset - off + k] = r;
        }
        out.push(row); off += (src[li] || '').length + 1;
      });
      engine = engine === 'fallback' ? engine : engine === 'cache' ? 'cache+shiki' : 'shiki';
      used[key] = enc(out);
      return out;
    } catch (e) { if (late) return null; warn(`Shiki unavailable for "${lang}" (${e.message || e})`); }
  }
  if (late) return null;
  engine = 'fallback';
  const out = mini(text, lang); out.fb = true;
  return out;
}

/* ───────────────────────── parsing ───────────────────────── */
const dedent = lines => {
  const ind = Math.min(...lines.filter(l => l.trim()).map(l => l.match(/^ */)[0].length), 1e9);
  return lines.map(l => l.slice(Math.min(ind, l.match(/^ */)[0].length)));
};
const cleanLines = text => {
  let lines = text.replace(/\t/g, '  ').replace(/\r/g, '').split('\n').map(l => l.replace(/\s+$/, ''));
  while (lines.length && !lines[0].trim()) lines.shift();
  while (lines.length && !lines[lines.length - 1].trim()) lines.pop();
  return dedent(lines);
};
// "1-3|5|7-" → one Set of 1-based line numbers per step (null = every line)
function parseFocus(spec, n) {
  spec = (spec || '').trim();
  if (!spec || spec === '*' || spec === 'all') return null;
  const s = new Set();
  for (const part of spec.split(',')) {
    const m = /^\s*(\d+)(?:\s*-\s*(\d*))?\s*$/.exec(part); if (!m) continue;
    const a = +m[1], b = m[2] === undefined ? a : m[2] === '' ? n : +m[2];
    for (let k = a; k <= b; k++) s.add(k);
  }
  return s;
}

/* Terminal: "$ command" starts a step, the lines after it are its output ("! text" marks an error line). One state per command,
 * each holding the whole transcript so far; the matcher glides the old lines and the new command types itself. */
function terminalStates(el, id) {
  const prompt = el.dataset.prompt || '$', cmds = [];
  for (const l of cleanLines(el.textContent)) {
    if (l === prompt || l.startsWith(prompt + ' ')) cmds.push({ cmd: l, out: [] });
    else if (cmds.length) cmds[cmds.length - 1].out.push(l);
    else if (l.trim()) console.warn(`deck-kit code (${id}): terminal line before the first "${prompt} command" is ignored: ${l}`);
  }
  const done = [];
  return cmds.map(c => {
    const cmdLine = done.length;
    done.push({ text: c.cmd, tk: 'cmd' }, ...c.out.map(t => (t.startsWith('! ') ? { text: t.slice(2), tk: 'err' } : { text: t, tk: 'out' })));
    const lines = done.map(l => ({ text: l.text, kind: 'ctx', tk: l.tk }));
    const roles = lines.map(l => [...l.text].map((_, i) => (l.tk === 'cmd' ? (i < prompt.length ? 'prompt' : 'cmd') : l.tk === 'err' ? 'del' : 'out')));
    return { lines, spec: null, cmdLine, roles, text: lines.map(l => l.text).join('\n') };
  });
}

/* Filetree: indented names (two spaces per level, a trailing / for a directory, "  # note" for a comment) become a drawn tree.
 * State 0 is the tree, state 1 the same tree with the target file marked and everything else dimmed. The target is
 * data-focus, or else the data-file of the next slide's first code block (the file its code belongs to). */
function treeStates(el, id, sec) {
  const raw = el.textContent.replace(/\t/g, '  ').replace(/\r/g, '').split('\n').map(l => l.replace(/\s+$/, '')).filter(l => l.trim());
  const base = Math.min(...raw.map(l => l.match(/^ */)[0].length), 1e9);
  const nodes = raw.map(l => {
    const ind = l.match(/^ */)[0].length - base, m = /^(\S+?)(?:\s+#\s*(.*))?$/.exec(l.trim()) || [0, l.trim(), ''];
    return { name: m[1], note: m[2] || '', depth: Math.floor(ind / 2), dir: m[1].endsWith('/') };
  });
  const anc = [];
  nodes.forEach((n, i) => {
    n.last = true;
    for (let j = i + 1; j < nodes.length && nodes[j].depth >= n.depth; j++) if (nodes[j].depth === n.depth) { n.last = false; break; }
    anc[n.depth] = n; anc.length = n.depth + 1;
    n.path = anc.map(a => a.name.replace(/\/$/, '')).join('/');
    n.prefix = '';
    for (let k = 1; k < n.depth; k++) n.prefix += anc[k].last ? '    ' : '│   ';
    if (n.depth) n.prefix += n.last ? '└── ' : '├── ';
    n.text = n.prefix + n.name + (n.note ? `   # ${n.note}` : '');
  });
  let target = (el.dataset.focus || sec?.nextElementSibling?.querySelector('[data-file]')?.dataset.file || '').replace(/^\.\//, '');
  let hit = -1;
  if (target) {
    const base = target.split('/').pop();
    hit = nodes.findIndex(n => n.path === target || n.path.endsWith('/' + target));
    if (hit < 0) hit = nodes.findIndex(n => n.name.replace(/\/$/, '') === base);
    if (hit < 0) console.warn(`deck-kit code (${id}): "${target}" is not in the tree; nothing is highlighted`);
  } else console.warn(`deck-kit code (${id}): no data-focus and the next slide has no data-file; nothing is highlighted`);
  const state = mark => {
    const lines = nodes.map((n, i) => ({ text: n.text, kind: mark && i === hit ? 'hit' : 'ctx' }));
    const roles = nodes.map((n, i) => [...n.text].map((_, c) => (c < n.prefix.length ? 'punct'
      : c >= n.prefix.length + n.name.length ? 'comment' : mark && i === hit ? 'ins' : n.dir ? 'type' : 'fg')));
    let spec = null;
    if (mark) {
      const keep = [hit + 1]; let need = nodes[hit].depth;
      for (let j = hit - 1; j >= 0; j--) if (nodes[j].depth < need) { keep.push(j + 1); need = nodes[j].depth; }
      spec = keep.join(',');
    }
    return { lines, spec, roles, text: lines.map(l => l.text).join('\n') };
  };
  if (hit < 0) return [state(false)];
  return el.hasAttribute('data-filetree-static') ? [state(true)] : [state(false), state(true)];
}

function parseBlock(el, id, sec) {
  const diff = el.hasAttribute('data-diff');
  const kind = el.hasAttribute('data-terminal') ? 'terminal' : el.hasAttribute('data-filetree') ? 'filetree' : 'code';
  const kids = $$(el, ':scope > [data-code-step]'), raw = [];
  let states;
  if (kind === 'terminal') states = terminalStates(el, id);
  else if (kind === 'filetree') states = treeStates(el, id, sec);
  else {
    if (kids.length) for (const k of kids) raw.push({ text: k.textContent, spec: k.dataset.lines ?? null, file: k.dataset.file });
    else {
      let cur = { lines: [], spec: null };
      const list = [cur];
      for (const l of el.textContent.replace(/\r/g, '').split('\n')) {
        const m = el.dataset.codeSep === 'off' ? null : /^\s*---+\s*(.*)$/.exec(l);
        if (m) { cur = { lines: [], spec: m[1] || null }; list.push(cur); } else cur.lines.push(l);
      }
      for (const s of list) raw.push({ text: s.lines.join('\n'), spec: s.spec });
    }
    states = raw.filter(r => r.text.trim()).map(r => {
      let lines = cleanLines(r.text).map(text => ({ text, kind: 'ctx' }));
      if (diff) lines = lines.map(l => {
        const m = /^([+-]) ?(.*)$/.exec(l.text);
        if (m) return { text: m[2], kind: m[1] === '+' ? 'ins' : 'del' };
        return { text: l.text.replace(/^ {1,2}/, ''), kind: 'ctx' };
      });
      return { lines, spec: r.spec, file: r.file, text: lines.map(l => l.text).join('\n') };
    });
  }
  if (!states.length) { if (kind !== 'code') fail(`${id}: an empty ${kind} block (a terminal needs "$ command" lines, a filetree indented names)`); return null; }
  // frames: one per (state, focus); the rest frame of every step shows exactly one of them
  const frames = [];
  for (const [si, s] of states.entries()) {
    const parts = s.spec != null ? s.spec.split('|') : [null];
    for (const p of parts) frames.push({ s: si, spec: p });
  }
  const bl = kind === 'code' ? el.dataset.lines : null;
  if (bl != null) {
    const parts = bl.split('|');
    if (states.length === 1 && frames.length === 1) { frames.length = 0; parts.forEach(p => frames.push({ s: 0, spec: p })); }
    else if (parts.length === frames.length) frames.forEach((f, k) => { f.spec = parts[k]; });
    else console.warn(`deck-kit code (${id}): data-lines has ${parts.length} parts for ${frames.length} steps; extra steps show every line`);
  }
  for (const f of frames) f.focus = parseFocus(f.spec, states[f.s].lines.length);
  const lang = (el.dataset.code || 'text').toLowerCase();
  return { el, id, kind, layout: null, lang, states, frames, diff, fixed: kind !== 'code',
    file: el.dataset.file || '', numbers: kind === 'code' && el.hasAttribute('data-numbers'), start: num(el.dataset.numbers, 1) || 1,
    cursor: kind === 'terminal' || el.hasAttribute('data-code-cursor'), dur: CFG.dur, dim: CFG.dim,
    from: num(el.dataset.codeFrom, num(el.dataset.step, 0)), roles: kind === 'code' ? null : states.map(s => s.roles), ready: null, laid: false };
}

/* ───────────────────────── matching two states (magic move) ─────────────────────────
 * Atoms are the unit that glides: a word, a number or one punctuation mark. Lines are matched first
 * (LCS on trimmed text), then atoms inside the changed hunks between matched lines. Deterministic. */
function lcs(a, b) {
  const n = a.length, m = b.length, t = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) t[i][j] = a[i] === b[j] ? t[i + 1][j + 1] + 1 : Math.max(t[i + 1][j], t[i][j + 1]);
  const out = [];
  for (let i = 0, j = 0; i < n && j < m;) {
    if (a[i] === b[j]) { out.push([i, j]); i++; j++; } else if (t[i + 1][j] >= t[i][j + 1]) i++; else j++;
  }
  return out;
}
const ATOM = /[\p{L}\p{N}_$]+|\S/gu;
function atomize(state) {
  state.atoms = []; state.span = [];
  state.lines.forEach((l, li) => {
    const a0 = state.atoms.length;
    for (const m of l.text.matchAll(ATOM)) state.atoms.push({ t: m[0], line: li, col: m.index });
    state.span.push([a0, state.atoms.length]);
  });
}
const isPunct = a => a.t.length === 1 && !/[\p{L}\p{N}_$]/u.test(a.t);
function matchStates(A, B) {
  const map = new Map();
  const ka = A.lines.map(l => l.text.trim()), kb = B.lines.map(l => l.text.trim());
  const ia = ka.map((k, i) => (k ? i : -1)).filter(i => i >= 0), ib = kb.map((k, i) => (k ? i : -1)).filter(i => i >= 0);
  const anchors = lcs(ia.map(i => ka[i]), ib.map(i => kb[i])).map(([x, y]) => [ia[x], ib[y]]);
  anchors.push([A.lines.length, B.lines.length]);
  let pa = 0, pb = 0;
  for (const [la, lb] of anchors) {
    const ra = [A.span[pa]?.[0] ?? A.atoms.length, la < A.lines.length ? A.span[la][0] : A.atoms.length];
    const rb = [B.span[pb]?.[0] ?? B.atoms.length, lb < B.lines.length ? B.span[lb][0] : B.atoms.length];
    const sa = A.atoms.slice(ra[0], ra[1]), sb = B.atoms.slice(rb[0], rb[1]), got = new Map();
    for (const [x, y] of lcs(sa.map(a => a.t), sb.map(a => a.t))) got.set(x, y);
    // a lone punctuation mark that matched far from any matched neighbour would fly across the block: drop it
    for (const [x, y] of [...got]) if (isPunct(sa[x]) && got.get(x - 1) !== y - 1 && got.get(x + 1) !== y + 1) got.delete(x);
    for (const [x, y] of got) map.set(ra[0] + x, rb[0] + y);
    if (la < A.lines.length) {
      const [a0, a1] = A.span[la], [b0] = B.span[lb];
      for (let k = 0; k < a1 - a0; k++) map.set(a0 + k, b0 + k);
    }
    pa = la + 1; pb = lb + 1;
  }
  return map;
}

/* ───────────────────────── layout: measure once, build the nodes ───────────────────────── */
const cssNum = (cs, name, d) => { const v = parseFloat(cs.getPropertyValue(name)); return isFinite(v) ? v : d; };
function probe(body) {
  const p = document.createElement('span');
  p.style.cssText = 'position:absolute;left:0;top:0;visibility:hidden;white-space:pre';
  p.textContent = 'M'.repeat(400); body.append(p);
  const w = p.offsetWidth / 400; p.remove();
  return w;
}
// where an element sits inside the slide, in canvas pixels (offsetLeft/Top ignore the deck's scale)
function relTo(el, sec) { let x = 0, y = 0; for (let n = el; n && n !== sec; n = n.offsetParent) { x += n.offsetLeft; y += n.offsetTop; } return { x, y }; }

/* Size rule of the layouts (measured once, in setup): the block takes the largest font size, at most `cap`, for which the longest line
 * of every state fits the width and every row fits the free height (from the block's top to the bottom margin, minus what stands
 * below it in the same column); never below data-code-min (24 px), below that lines wrap. `fill`: the panel is stretched towards
 * the free height (at most `fill` times its content: 1.25-1.4) and the code sits in the middle of it. data-code-size pins a
 * size (shrink-to-fit only), data-code-max changes the cap. */
const PRESET = {
  'code-full': { cap: 44, fill: 1.3, stack: true }, terminal: { cap: 40, fill: 1.25, stack: true },
  'code-side': { cap: 36, fill: 1.4, center: true }, 'code-over': { cap: 36, fill: 1.3, center: true }, filetree: { cap: 40, fill: 1.4, center: true },
};
function freeHeight(b, sec, cs, preset) {
  let bottom = sec.clientHeight - cssNum(cs, '--dk-code-bottom', 90);
  if (preset.stack) for (let n = b.el.nextElementSibling; n; n = n.nextElementSibling) {
    const c = getComputedStyle(n);
    if (n.matches('aside, script, style, [hidden], .dk-note') || c.position === 'absolute' || c.position === 'fixed' || c.display === 'none') continue;
    bottom -= n.offsetHeight + (parseFloat(c.marginTop) || 0) + (parseFloat(c.marginBottom) || 0);
  }
  return Math.max(0, Math.floor(bottom - relTo(b.el, sec).y));
}

function layout(b, sec) {
  const el = b.el;
  b.dur = num(el.dataset.codeDur, CFG.dur); b.dim = num(el.dataset.codeDim, CFG.dim);
  b.states.forEach(atomize);
  el.classList.add('dk-code');
  el.dataset.kind = b.kind;
  el.textContent = '';
  let bar = null;
  if (b.file) { bar = D.el('div', { class: 'dk-code-bar' }, el); D.el('span', { class: 'dk-code-file', text: b.file }, bar); }
  const body = D.el('div', { class: 'dk-code-body' }, el);
  const cs = getComputedStyle(el);
  const padX = cssNum(cs, '--dk-code-pad-x', 40), padY = cssNum(cs, '--dk-code-pad-y', 30), lhk = cssNum(cs, '--dk-code-lh', 1.5);
  const preset = sec && b.layout ? PRESET[b.layout] : null, pinned = el.dataset.codeSize != null;
  let size = pinned ? +el.dataset.codeSize : preset ? num(el.dataset.codeMax, preset.cap) : parseFloat(cs.fontSize);
  const start = size;
  if (pinned || preset) el.style.fontSize = size + 'px';
  const minSize = Math.min(size, num(el.dataset.codeMin, CFG.minSize));
  const width = el.clientWidth;
  let cw = probe(body);
  const maxLen = Math.max(...b.states.flatMap(s => s.lines.map(l => l.text.length)), 1);
  const nLines = Math.max(...b.states.map(s => s.lines.length));
  const digits = String(b.start + nLines - 1).length;
  const gutterCols = (b.numbers ? digits + 2 : 0) + (b.diff ? 2 : 0);
  const barH = bar ? bar.offsetHeight : 0, free = preset ? freeHeight(b, sec, cs, preset) : 0;
  // rule: fit the longest line, and (in a layout) the free height; never below the floor (24 px); below the floor, wrap
  const fitSize = (width - 2 * padX) / ((maxLen + gutterCols) * (cw / size));
  if (preset && !pinned) {
    let s = Math.floor(Math.min(size, fitSize) * 4) / 4;
    while (s > minSize && free && barH + 2 * padY + nLines * Math.round(s * lhk) > free) s -= .25;
    size = Math.max(minSize, s);
  } else if (fitSize < size) size = Math.max(minSize, Math.floor(fitSize * 4) / 4);
  if (size !== start) { el.style.fontSize = size + 'px'; cw = probe(body); }
  const lineH = Math.round(size * lhk), avail = Math.max(8, Math.floor((width - 2 * padX) / cw) - gutterCols);
  const numW = b.numbers ? (digits + 2) * cw : 0, signW = b.diff ? 2 * cw : 0, x0 = padX + signW + numW, wrapped = maxLen > avail;
  if (wrapped) console.warn(`deck-kit code (${b.id}): a line is ${maxLen} columns, the block fits ${avail}; long lines wrap. Shorten them or widen the block`);

  // rows of every state (long lines wrap with a hanging indent)
  const items = [], byKey = new Map();
  const decor = (key, make) => { let it = byKey.get(key); if (!it) { it = make(); it.kind = it.kind || 'decor'; items.push(it); byKey.set(key, it); } return it; };
  let maxRows = 1;
  b.states.forEach((S, si) => {
    let row = 0; S.rows = []; S.recs = [];
    S.lines.forEach((l, li) => {
      const ind = l.text.match(/^ */)[0].length, cont = Math.min(ind + 2, Math.floor(avail / 2)), [a0, a1] = S.span[li];
      let cur = 0, shift = 0;
      for (let k = a0; k < a1; k++) {
        const a = S.atoms[k];
        let vc = a.col - shift;
        if (vc + a.t.length > avail && vc > (cur ? cont : 0)) { cur++; shift = a.col - cont; vc = cont; }
        S.recs[k] = { x: Math.round(x0 + vc * cw), y: padY + (row + cur) * lineH, line: li, col: a.col, role: 'fg' };
      }
      S.rows[li] = row;
      const y = r => padY + r * lineH;
      if (b.numbers) decor(`n${row}|${b.start + li}`, () => ({ text: String(b.start + li), cls: 'dk-code-num', style: { width: digits * cw + 'px' }, recs: [], nx: padX + signW })).recs[si] = { x: padX + signW, y: y(row), line: li };
      if (l.kind === 'ins' || l.kind === 'del') {
        decor(`s${row}|${l.kind}`, () => ({ text: l.kind === 'ins' ? '+' : '-', cls: 'dk-code-sign', kind: 'decor', recs: [], data: l.kind })).recs[si] = { x: padX, y: y(row), line: li };
      }
      for (let r = 0; r <= cur; r++) if (l.kind !== 'ctx')
        decor(`b${row + r}|${l.kind}`, () => ({ text: '', cls: 'dk-code-band', recs: [], data: l.kind, style: { height: lineH + 'px' } })).recs[si] = { x: 0, y: y(row + r), line: li };
      row += cur + 1;
    });
    S.nrows = row; maxRows = Math.max(maxRows, row);
  });
  // the panel: content height, or (fill) stretched towards the free height with the code in the middle
  const contentH = maxRows * lineH + 2 * padY;
  let bodyH = contentH, top0 = padY;
  if (preset?.fill && free) {
    const want = Math.min(free - barH, Math.round(contentH * preset.fill));
    if (want > contentH) { bodyH = want; top0 = padY + Math.floor((want - contentH) / 2); }
  }
  body.style.height = bodyH + 'px';
  // the row of blocks sits lower by half the spare height, but stays near its title (at most 96 px)
  b.shift = preset?.center && free ? clamp(Math.floor((free - barH - bodyH) / 2), 0, 96) : 0;
  if (preset && free && barH + contentH > free) console.warn(`deck-kit code (${b.id}): the code needs ${barH + contentH} px of height and the slide leaves ${free}; cut lines, split the states, or shorten the title`);

  // match consecutive states: matched atoms share one node
  b.states.forEach((S, si) => {
    const prev = si ? b.states[si - 1] : null, m = prev ? matchStates(prev, S) : new Map(), back = new Map([...m].map(([x, y]) => [y, x]));
    S.node = [];
    S.atoms.forEach((a, k) => {
      const rec = S.recs[k];
      let it = null;
      if (back.has(k)) it = prev.node[back.get(k)];
      if (!it) { it = { kind: 'atom', text: a.t, cls: 'dk-code-tok', recs: [] }; items.push(it); }
      it.recs[si] = rec; S.node[k] = it; a._rec = rec;
    });
  });
  if (top0 !== padY) for (const it of items) for (const r of it.recs) if (r) r.y += top0 - padY;   // fill: the code sits in the middle of the panel
  // order: bands under numbers under text
  const rank = { band: 0, num: 1, sign: 1, tok: 2 };
  items.sort((p, q) => rank[p.cls.replace('dk-code-', '')] - rank[q.cls.replace('dk-code-', '')]);
  for (const it of items) {
    it.el = D.el('span', { class: it.cls, text: it.text }, body);
    if (it.style) Object.assign(it.el.style, it.style);
    if (it.data) it.el.dataset.k = it.data;
    it.c = {};
  }
  b.caret = D.el('span', { class: 'dk-code-caret' }, body);
  b.caret.style.height = lineH * .78 + 'px';
  Object.assign(b, { items, body, cw, lineH, size, padY, x0, top0, avail, bodyTop: body.offsetTop, laid: true, cur: null, c: {} });
  applyRoles(b);

  // terminal timing, in seconds of the step: the command types, then its output appears line by line
  if (b.kind === 'terminal') b.frames.forEach(f => {
    const S = b.states[f.s], chars = S.lines[S.cmdLine].text.length, outN = S.lines.length - S.cmdLine - 1;
    // a step is at most 2.8 s, so it is finished within the default 3 s hold of the video timeline: the typing is what gives way
    const lead = .2, gap = outN ? .2 : 0, out = outN ? Math.min(outN * .07, .7) + .2 : 0, type = clamp(chars * .035, .4, 2.8 - lead - gap - out - .2);
    f.tm = { lead, type, t0: lead + type + gap, out: Math.min(outN * .07, .7) / Math.max(1, outN), dur: lead + type + gap + out + .2, cmd: S.cmdLine };
  });

  // one marker per step that changes something: the runtime drives it, its progress is the block's state
  const F = b.frames.length, first = b.cursor ? 0 : 1;
  b.raw = new Array(F).fill(0); if (!b.cursor) b.raw[0] = 1;
  b.markers = [];
  for (let k = first; k < F; k++) {
    const mk = D.el('i', { class: 'dk-code-mark', hidden: '', 'data-step': b.from + k, 'data-anim': 'code-step', 'data-dur': frameDur(b, k).toFixed(3) }, el);
    mk._blk = b; mk._k = k; b.markers.push(mk);
  }
  b.el._blk = b;
  paint(b);
}

/* Claims (code-side): the children of .dk-claims go with the code states, claim k at step from + k. "replace" (default):
 * one claim at a time, in one grid cell, so the column is as tall as the tallest claim; "stack": claims accumulate, the previous one steps back. */
function wireClaims(box, b) {
  const kids = [...box.children], mode = box.dataset.claims === 'stack' ? 'stack' : 'replace';
  box.dataset.claims = mode;
  if (kids.length !== b.frames.length) console.warn(`deck-kit code (${b.id}): ${kids.length} claims for ${b.frames.length} code steps; claim k goes with step k (${kids.length > b.frames.length ? 'the extra ones share the last step' : 'the last steps have no claim'})`);
  kids.forEach((k, i) => {
    k.classList.add('dk-claim');
    const step = Math.min(i, b.frames.length - 1) + b.from;
    if (k.dataset.step == null) k.dataset.step = step;
    if (k.dataset.anim == null) k.dataset.anim = 'fade';
    if (i < kids.length - 1 && i + 1 < b.frames.length) {
      if (mode === 'replace' && k.dataset.out == null) k.dataset.out = b.from + i + 1;
      if (mode === 'stack' && k.dataset.dim == null) k.dataset.dim = b.from + i + 1;
    }
  });
}

/* Notes (code-over): data-note="5-6" points at lines 5-6 of the state shown at the note's step (data-step; by default the first step
 * whose focus covers them). Positions are measured once: a bracket at the end of the longest line, an elbow arrow to a card in the
 * free column right of the block. A note leaves when the next one appears, unless it has data-note-keep. */
function wireNotes(sec, b) {
  const notes = $$(sec, '[data-note]').filter(n => !n.closest('[data-code],[data-terminal],[data-filetree]'));
  if (!notes.length) return;
  if (!b || !b.laid) { fail(`${sec.id}: data-note needs a code block on the same slide`); return; }
  const pos = relTo(b.el, sec), bw = b.el.offsetWidth, bh = b.el.offsetHeight;
  const right = sec.clientWidth - (parseFloat(getComputedStyle(sec).paddingRight) || 0), W = Math.round(right - pos.x);
  const list = [];
  for (const n of notes) {
    const m = /^\s*(\d+)(?:\s*-\s*(\d+))?\s*$/.exec(n.dataset.note);
    if (!m) { fail(`${b.id}: data-note="${n.dataset.note}" is not a line or a range like "5-6"`); continue; }
    const a = +m[1], covers = f => !f.focus || (() => { for (let l = a; l <= (m[2] ? +m[2] : a); l++) if (!f.focus.has(l)) return false; return true; })();
    let step = n.dataset.step != null ? +n.dataset.step : null;
    if (step == null) { const k = b.frames.findIndex(f => f.focus && covers(f)); step = b.from + Math.max(0, k >= 0 ? k : b.frames.findIndex(f => !f.focus)); }
    const k = clamp(step - b.from, 0, b.frames.length - 1), fr = b.frames[k], S = b.states[fr.s];
    const z = Math.min(m[2] ? +m[2] : a, S.lines.length);
    if (a > S.lines.length) { console.warn(`deck-kit code (${b.id}): data-note="${n.dataset.note}" is past the last line (${S.lines.length}) of the state at step ${step}`); continue; }
    if (!covers(fr)) console.warn(`deck-kit code (${b.id}): the lines of data-note="${n.dataset.note}" are dimmed at step ${step}; put them in that step's data-lines`);
    const yOf = row => b.bodyTop + b.top0 + row * b.lineH, yTop = yOf(S.rows[a - 1]), yBot = yOf(S.rows[z] ?? S.nrows);
    let xr = 0;
    for (let l = a - 1; l < z; l++) xr = Math.max(xr, b.x0 + Math.min(S.lines[l].text.length, b.avail) * b.cw);
    n.classList.add('dk-note');
    Object.assign(n.style, { left: pos.x + 'px', top: pos.y + 'px', width: W + 'px', height: bh + 'px' });
    const t = D.el('div', { class: 'dk-note-t' });
    while (n.firstChild) t.append(n.firstChild);
    const bx = Math.round(xr + 22), nx = Math.round(Math.max(bw + 48, bx + 64));
    Object.assign(t.style, { left: nx + 'px', width: Math.max(240, W - nx) + 'px' });
    const sv = D.svg('svg', { class: 'dk-note-svg', width: W, height: bh, viewBox: `0 0 ${W} ${bh}` }, n);
    n.append(t);
    if (W - nx < 300) console.warn(`deck-kit code (${b.id}): only ${W - nx} px right of the code for the note "${t.textContent.slice(0, 24)}"; narrow the block (--dk-over-w)`);
    const th = t.offsetHeight, ym = (yTop + yBot) / 2;
    const ty = clamp(Math.round(ym - th / 2), 0, Math.max(0, bh - th)), y0 = Math.round(yTop + 8), y1 = Math.round(yBot - 8), yc = Math.round(ym), yt = Math.round(ty + th / 2);
    const mid = Math.round((bx + nx) / 2);
    t.style.top = ty + 'px';
    D.svg('path', { d: `M${bx - 8},${y0} H${bx} V${y1} H${bx - 8}`, class: 'br' }, sv);
    D.svg('path', { d: `M${bx + 6},${yc} H${mid} V${yt} H${nx}`, class: 'ln' }, sv);
    D.svg('path', { d: `M${bx + 20},${yc - 10} L${bx + 5},${yc} L${bx + 20},${yc + 10} Z`, class: 'hd' }, sv);
    if (n.dataset.step == null) n.dataset.step = step;
    if (n.dataset.anim == null) n.dataset.anim = 'fade';
    list.push({ n, step });
  }
  const steps = [...new Set(list.map(x => x.step))].sort((p, q) => p - q);
  for (const { n, step } of list) {
    const nxt = steps.find(s => s > step);
    if (nxt != null && n.dataset.out == null && !n.hasAttribute('data-note-keep')) n.dataset.out = nxt;
  }
}

const newChars = (b, k) => {
  const f = b.frames[k], S = b.states[f.s], P = k ? b.states[b.frames[k - 1].s] : null;
  if (P === S) return 0;
  return S.node.reduce((n, it, i) => n + (it.recs.length && (!P || !it.recs[b.frames[k - 1].s]) ? S.atoms[i].t.length : 0), 0);
};
const frameDur = (b, k) => (b.kind === 'terminal' ? b.frames[k].tm.dur : b.cursor ? clamp(newChars(b, k) * .03 + .3, .7, 2) : b.dur);

function applyRoles(b) {
  if (!b.laid || !b.roles) return;
  b.states.forEach((S, si) => S.atoms.forEach(a => { a._rec.role = b.roles[si]?.[a.line]?.[a.col] || 'fg'; }));
  if (b.cur) paint(b, true);
}

/* ───────────────────────── painting: a pure function of (frame a, frame b, progress) ───────────────────────── */
D.anim('code-step', { dur: .9, curve: ease.linear, f(el, e, info) {
  const b = el._blk; b.raw[el._k] = info.raw;
  if (el._k === b.frames.length - 1) { b.dirtyArgs = null; paint(b); }
  return {};
} });

const wr = (it, k, v, apply) => { if (it.c[k] !== v) { it.c[k] = v; apply(v); } };
function paint(b, again) {
  if (!again) {
    let cur = 0;
    for (let k = b.frames.length - 1; k >= 1; k--) if (b.raw[k] > 0) { cur = k; break; }
    b.cur = { k: cur, p: cur || b.cursor ? b.raw[cur] : 1 };
  }
  const { k, p } = b.cur, fb = b.frames[k], fa = k ? b.frames[k - 1] : b.cursor ? null : fb;
  const sa = fa ? fa.s : -1, sb = fb.s, sameState = sa === sb;
  const term = b.kind === 'terminal' && !sameState ? fb.tm : null, sec = term ? p * term.dur : 0;   // terminal: times in seconds of the step
  // segments of the step's progress
  const T = b.cursor ? { out: [0, .28], mv: [0, .28], in: [.28, .5], dim: [0, .28] } : { out: [0, .35], mv: [.1, .8], in: [.45, 1], dim: [.1, .7] };
  const qOut = 1 - ease.outCubic(seg(p, ...T.out)), qMv = ease.inOutCubic(seg(p, ...T.mv)), qIn = ease.outCubic(seg(p, ...T.in)), qDim = ease.inOutSine(seg(p, ...T.dim));
  const dimOf = (f, line) => (!f || !f.focus || f.focus.has(line + 1) ? 1 : b.dim);
  // typing: new atoms appear character by character in reading order
  let typed = null, total = 0;
  if (b.cursor && !sameState) {
    typed = new Map(); const S = b.states[sb];
    S.atoms.forEach((a, i) => { const it = S.node[i]; if (!(sa >= 0 && it.recs[sa]) && (!term || a.line === term.cmd)) { typed.set(it, { start: total, len: a.t.length }); total += a.t.length; } });
  }
  const tt = typed ? (term ? seg(sec, term.lead, term.lead + term.type) : seg(p, .28, 1)) * total : 0;
  let caret = null;
  for (const it of b.items) {
    const ra = sa >= 0 ? it.recs[sa] : null, rb = it.recs[sb];
    let x, y, o, role, text = it.text;
    if (ra && rb) {
      x = lerp(ra.x, rb.x, qMv); y = lerp(ra.y, rb.y, qMv);
      o = lerp(dimOf(fa, ra.line), dimOf(fb, rb.line), sameState ? ease.inOutSine(seg(p, 0, .6)) : qDim);
      role = (p >= .5 ? rb : ra).role;
    } else if (ra) { x = ra.x; y = ra.y; o = dimOf(fa, ra.line) * qOut; role = ra.role; }
    else if (rb) {
      x = rb.x; y = rb.y; role = rb.role;
      const ty = typed && typed.get(it);
      if (ty) {
        const shown = clamp(Math.round(tt - ty.start), 0, ty.len);
        o = shown > 0 ? dimOf(fb, rb.line) : 0; text = it.text.slice(0, shown);
        if (shown > 0 && shown <= ty.len && p < 1 && (!term || tt < total) && (!caret || ty.start >= caret.start)) caret = { start: ty.start, x: x + shown * b.cw, y };
      } else if (term) {
        const t0 = term.t0 + Math.max(0, rb.line - term.cmd - 1) * term.out;   // output: line by line, after the command has typed
        o = dimOf(fb, rb.line) * ease.outCubic(seg(sec, t0, t0 + .25));
      } else o = dimOf(fb, rb.line) * qIn;
    } else { o = 0; x = y = 0; }
    wr(it, 'v', o <= .004 ? 'hidden' : '', v => { it.el.style.visibility = v; });
    if (o <= .004) { wr(it, 'o', '', v => { it.el.style.opacity = v; }); if (it.kind === 'atom') wr(it, 'x', it.text, v => { it.el.textContent = v; }); continue; }
    wr(it, 'o', o >= .999 ? '' : o.toFixed(3), v => { it.el.style.opacity = v; });
    wr(it, 't', `translate(${x.toFixed(2)}px,${y.toFixed(2)}px)`, v => { it.el.style.transform = v; });
    if (it.kind === 'atom') {
      wr(it, 'r', role, v => { it.el.dataset.r = v; });
      wr(it, 'x', text, v => { it.el.textContent = v; });
    }
  }
  const showCaret = !!caret && p > 0 && p < 1;
  wr(b, 'cv', showCaret ? 'visible' : 'hidden', v => { b.caret.style.visibility = v; });
  if (showCaret) b.caret.style.transform = `translate(${caret.x.toFixed(2)}px,${(caret.y + b.lineH * .11).toFixed(2)}px)`;
}

/* ───────────────────────── wiring ───────────────────────── */
const blocks = [], bySlide = new Map();
function slideSetup(sec) {
  const list = bySlide.get(sec.id) || [];
  for (const b of list) layout(b, sec);
  const shift = list[0]?.shift;
  if (shift) for (const n of [list[0].el, ...$$(sec, ':scope > .dk-claims, :scope > .dk-companion')]) n.style.marginTop = shift + 'px';
  wireNotes(sec, list[0]);
}
const origSlide = D.slide;
D.slide = function (id, spec) {
  if (bySlide.has(id)) {
    const user = spec || {};
    spec = { ...user, setup(el, api) { slideSetup(el); user.setup?.(el, api); } };
  }
  return origSlide.call(D, id, spec);
};

const LAYOUTS = ['code-full', 'code-side', 'code-over', 'terminal', 'filetree'], BLOCK = '[data-code], [data-terminal], [data-filetree]';
function scan() {
  const deck = document.querySelector('.deck');
  if (!deck) { fail('no .deck element yet; load the plugin after the deck markup'); return; }
  if (!getComputedStyle(document.documentElement).getPropertyValue('--dk-code-size').trim())
    fail('runtime/code.css is missing (add <style id="deck-kit-code-css"></style> right after the runtime CSS and run node scripts/sync-runtime.mjs deck.html)');
  let late = false;
  for (const me of document.scripts) {
    if (me.id === 'deck-kit-code-js') break;
    if (!me.src && !/^deck-kit/.test(me.id) && /Deck\.slide\(/.test(me.text)) { late = true; break; }
  }
  const owned = [];
  $$(deck, ':scope > section.slide').forEach((sec, i) => {
    const els = $$(sec, BLOCK).filter(e => !e.parentElement.closest(BLOCK));
    if (!els.length) return;
    if (!sec.id) sec.id = `code-slide-${i + 1}`;
    const list = els.map((e, j) => parseBlock(e, `${sec.id}#${j + 1}`, sec)).filter(Boolean);
    if (!list.length) return;
    // layout preset: data-layout or a class on the slide; else inferred (claims: side, notes: over, one code block: full)
    let L = sec.dataset.layout || LAYOUTS.find(l => sec.classList.contains(l)) || '';
    if (L && L !== 'none' && !LAYOUTS.includes(L)) { fail(`slide "${sec.id}": unknown layout "${L}" (use ${LAYOUTS.join(', ')} or none)`); L = ''; }
    if (!L) L = list[0].kind === 'terminal' ? 'terminal' : list[0].kind === 'filetree' ? 'filetree' : sec.querySelector('.dk-claims') ? 'code-side'
      : sec.querySelector('[data-note]') ? 'code-over' : list.length === 1 ? 'code-full' : '';
    if (L === 'none') L = '';
    if (L) sec.dataset.layout = L;
    bySlide.set(sec.id, list); blocks.push(...list); owned.push(sec.id);
    origSlide.call(D, sec.id, { setup: slideSetup });
    const claims = sec.querySelector('.dk-claims');
    if (claims) wireClaims(claims, list[0]);
    for (const b of list) {
      b.layout = L || null;
      // styled from the start, so the warm-up layout requests the code font and fonts.ready waits for it
      b.el.classList.add('dk-code');
      const most = Math.max(...b.states.map(s => s.lines.length));
      if (most > (b.kind === 'code' ? 18 : 14)) console.warn(`deck-kit code (${b.id}): a state has ${most} lines; show 8-15`);
    }
  });
  if (late) fail(`load this plugin before the deck script that calls Deck.slide(). It is loaded after it, so the Deck.slide() hooks (setup, frame, steps) of the code slides (${owned.join(', ') || 'none'}) are replaced and will not run. Move <script id="deck-kit-code-js"> above your script`);
}
scan();

function start() {
  if (!blocks.length) { codeReady = true; return; }
  const jobs = blocks.filter(b => !b.fixed).map(b => Promise.all(b.states.map(s => highlight(s.text, b.lang))).then(r => { b.roles = r; applyRoles(b); }));
  Promise.allSettled(jobs).then(() => {
    codeReady = true;
    // live only: a slow CDN may still deliver, and the block then upgrades in place (exports never do: they must be repeatable)
    if (D.MODE === 'live') for (const b of blocks) if (b.roles && b.roles.some(r => r.fb))
      Promise.all(b.states.map(s => highlight(s.text, b.lang, true))).then(r => { if (r.every(Boolean)) { b.roles = r; applyRoles(b); } });
  });
}
document.readyState === 'loading' ? document.addEventListener('readystatechange', function h() {
  if (document.readyState === 'loading') return;
  document.removeEventListener('readystatechange', h); start();
}) : start();

/* ───────────────────────── offline cache without npm ─────────────────────────
 * Open the deck once as deck.html?code-cache (needs the network for Shiki): a panel offers to write the highlighted tokens straight
 * into the deck file (Chrome's file picker; pick the deck itself) or to copy the <script> tag. Same result as
 * `node scripts/sync-runtime.mjs --code-cache deck.html`, no Node needed. */
const cacheTag = () => `<script type="application/json" id="deck-kit-code-cache">${D.code.dump()}<\/script>`;
function injectCache(html) {
  const tag = cacheTag(), old = /^<script type="application\/json" id="deck-kit-code-cache">[\s\S]*?<\/script>/m, slot = /^<script id="deck-kit-code-js">/m;
  if (old.test(html)) return html.replace(old, () => tag);
  if (slot.test(html)) return html.replace(slot, () => `${tag}\n<script id="deck-kit-code-js">`);
  throw new Error('that file has no <script id="deck-kit-code-js"> slot: pick the deck itself');
}
function cachePanel() {
  const put = () => {
    const box = D.el('div', { id: 'dk-code-cache-panel', role: 'status', style: { position: 'fixed', right: '16px', bottom: '16px', zIndex: '2147483000', maxWidth: '440px', padding: '14px 18px',
      background: '#111', color: '#fff', font: '500 15px/1.45 system-ui,sans-serif', borderRadius: '10px', boxShadow: '0 8px 30px rgba(0,0,0,.4)' } }, document.body);
    const say = t => { msg.textContent = t; };
    const msg = D.el('div', {}, box), row = D.el('div', { style: { marginTop: '10px', display: 'flex', gap: '10px' } }, box);
    const btn = (t, f) => { const x = D.el('button', { text: t, style: { font: 'inherit', padding: '6px 12px', borderRadius: '6px', border: '0', cursor: 'pointer' } }, row); x.onclick = () => f().catch(e => say(String(e.message || e))); return x; };
    say('Highlighting code…');
    const t = setInterval(() => {
      if (!codeReady) return;
      clearInterval(t);
      if (!/shiki|cache/.test(engine)) { say(`Shiki did not load (engine: ${engine || 'none'}), nothing to store. Check the network and reload.`); return; }
      const n = Object.keys(used).length;
      say(`${n} highlighted code states, ${(D.code.dump().length / 1024).toFixed(1)} KB. Store them in the deck so it works offline.`);
      if (window.showOpenFilePicker) btn('Store in the deck file…', async () => {
        const [h] = await window.showOpenFilePicker({ types: [{ description: 'the deck', accept: { 'text/html': ['.html', '.htm'] } }] });
        const out = injectCache(await (await h.getFile()).text());
        const w = await h.createWritable(); await w.write(out); await w.close();
        say(`Stored ${n} states in ${h.name}. Reload it without ?code-cache, then run bundle.`);
      });
      btn('Copy the <script> tag', async () => { await navigator.clipboard.writeText(cacheTag()); say('Copied. Paste it just above <script id="deck-kit-code-js"> (replace an old one).'); });
    }, 200);
  };
  document.body ? put() : document.addEventListener('DOMContentLoaded', put);
}
if (D.MODE === 'live' && /[?&]code-cache(=|&|$)/.test(location.search)) cachePanel();

D.code = { config(o) { Object.assign(CFG, o); return D.code; }, blocks, get ready() { return codeReady; }, get engine() { return engine; },
  // JSON for the offline cache slot (only what Shiki or the cache produced in this run)
  dump() { return JSON.stringify(used).replace(/</g, '\\u003c'); },
  cacheTag, inject: injectCache };
})();
