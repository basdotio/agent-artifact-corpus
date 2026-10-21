#!/usr/bin/env node
// Plan a deck as data. SCRIPT.md holds the shot table (template/SCRIPT.md); this tool
//   --check      prints the titles alone (the title test) and lints the story
//   --animatic   per-slide steps, words on screen, estimated time, cumulative timeline
//   --new f.html a deck skeleton from template/deck.html: one section per row, TODO markers
// Zero dependencies (node:fs), Node 18+. Details: 03-story.md.
//   node scripts/plan.mjs SCRIPT.md --check
//   node scripts/plan.mjs SCRIPT.md --animatic
//   node scripts/plan.mjs SCRIPT.md --new my-deck.html
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

/* ───────────────────────── vocabulary ───────────────────────── */

// Transition names of runtime/deck.js (06-transitions.md).
export const TRANSITIONS = ['none', 'fade', 'dip', 'push', 'cover', 'zoom', 'iris', 'wipe', 'blinds', 'cube', 'flip', 'tear', 'dissolve', 'morph', 'camera',
  'flash', 'punch', 'whip', 'glitch', 'lightleak', 'dither'];

const DAYS = 'mon|tue|wed|thu|fri|sat|sun|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec';
const CLOSE_TECH = new RegExp(`\\b(try|adopt|use|install|clone|start|run|read|join|contribute|migrate|fork|star|open|take|copy|get|steal|ship|pick)\\b|github|\\brepo\\b|https?:|\\bnpm\\b|\\bpip\\b|\\b(${DAYS})\\b`, 'i');
const CLOSE_PITCH = new RegExp(`\\b(raise|raising|invest|join|fund|back|close|ask|asking|need|seek|seeking|commit|approve|sign|pilot|intro|introduce|meet)\\b|[$€£]\\s?\\d|\\d\\s?(k|m|b)\\b|\\b(${DAYS})\\b`, 'i');
const CLOSE_LAUNCH = new RegExp(`\\b(available|ships?|shipping|today|now|starting|from|price|priced|pricing|free|get|download|order|pre-?order|sign|waitlist|try|rolling|rollout|live)\\b|[$€£]\\s?\\d|\\b(${DAYS})\\b`, 'i');
const CLOSE_ANY = new RegExp([CLOSE_TECH, CLOSE_PITCH, CLOSE_LAUNCH].map(r => r.source).join('|'), 'i');
const CLOSE_WEAK = /^\W*(questions?\b|any questions|thank(s| you)|q\s*&\s*a|the end|fin)\b/i;

// The spine of each talk type (03-story.md). Chapters are matched by keyword on the Chapter column.
export const PRESETS = {
  generic: { label: 'no type set', wpm: 130, perMin: [0.5, 1.5], spine: [], close: CLOSE_ANY, closeHint: 'the decision, the ask or the next step' },
  'tech-talk': {
    label: 'technical talk', wpm: 130, perMin: [0.6, 1.3], close: CLOSE_TECH, closeHint: 'how to adopt it: a command, a repo, a first step',
    spine: [
      { name: 'problem', re: /problem|context|stakes|pain|setup|why/i },
      { name: 'failed attempts', re: /fail|attempt|tried|naive|obvious|baseline|dead.?end|wrong|before/i },
      { name: 'mechanism', re: /mechanism|how it works|design|architecture|idea|approach|insight|internals|solution/i },
      { name: 'proof / benchmark', re: /proof|benchmark|result|measure|numbers|evidence|evaluation|data/i },
      { name: 'how to adopt', re: /adopt|how to|start|try|use it|next|take|getting|rollout|migrat|apply/i },
    ],
    wants: [
      { chapter: 'proof / benchmark', kinds: ['chart', 'number'], msg: 'the proof chapter has no chart or number; a benchmark needs a comparison you can see' },
      { chapter: 'mechanism', kinds: ['diagram', 'code'], msg: 'the mechanism chapter has no diagram or code; show how it works, do not only say it' },
    ],
  },
  pitch: {
    label: 'investor / idea pitch', wpm: 140, perMin: [0.8, 2], close: CLOSE_PITCH, closeHint: 'the ask: amount, use of funds, decision, date',
    spine: [
      { name: 'problem', re: /problem|pain|situation|today|status quo/i },
      { name: 'insight', re: /insight|secret|observation|belief|realiz|thesis|idea/i },
      { name: 'product', re: /product|solution|how it works|demo|the answer/i },
      { name: 'why now', re: /why now|timing|shift|tailwind|trend|window/i },
      { name: 'traction', re: /traction|proof|pilot|result|growth|customers|revenue|numbers|evidence/i },
      { name: 'ask', re: /\bask\b|raise|raising|funding|invest|decision|use of funds|next steps?/i },
    ],
    wants: [
      { chapter: 'traction', kinds: ['chart', 'number'], msg: 'the traction chapter has no chart or number; traction is the one claim that needs evidence' },
    ],
  },
  'product-launch': {
    label: 'product launch', wpm: 125, perMin: [0.7, 1.6], close: CLOSE_LAUNCH, closeHint: 'availability: what, when, where, how much',
    spine: [
      { name: 'before / after', re: /before|after|old way|new way|today|contrast|status quo|problem/i },
      { name: 'the moment', re: /moment|reveal|meet|introduc|unveil|announce|demo|the product/i },
      { name: 'how it works', re: /how it works|how|inside|under the hood|features?|mechanism|tour/i },
      { name: 'proof', re: /proof|numbers|customers?|results?|benchmark|beta|early|evidence|quote/i },
      { name: 'availability', re: /availab|pricing|price|ship|today|get it|rollout|launch date|when/i },
    ],
    wants: [
      { chapter: 'proof', kinds: ['chart', 'number', 'photo'], msg: 'the proof chapter shows no chart, number or screenshot' },
    ],
  },
};

// Visual kinds: what the Visual column may say. Anything else is accepted as a free description.
const KINDS = {
  chart: /^(charts?|bars?|bar-chart|line|lines|line-chart|donut|pie|waterfall|scatter|area|plots?|graphs?|sparklines?|histogram|heatmap|gauge|benchmarks?)$/i,
  diagram: /^(diagrams?|flows?|flowchart|architecture|timeline|roadmap|matrix|2x2|map|schematic|sequence|pipeline|graph-diagram)$/i,
  code: /^(code|snippet|terminal|diff|shell|cli|repl|config)$/i,
  photo: /^(photos?|images?|screenshots?|pictures?|mock|mockup|mock-up|ui|demo|video|gif|illustration)$/i,
  number: /^(numbers?|stat|stats|metric|counter|big-number|figure)$/i,
  none: /^(none|-|—|–|n\/a|no|text|statement|quote|title|blank)$/i,
};
const NUMWORD = { one: 1, two: 2, three: 3, four: 4, five: 5, a: 1, an: 1 };

/* ───────────────────────── small helpers ───────────────────────── */

const plain = s => String(s ?? '').replace(/\\\|/g, '|').replace(/[*_`]+/g, '').replace(/\s+/g, ' ').trim();
export const wordsOf = s => (plain(s).match(/[^\s]+/g) || []).filter(w => /[\p{L}\p{N}]/u.test(w));
export const wordCount = s => wordsOf(s).length;
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
export const mmss = sec => { const s = Math.max(0, Math.round(sec)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };
const slug = (s, n = 4) => plain(s).toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim().split(' ').slice(0, n).join('-') || 'slide';

// "20 min", "20m", "1h", "90 s", "1:30" (m:ss) -> seconds
export function parseDuration(v) {
  if (v == null) return null;
  const s = String(v).trim().toLowerCase();
  let m;
  if ((m = s.match(/^(\d+):(\d{2})$/))) return +m[1] * 60 + +m[2];
  if ((m = s.match(/^(\d+(?:\.\d+)?)\s*(h|hr|hrs|hour|hours)\b/))) return +m[1] * 3600;
  if ((m = s.match(/^(\d+(?:\.\d+)?)\s*(s|sec|secs|second|seconds)\b/))) return +m[1];
  if ((m = s.match(/^(\d+(?:\.\d+)?)\s*(m|min|mins|minute|minutes)?\b/))) return +m[1] * 60;
  return null;
}

/* ───────────────────────── parsing ───────────────────────── */

const splitRow = line => {
  const t = line.trim().replace(/^\|/, '').replace(/\|$/, '');
  const cells = []; let cur = '';
  for (let i = 0; i < t.length; i++) {
    if (t[i] === '\\' && t[i + 1] === '|') { cur += '\\|'; i++; }
    else if (t[i] === '|') { cells.push(cur.trim()); cur = ''; }
    else cur += t[i];
  }
  cells.push(cur.trim());
  return cells;
};

const COLS = {
  n: /^(#|no\.?|n|num|number|slide)$/i,
  chapter: /^(chapter|act|section|part)$/i,
  title: /^(title|claim|slide title|headline)/i,
  steps: /^(steps?|builds?|clicks?)$/i,
  visual: /^(visual|picture|image|shows?)$/i,
  transition: /^(transition|in|enters?)$/i,
  note: /^(notes?|say|speaker notes?|script|voice)$/i,
  words: /^(words|on-screen words)$/i,
  sec: /^(sec|secs|seconds|time|duration)$/i,
  state: /^(through-?line|state|metric|state change|running)$/i,
};

export function parseVisual(cell) {
  const raw = plain(cell);
  const out = { raw, desc: '', items: [], empty: raw === '' };
  if (out.empty) return out;
  const colon = raw.indexOf(':');
  const head = colon > 0 ? raw.slice(0, colon) : raw;
  out.desc = colon > 0 ? raw.slice(colon + 1).trim() : '';
  for (const part of head.split(/\s*(?:,|\+|&|;|\/|\band\b)\s*/i).filter(Boolean)) {
    const toks = part.toLowerCase().split(/\s+/);
    let n = 1;
    if (/^\d+x?$/.test(toks[0])) n = parseInt(toks[0], 10);
    else if (NUMWORD[toks[0]] && toks.length > 1) n = NUMWORD[toks[0]];
    let kind = 'other';
    for (const t of toks) {
      const w = t.replace(/s$/, '');
      const hit = Object.keys(KINDS).find(k => KINDS[k].test(t) || KINDS[k].test(w));
      if (hit) { kind = hit; break; }
    }
    out.items.push({ kind, n, text: part.trim() });
  }
  out.kinds = [...new Set(out.items.map(i => i.kind))];
  out.charts = out.items.filter(i => i.kind === 'chart').reduce((a, i) => a + i.n, 0);
  return out;
}

export function parseTransition(cell) {
  const raw = plain(cell).toLowerCase();
  if (raw === '' || raw === '-' || raw === '—' || raw === 'default' || raw === 'same') return { raw, name: null };
  const m = raw.match(/^([a-z]+)(?::(left|right|up|down))?(?:@\s*(\d+)[ ,]+(\d+))?$/);
  if (!m) return { raw, name: raw, bad: true };
  return { raw, name: m[1], dir: m[2] || null, origin: m[3] ? [+m[3], +m[4]] : null, bad: !TRANSITIONS.includes(m[1]) };
}

export function parseSteps(cell) {
  const raw = plain(cell);
  if (raw === '' || raw === '-' || raw === '—') return { count: 0, texts: [] };
  if (/^\d+$/.test(raw)) return { count: +raw, texts: [] };
  const texts = raw.split(/\s*;\s*/).map(s => s.replace(/^\s*\d+\s*[:.)]\s*/, '').trim()).filter(Boolean);
  return { count: texts.length, texts };
}

const toNumber = s => {
  const m = String(s).replace(/,/g, '').replace(/−/g, '-').match(/(-?\d+(?:\.\d+)?)\s*(k|m|b|%|x)?/i);
  if (!m) return null;
  return parseFloat(m[1]) * ({ k: 1e3, m: 1e6, b: 1e9 }[(m[2] || '').toLowerCase()] || 1);
};

export function parseScript(text) {
  const errors = [], lines = text.replace(/\r\n?/g, '\n').split('\n');
  const header = {};
  let i = 0;
  if (lines[0] && lines[0].trim() === '---') {
    for (i = 1; i < lines.length && lines[i].trim() !== '---'; i++) {
      const m = lines[i].match(/^\s*([A-Za-z][\w -]*?)\s*:\s*(.*?)\s*$/);
      if (m) header[m[1].toLowerCase().replace(/\s+/g, '-')] = m[2].replace(/^(["'])(.*)\1$/, '$2');
    }
    if (i >= lines.length) errors.push('the header block opened with --- is never closed');
    i++;
  } else errors.push('no header: start SCRIPT.md with a --- block (type, length, title ...), see template/SCRIPT.md');

  // the first table that has a "#" and a title column
  let head = null, start = -1;
  for (let j = i; j < lines.length; j++) {
    if (!/^\s*\|/.test(lines[j])) continue;
    const cells = splitRow(lines[j]);
    if (cells.some(c => COLS.n.test(plain(c))) && cells.some(c => COLS.title.test(plain(c)))) { head = cells; start = j; break; }
  }
  const rows = [];
  const type = (header.type || '').toLowerCase().trim();
  if (type && !PRESETS[type]) errors.push(`unknown type "${header.type}": use ${Object.keys(PRESETS).filter(k => k !== 'generic').join(' | ')}`);
  const preset = PRESETS[PRESETS[type] ? type : 'generic'];
  const script = {
    header, errors, rows, type: PRESETS[type] ? type : 'generic', preset,
    title: header.title || 'Untitled deck',
    target: parseDuration(header.length),
    wpm: parseInt(header.rate, 10) || preset.wpm,
  };
  if (header.length && script.target == null) errors.push(`cannot read length "${header.length}": write it like "20 min"`);
  if (!head) { errors.push('no shot table found: a markdown table with at least "#" and "Title" columns'); return script; }

  const col = {};
  head.forEach((c, k) => { for (const [name, re] of Object.entries(COLS)) if (col[name] == null && re.test(plain(c))) col[name] = k; });
  let chapter = '';
  for (let j = start + 2; j < lines.length && /^\s*\|/.test(lines[j]); j++) {
    const c = splitRow(lines[j]);
    if (c.every(x => /^:?-{2,}:?$/.test(x) || x === '')) continue;
    const get = name => (col[name] == null ? '' : c[col[name]] ?? '');
    const nRaw = plain(get('n'));
    if (!/^\d+$/.test(nRaw)) { errors.push(`row ${rows.length + 1}: "${nRaw}" in the # column is not a slide number`); continue; }
    if (plain(get('chapter'))) chapter = plain(get('chapter'));
    const steps = parseSteps(get('steps')), title = plain(get('title'));
    const row = {
      n: +nRaw, index: rows.length + 1, chapter, title, steps: steps.count, stepTexts: steps.texts,
      visual: parseVisual(get('visual')), transition: parseTransition(get('transition')),
      note: plain(get('note')), extraWords: get('words') === '' ? null : parseInt(get('words'), 10),
      sec: get('sec') === '' ? null : parseDuration(get('sec')), state: plain(get('state')),
    };
    row.screenWords = wordCount(title) + (row.extraWords ?? row.stepTexts.reduce((a, t) => a + wordCount(t), 0));
    rows.push(row);
    if (!title) errors.push(`slide ${row.index}: empty title`);
  }
  if (!rows.length) errors.push('the shot table has a header but no rows');
  for (const k of ['visual', 'transition']) if (col[k] == null) script.missingColumns = [...(script.missingColumns || []), k];
  return script;
}

/* ───────────────────────── the title heuristic ───────────────────────── */

// A cheap check, not grammar: does the title contain a word that looks like a verb?
const IRREGULAR = ('is are was were be been being am has have had having do does did done doing can could will would should must may might shall cannot ' +
  "isn't aren't wasn't weren't don't doesn't didn't can't won't ran went gone gave given took taken made saw seen came became began begun broke broken built bought " +
  'brought caught chose chosen cost drove driven fell fallen felt found flew grew grown held kept knew known led left lost met paid rose risen sold sent shot shut sat ' +
  'spent stood stole struck taught told thought threw thrown understood won wrote written outran overtook beat beaten hit let bit bent dug drew drawn drank ate eaten fed ' +
  'fought forgot forgotten hid hidden hung laid lay lit meant rode rang sang sank slept spoke spun split spread swam swept tore woke wore wept shrank sought sped ' +
  'gets got gotten goes says knows sees seems means leads leaves').split(' ');
const BASE_VERBS = ('add aim allow answer appear apply ask avoid become begin bend bind blow break bring build burn buy call cap carry catch cause change charge check choose ' +
  'close come compare cost count cover create cross cut deliver depend design detect die divide draw drop earn eat end enter exceed expect fail fall fill find fix flatten ' +
  'flow follow force gain get give go grow guess handle happen have help hide hit hold hurt improve include increase join jump keep kill know land launch lead learn leave ' +
  'let lift like live look lose lower make matter mean measure meet miss move need offer open own pay pick plan play prove pull push put raise reach read reduce rely remove ' +
  'replace reply require return reveal rise run save say see seem sell send serve set shift ship show shrink shut sit solve spend split spread start stay steal stop stretch ' +
  'strike suffer take talk teach tell test think throw track trade trust try turn understand use wait want waste watch win work write beat break bet weigh double halve ' +
  'triple cut beat outgrow outrun outpace overtake outlast survive stall spike drift crash crush cost slip climb tumble stay stick swap switch bury burn hurt hit walk ' +
  'ignore hold lock bind miss lack spend earn owe pay repay shrink grow sink sour speed slow').split(' ');
const VERB_FORMS = new Set(IRREGULAR);
for (const b of BASE_VERBS) {
  VERB_FORMS.add(b);
  VERB_FORMS.add(/(s|x|z|ch|sh|o)$/.test(b) ? b + 'es' : /[^aeiou]y$/.test(b) ? b.slice(0, -1) + 'ies' : b + 's');
  VERB_FORMS.add(b.endsWith('e') ? b + 'd' : /[^aeiou]y$/.test(b) ? b.slice(0, -1) + 'ied' : b + 'ed');
  VERB_FORMS.add(b.endsWith('e') ? b.slice(0, -1) + 'ing' : b + 'ing');
  if (/^[^aeiou]*[aeiou][^aeiouwxy]$/.test(b) || /^[^aeiou]+[aeiou][^aeiouwxy]$/.test(b)) { VERB_FORMS.add(b + b.slice(-1) + 'ing'); VERB_FORMS.add(b + b.slice(-1) + 'ed'); }
}
const NOT_PAST = new Set(['need', 'seed', 'speed', 'bed', 'red', 'feed', 'weed', 'breed', 'indeed', 'hundred', 'sacred', 'naked', 'wicked', 'bleed', 'proceed', 'exceed']);

export function hasVerb(title) {
  const ws = plain(title).toLowerCase().replace(/[’]/g, "'").split(/[^a-z']+/).filter(Boolean);
  return ws.some(w => VERB_FORMS.has(w) || (w.length >= 5 && w.endsWith('ed') && !NOT_PAST.has(w)) || /'(s|re|ve|ll|d)$/.test(w) && w.length > 3 && /^(it|that|there|we|you|they|he|she|what|who|here)'/.test(w));
}

/* ───────────────────────── timing ───────────────────────── */

export function slideTiming(script, row) {
  const read = 1.5 + 0.3 * row.screenWords;                       // 03-story.md: a second and a half plus 0.3 s per word
  const speakWords = wordCount(row.note);
  const speak = speakWords / script.wpm * 60;
  const stepsMin = 3 + 2.5 * row.steps;                           // each click needs a beat to land
  if (row.sec != null) return { sec: row.sec, why: 'set', read, speak, stepsMin, speakWords };
  const sec = Math.max(read, speak, stepsMin);
  return { sec, why: sec === speak && speakWords ? 'speech' : sec === stepsMin ? 'steps' : 'reading', read, speak, stepsMin, speakWords };
}

export function animatic(script) {
  let cum = 0;
  const slides = script.rows.map(row => {
    const t = slideTiming(script, row);
    const start = cum; cum += t.sec;
    return { row, ...t, start, end: cum };
  });
  const filled = script.rows.filter(r => wordCount(r.note) >= 8).length;
  const total = cum, target = script.target;
  const spokenWords = script.rows.reduce((a, r) => a + wordCount(r.note), 0);
  // Notes that are stubs make the estimate a floor: reading and click time, not what you will actually say.
  const budget = target ? Math.round(script.wpm * target / 60) : 0;
  const floors = script.rows.length > 0 && (filled < script.rows.length / 2 || (budget > 0 && spokenWords < budget * 0.6));
  const chapters = [];
  for (const s of slides) {
    const last = chapters[chapters.length - 1];
    if (last && last.name === s.row.chapter) { last.sec += s.sec; last.count++; }
    else chapters.push({ name: s.row.chapter, sec: s.sec, count: 1, start: s.start });
  }
  const findings = [];
  const avg = slides.length ? total / slides.length : 0;
  for (const s of slides) {
    if (avg && s.sec > 2.2 * avg && s.sec > 60) findings.push({ level: 'warn', slide: s.row.index, code: 'long-slide', msg: `${mmss(s.sec)} on one slide (average ${mmss(avg)}): add steps or split it` });
    if (s.row.screenWords > 40) findings.push({ level: 'warn', slide: s.row.index, code: 'dense', msg: `${s.row.screenWords} words on screen at the last step (rule: under 40)` });
  }
  if (target) {
    const delta = (total - target) / target;
    if (Math.abs(delta) > 0.1) {
      const n = avg ? Math.round(Math.abs(total - target) / avg) : 0;
      if (floors && delta < 0) findings.push({ level: 'note', slide: null, code: 'length', msg: `estimated ${mmss(total)} against a target of ${mmss(target)}, but the notes hold ${spokenWords} of the ${budget} words that fit: this is a floor. Write the notes, then run it again` });
      else findings.push({ level: 'warn', slide: null, code: 'length', msg: `estimated ${mmss(total)} against a target of ${mmss(target)} (${delta > 0 ? '+' : ''}${Math.round(delta * 100)}%): ${delta > 0 ? 'cut' : 'add'} about ${n} slide${n === 1 ? '' : 's'} of average length${delta > 0 && floors ? ' (and that is before the notes are finished)' : ''}` });
    }
  }
  if (floors && !target) findings.push({ level: 'note', slide: null, code: 'floor', msg: `only ${filled} of ${slides.length} slides have a speaker note of 8+ words: times are a floor (reading and click time), not a forecast` });
  return { slides, total, target, avg, chapters, findings, spokenWords, floors };
}

/* ───────────────────────── the linter ───────────────────────── */

export function lint(script) {
  const f = [], rows = script.rows, P = script.preset;
  const add = (level, slide, code, msg) => f.push({ level, slide, code, msg });
  for (const e of script.errors) add('error', null, 'parse', e);
  if (!rows.length) return f;
  if (script.missingColumns) add('warn', null, 'columns', `no ${script.missingColumns.join(' / ')} column: those checks are skipped`);
  if (script.type === 'generic') add('note', null, 'type', `no \`type:\` in the header (${Object.keys(PRESETS).filter(k => k !== 'generic').join(' | ')}): the spine checks are skipped`);
  if (!script.header.thesis) add('warn', null, 'thesis', 'no `thesis:` in the header: write what the room knows or does at the end, in one sentence');

  // titles
  const seen = new Map();
  for (const r of rows) {
    const n = wordCount(r.title), verb = hasVerb(r.title);
    if (n < 4 && !verb) add('warn', r.index, 'title-topic', `"${r.title}" is a topic (${n} word${n === 1 ? '' : 's'}, no verb): write the claim as a sentence`);
    else if (n < 4) add('warn', r.index, 'title-short', `"${r.title}" is ${n} words: a claim usually needs 4+`);
    else if (!verb) add('warn', r.index, 'title-shape', `"${r.title}" has no verb-ish word: is it a claim or a label? (heuristic)`);
    if (n > 16) add('warn', r.index, 'title-long', `title has ${n} words: it will not hold on two lines at 88 px`);
    const key = r.title.toLowerCase();
    if (seen.has(key)) add('warn', r.index, 'title-dup', `same title as slide ${seen.get(key)}: one idea per slide`); else seen.set(key, r.index);
  }

  // transitions
  const used = new Map();
  rows.forEach((r, k) => {
    if (r.transition.bad) add('error', r.index, 'transition-unknown', `unknown transition "${r.transition.raw}" (${TRANSITIONS.join(', ')})`);
    if (k === 0) return;
    const name = r.transition.name || script.header['default-transition'] || 'fade';
    if (!r.transition.bad) used.set(name, (used.get(name) || 0) + 1);
  });
  if (used.size > 3) add('warn', null, 'transitions', `${used.size} transition types (${[...used.keys()].join(', ')}): keep 2-3, each with one meaning (06-transitions.md)`);

  // visuals
  let noneRun = 0;
  for (const r of rows) {
    if (r.visual.empty) { add('warn', r.index, 'no-visual', 'no Visual decision: write chart, diagram, code, photo, number, or "none" if the slide is only a statement'); noneRun = 0; continue; }
    if (r.visual.charts > 1) add('warn', r.index, 'multi-chart', `${r.visual.charts} charts on one slide: one chart, one question; split the slide or overlay as one chart`);
    if (r.visual.kinds.length === 1 && r.visual.kinds[0] === 'none') { noneRun++; if (noneRun === 3) add('warn', r.index, 'text-run', 'three text-only slides in a row: put a picture or a number in one of them'); } else noneRun = 0;
  }

  // steps and density
  for (const r of rows) {
    if (r.steps > 5) add('warn', r.index, 'steps-many', `${r.steps} steps: past 4-5 clicks the room loses the thread; split the slide`);
    if (r.screenWords > 40) add('warn', r.index, 'words-screen', `${r.screenWords} words on screen at the last step: keep under 40 and move the rest to the note`);
  }

  // the ending
  const last = rows[rows.length - 1];
  const closeText = last.title;
  if (CLOSE_WEAK.test(last.title)) add('warn', last.index, 'no-close', `the last slide says "${last.title}": end on ${P.closeHint}, not on thanks or questions`);
  else if (!P.close.test(closeText)) add('warn', last.index, 'no-close', `the last slide does not read as a closing ask (${P.closeHint}): "${last.title}" (heuristic)`);

  // spine
  if (P.spine.length) {
    const chapters = [...new Set(rows.map(r => r.chapter).filter(Boolean))];
    if (!chapters.length) add('warn', null, 'spine', `no Chapter column filled: cannot check the ${P.label} spine (${P.spine.map(s => s.name).join(' → ')})`);
    else {
      let at = -1;
      for (const s of P.spine) {
        const idx = chapters.findIndex(c => s.re.test(c));
        if (idx < 0) add('warn', null, 'spine-missing', `${P.label}: no chapter reads as "${s.name}" (chapters: ${chapters.join(' | ')})`);
        else { if (idx < at) add('warn', null, 'spine-order', `${P.label}: "${s.name}" comes before an earlier step of the spine (${P.spine.map(x => x.name).join(' → ')})`); at = Math.max(at, idx); }
      }
      for (const w of P.wants || []) {
        const inChapter = rows.filter(r => r.chapter && new RegExp(P.spine.find(s => s.name === w.chapter).re).test(r.chapter));
        if (inChapter.length && !inChapter.some(r => (r.visual.kinds || []).some(k => w.kinds.includes(k)))) add('warn', inChapter[0].index, 'spine-visual', w.msg);
      }
    }
  }

  // length: slide count and the word budget
  if (script.target) {
    const min = script.target / 60, per = rows.length / min;
    const [lo, hi] = P.perMin;
    if (per < lo || per > hi) add('warn', null, 'slide-count', `${rows.length} slides in ${mmss(script.target)} is ${per.toFixed(2)} per minute; ${P.label} runs ${lo}-${hi}: ${per > hi ? 'cut to about ' + Math.floor(hi * min) : 'you have room for about ' + Math.floor(lo * min)}`);
    const budget = Math.round(script.wpm * min), spoken = rows.reduce((a, r) => a + wordCount(r.note), 0);
    const filled = rows.filter(r => wordCount(r.note) >= 8).length;
    if (filled >= rows.length / 2) {
      if (spoken > budget * 1.1) add('warn', null, 'word-budget', `the notes hold ${spoken} words; at ${script.wpm} wpm ${mmss(script.target)} fits ${budget}: cut ${spoken - budget} words`);
      else if (spoken < budget * 0.5) add('note', null, 'word-budget', `the notes hold ${spoken} of the ${budget} words that ${mmss(script.target)} fits at ${script.wpm} wpm: fine if you improvise, short if you read`);
    }
    const a = animatic(script);
    if (Math.abs(a.total - script.target) / script.target > 0.1 && !a.floors) add('warn', null, 'length', `estimated ${mmss(a.total)} against a target of ${mmss(script.target)} (see --animatic)`);
  } else add('note', null, 'no-length', 'no `length:` in the header: slide count, word budget and timing are not checked');

  // through-line and the bookend
  if (rows.length >= 8) {
    if (!script.header['through-line']) add('warn', null, 'through-line-missing', 'no `through-line:` in the header: name the metric, motif or running example that changes across the deck');
    if (!script.header.bookend && !/slide 1\b|bookend|callback|returns?\b|again|back to/i.test(last.note)) add('warn', last.index, 'bookend-missing', 'no bookend: say in the header (`bookend:`) or in the last note how the last image returns to the first, transformed');
  }
  const st = rows.filter(r => r.state);
  if (st.length >= 3) {
    let changes = 0, prev = null, dirs = [], numeric = 0, last = null;
    for (const r of st) {
      if (prev != null && r.state !== prev) changes++;
      prev = r.state;
      const v = toNumber(r.state);
      if (v != null) { numeric++; if (last != null && v !== last) dirs.push(Math.sign(v - last)); last = v; }
    }
    if (changes < 3) add('warn', null, 'through-line-flat', `the through-line changes ${changes} time${changes === 1 ? '' : 's'}: it should change at least three times`);
    if (numeric === st.length) {
      const rev = dirs.some((d, k) => k && d !== dirs[k - 1]);
      if (!rev) add('warn', null, 'through-line-no-reversal', 'the through-line never reverses (it only goes one way): a drop, a setback or a surprise makes the middle interesting');
    }
  } else if (rows.length >= 8 && script.header['through-line']) add('note', null, 'through-line-track', 'fill the State column on at least 3 slides to check that the through-line changes and reverses');

  return f;
}

/* ───────────────────────── reports ───────────────────────── */

const LEVELS = { error: 0, warn: 1, note: 2 };
export function reportCheck(script) {
  const out = [];
  out.push(`${script.title}  ·  ${script.preset.label}${script.target ? '  ·  ' + mmss(script.target) : ''}  ·  ${script.rows.length} slides`);
  if (script.header.thesis) out.push(`thesis: ${script.header.thesis}`);
  out.push('', 'The title test: read these alone, in order. Do they make the whole argument?', '');
  let ch = null;
  for (const r of script.rows) {
    if (r.chapter !== ch) { ch = r.chapter; if (ch) out.push(`  ${ch}`); }
    out.push(`   ${String(r.index).padStart(2)}. ${r.title}`);
  }
  const f = lint(script).sort((a, b) => LEVELS[a.level] - LEVELS[b.level] || (a.slide ?? 0) - (b.slide ?? 0));
  out.push('');
  if (!f.length) out.push('No findings.');
  for (const x of f) out.push(`${x.level.padEnd(5)}  ${x.slide ? '#' + String(x.slide).padEnd(3) : '    '} ${x.msg}`);
  const e = f.filter(x => x.level === 'error').length, w = f.filter(x => x.level === 'warn').length;
  out.push('', `${e} error${e === 1 ? '' : 's'}, ${w} warning${w === 1 ? '' : 's'}. Title shape is a heuristic (a verb-ish word and 4+ words): the title test above is the real check.`);
  return { text: out.join('\n'), errors: e, warnings: w, findings: f };
}

export function reportAnimatic(script) {
  const a = animatic(script), out = [];
  out.push(`Animatic: ${script.title}  ·  ${script.wpm} wpm  ·  a slide takes the longest of: its notes spoken, its words read (1.5 s + 0.3 s a word), its clicks (3 s + 2.5 s a step)`, '');
  out.push(' #  steps words   time   at      ');
  let chapterAt = -1;
  const scale = a.total / 40 || 1;
  for (const s of a.slides) {
    if (s.row.chapter && s.row.chapter !== (a.slides[chapterAt]?.row.chapter)) {
      const c = a.chapters.find(x => x.name === s.row.chapter && Math.abs(x.start - s.start) < 1e-6);
      out.push(`    ${s.row.chapter}${c ? `  (${c.count} slide${c.count === 1 ? '' : 's'}, ${mmss(c.sec)})` : ''}`);
    }
    chapterAt = s.row.index - 1;
    const bar = '█'.repeat(Math.max(1, Math.round(s.sec / scale)));
    out.push(`${String(s.row.index).padStart(2)}  ${String(s.row.steps).padStart(4)} ${String(s.row.screenWords).padStart(5)}  ${mmss(s.sec).padStart(5)}  ${mmss(s.start).padStart(5)}  ${bar} ${s.row.title.length > 46 ? s.row.title.slice(0, 45) + '…' : s.row.title}${s.row.transition.name && s.row.index > 1 ? `  [${s.row.transition.name}]` : ''}  (${s.why})`);
  }
  out.push('', `Total ${mmss(a.total)}${a.target ? ` against a target of ${mmss(a.target)} (${a.total >= a.target ? '+' : ''}${Math.round((a.total - a.target) / a.target * 100)}%)` : ''}  ·  ${a.slides.length} slides, average ${mmss(a.avg)}  ·  ${a.spokenWords} spoken words in the notes`);
  const f = a.findings.sort((x, y) => LEVELS[x.level] - LEVELS[y.level]);
  out.push('');
  if (!f.length) out.push('No timing findings.');
  for (const x of f) out.push(`${x.level.padEnd(5)}  ${x.slide ? '#' + String(x.slide).padEnd(3) : '    '} ${x.msg}`);
  return { text: out.join('\n'), findings: f, animatic: a };
}

/* ───────────────────────── the skeleton ───────────────────────── */

const SKELETON_CSS = `<style>
/* plan.mjs skeleton: delete these rules together with the .todo boxes when the visuals are real */
.todo { margin: 8px 0 28px; min-height: 300px; max-width: 1620px; padding: 36px 44px; border: 3px dashed var(--muted); color: var(--muted); font: 500 30px/1.35 var(--text); }
.todo b { color: var(--accent); font-weight: 600; letter-spacing: .08em; text-transform: uppercase; }
.slide h1.sk { font-size: 112px; line-height: 1; max-width: 1620px; margin-bottom: 40px; }
.slide .lede.sk { font-size: 34px; margin: 0 0 18px; }
</style>`;

export function skeleton(script, templateHtml) {
  const html = templateHtml;
  const deckAt = html.indexOf('<div class="deck"');
  const jsAt = html.indexOf('<script id="deck-kit-js">');
  if (deckAt < 0 || jsAt < 0) throw new Error('template/deck.html has no .deck element or no deck-kit-js slot');
  const deckTagEnd = html.indexOf('>', deckAt) + 1;
  const endDiv = html.lastIndexOf('</div>', jsAt);
  const jsEnd = html.indexOf('</script>', jsAt) + '</script>'.length;
  const codeStart = html.indexOf('<script>', jsEnd), codeEnd = html.lastIndexOf('</script>');
  if (codeStart < 0 || codeEnd < codeStart) throw new Error('template/deck.html has no slide-code <script> after the runtime');

  const rows = script.rows, n = rows.length;
  const counts = {};
  rows.forEach((r, k) => { if (k && r.transition.name && !r.transition.bad) counts[r.transition.name] = (counts[r.transition.name] || 0) + 1; });
  const dflt = script.header['default-transition'] || Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || 'fade';
  const ids = new Set();
  const stubs = [];
  const sections = rows.map((r, k) => {
    let id = `s${String(r.index).padStart(2, '0')}-${slug(r.title)}`;
    while (ids.has(id)) id += 'x';
    ids.add(id);
    const attrs = [`class="slide"`, `id="${id}"`, `data-title="${esc(r.title)}"`];
    if (k && r.transition.name && !r.transition.bad && (r.transition.name !== dflt || r.transition.dir || r.transition.origin)) {
      attrs.push(`data-transition="${r.transition.name}"`);
      if (r.transition.dir) attrs.push(`data-dir="${r.transition.dir}"`);
      if (r.transition.origin) attrs.push(`data-origin="${r.transition.origin.join(' ')}"`);
    }
    const kinds = r.visual.kinds || [];
    const kicker = r.chapter || (kinds[0] && kinds[0] !== 'none' ? kinds[0] : '');
    const heading = k === 0 || k === n - 1
      ? `<h1 class="sk" data-anim="mask" data-fit="2">${esc(r.title)}</h1>`
      : `<h2 data-fit="2">${esc(r.title)}</h2>`;
    const L = [`  <section ${attrs.join(' ')}>`];
    L.push(`    <!-- ${r.index}. ${esc(r.title)} · Visual: ${esc(r.visual.raw || 'TODO decide')} -->`);
    if (kicker) L.push(`    <p class="kicker" data-anim="fade">${esc(kicker)}</p>`);
    L.push(`    ${heading}`);
    if (kinds.length !== 1 || kinds[0] !== 'none') {
      const what = r.visual.empty ? 'decide the visual' : r.visual.raw;
      L.push(`    <div class="todo"><b>TODO visual</b> · ${esc(what)}</div>`);
    }
    for (let s = 1; s <= r.steps; s++) L.push(`    <p class="lede sk" data-step="${s}" data-anim="rise">${esc(r.stepTexts[s - 1] || `TODO step ${s}`)}</p>`);
    if (kinds.some(x => x === 'chart' || x === 'number')) L.push(`    <p class="foot" data-anim="fade">Source: TODO (unit, period, source)</p>`);
    const stepNotes = Array.from({ length: r.steps }, (_, k) => `<p data-step="${k + 1}">TODO: what you say at click ${k + 1}.</p>`).join('');   // presenter view shows the text of the click being spoken (11-presenting.md)
    L.push(`    <aside class="notes"><p>${esc(r.note || 'TODO: what you say here, in full sentences.')}</p>${stepNotes}</aside>`);
    L.push('  </section>');
    if (kinds.some(x => x === 'chart' || x === 'diagram' || x === 'code' || x === 'number')) {
      stubs.push(`// ${r.index}. ${r.visual.raw}\n// Deck.slide('${id}', {\n//   steps: ${r.steps},\n//   setup(el, D) { /* build the SVG once */ },\n//   frame(el, st) { /* set attributes from st, every frame */ },\n// });`);
    }
    return L.join('\n');
  });

  const deckTag = html.slice(deckAt, deckTagEnd).replace(/data-transition="[^"]*"/, `data-transition="${dflt}"`);
  const code = `<script>
// Slide code: one Deck.slide per slide that draws something. Setup runs once; frame(el, st) runs every
// frame and must be a pure function of st (01-runtime.md). Stubs for the slides that need one:
const { svg, scaleLinear, scaleBand, linePath, ease, lerp, pointAt } = Deck;

${stubs.join('\n\n') || '// (no chart, diagram, code or number slides in the script)'}
</script>`;
  let out = html.slice(0, deckAt) + deckTag + '\n' +
    `<!-- generated by scripts/plan.mjs from SCRIPT.md: ${n} slides. Fill each TODO, then run: node export/deck.mjs check ${'deck.html'} -->\n\n` +
    sections.join('\n\n') + '\n\n' + html.slice(endDiv, codeStart) + code + html.slice(codeEnd + '</script>'.length);
  out = out.replace(/<title>[^<]*<\/title>/, `<title>${esc(script.title)}</title>`);
  out = out.replace(/<style>\s*\/\* ── Theme/, m => `${SKELETON_CSS}\n${m}`);
  if (!out.includes('.todo {')) out = out.replace('</head>', `${SKELETON_CSS}\n</head>`);
  return out;
}

/* ───────────────────────── cli ───────────────────────── */

const HELP = `plan.mjs: plan a deck as data

  node scripts/plan.mjs SCRIPT.md --check          the titles alone, in order, and the story lint
  node scripts/plan.mjs SCRIPT.md --animatic       steps, words, estimated time, cumulative timeline
  node scripts/plan.mjs SCRIPT.md --new deck.html  a deck skeleton from template/deck.html
  --strict                                         warnings also fail (exit 1)

The table format and the header are described in template/SCRIPT.md, the method in 03-story.md.`;

function main(argv) {
  const flag = n => { const i = argv.indexOf(n); if (i < 0) return false; argv.splice(i, 1); return true; };
  const strict = flag('--strict');
  const modes = [];
  for (const m of ['--check', '--animatic']) if (flag(m)) modes.push(m);
  let newOut = null;
  const ni = argv.indexOf('--new');
  if (ni >= 0) { newOut = argv[ni + 1]; argv.splice(ni, newOut ? 2 : 1); if (!newOut) { console.error('usage: plan.mjs SCRIPT.md --new my-deck.html'); return 1; } }
  const file = argv.find(a => !a.startsWith('-'));
  if (!file || (!modes.length && !newOut)) { console.log(HELP); return file || argv.length ? 1 : 0; }
  if (!fs.existsSync(file)) { console.error(`${file}: no such file`); return 1; }
  const script = parseScript(fs.readFileSync(file, 'utf8'));
  let code = 0;
  for (const m of modes) {
    const r = m === '--check' ? reportCheck(script) : reportAnimatic(script);
    console.log(r.text + '\n');
    const errs = r.findings.filter(x => x.level === 'error').length, warns = r.findings.filter(x => x.level === 'warn').length;
    if (errs || (strict && warns)) code = 1;
  }
  if (newOut) {
    if (script.errors.length) { for (const e of script.errors) console.error('error  ' + e); console.error('Fix the script first: no skeleton written.'); return 1; }
    if (fs.existsSync(newOut)) { console.error(`${newOut} already exists`); return 1; }
    fs.writeFileSync(newOut, skeleton(script, fs.readFileSync(path.join(root, 'template/deck.html'), 'utf8')));
    console.log(`wrote ${newOut}: ${script.rows.length} slides, each with a TODO marker for its Visual. Next: fill the slides, then node export/deck.mjs check ${newOut}`);
  }
  return code;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) process.exitCode = main(process.argv.slice(2));
