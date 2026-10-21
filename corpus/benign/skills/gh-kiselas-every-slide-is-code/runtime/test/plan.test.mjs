import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import * as Plan from '../../scripts/plan.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const read = f => fs.readFileSync(path.join(root, f), 'utf8');
const TEMPLATE = read('template/SCRIPT.md');

// A script from rows given as [chapter, title, steps, visual, transition, note].
function script(rows, header = {}, extra = '') {
  const h = { title: 'T', type: 'pitch', length: '8 min', thesis: 'We win.', ...header };
  const head = '---\n' + Object.entries(h).filter(([, v]) => v != null).map(([k, v]) => `${k}: ${v}`).join('\n') + '\n---\n\n';
  const body = rows.map((r, i) => `| ${i + 1} | ${r.join(' | ')} |`).join('\n');
  return Plan.parseScript(head + `| # | Chapter | Title | Steps | Visual | Transition | Note |\n|---|---|---|---|---|---|---|\n${body}\n` + extra);
}
const codes = s => Plan.lint(s).map(f => f.code);
const has = (s, code) => Plan.lint(s).filter(f => f.code === code);

// A pitch that should raise no warnings: the baseline every lint test bends.
const GOOD = [
  ['Problem', 'Restaurants throw away a tenth of the food they buy', 1, 'number', '-', 'x'],
  ['Problem', 'Most of it is binned before it reaches a plate', 1, 'chart: bars', 'camera', 'x'],
  ['Insight', 'Waste is a forecasting problem, not a discipline problem', 0, 'none', 'tear', 'x'],
  ['Product', 'A scale that knows what it is weighing', 2, 'diagram: blueprint', 'morph', 'x'],
  ['Why now', 'Cheap load cells made this a device kitchens can afford', 1, 'chart: cost', 'camera', 'x'],
  ['Traction', 'Pilot kitchens cut waste by 41 percent in six months', 2, 'chart: waterfall', 'camera', 'x'],
  ['Ask', 'We are raising $4M to reach a thousand kitchens', 1, 'chart: use of funds', 'tear', 'x'],
];

test('the shipped template parses and lints clean', () => {
  const s = Plan.parseScript(TEMPLATE);
  assert.deepEqual(s.errors, []);
  assert.equal(s.type, 'pitch');
  assert.equal(s.rows.length, 12);
  assert.equal(s.target, 480);
  assert.equal(s.wpm, 140);
  const f = Plan.lint(s).filter(x => x.level !== 'note');
  assert.deepEqual(f, [], f.map(x => x.msg).join('\n'));
  assert.equal(s.rows[1].chapter, 'I · Problem', 'an empty Chapter cell continues the chapter above');
  assert.equal(s.rows[5].chapter, 'III · Product');
  assert.equal(s.rows[5].steps, 3);
  assert.equal(s.rows[1].transition.name, 'camera');
});

test('durations, steps, visuals and transitions parse', () => {
  assert.equal(Plan.parseDuration('20 min'), 1200);
  assert.equal(Plan.parseDuration('90 s'), 90);
  assert.equal(Plan.parseDuration('1h'), 3600);
  assert.equal(Plan.parseDuration('1:30'), 90);
  assert.equal(Plan.parseDuration('8'), 480);
  assert.equal(Plan.parseDuration('soon'), null);

  assert.deepEqual(Plan.parseSteps('3'), { count: 3, texts: [] });
  assert.deepEqual(Plan.parseSteps('-'), { count: 0, texts: [] });
  assert.deepEqual(Plan.parseSteps('1: bars turn red; 2. a bracket'), { count: 2, texts: ['bars turn red', 'a bracket'] });

  const v = Plan.parseVisual('chart: waterfall, one bar per click');
  assert.equal(v.charts, 1); assert.deepEqual(v.kinds, ['chart']); assert.match(v.desc, /one bar per click/);
  assert.equal(Plan.parseVisual('2 charts').charts, 2);
  assert.equal(Plan.parseVisual('chart + diagram').charts, 1);
  assert.deepEqual(Plan.parseVisual('chart + diagram').kinds, ['chart', 'diagram']);
  assert.equal(Plan.parseVisual('two bar charts').charts, 2);
  assert.deepEqual(Plan.parseVisual('none').kinds, ['none']);
  assert.equal(Plan.parseVisual('').empty, true);
  assert.deepEqual(Plan.parseVisual('a receipt printer, drawn').kinds, ['other']);
  assert.deepEqual(Plan.parseVisual('code: 12 lines of Rust').kinds, ['code']);

  assert.equal(Plan.parseTransition('-').name, null);
  assert.deepEqual(Plan.parseTransition('push:left'), { raw: 'push:left', name: 'push', dir: 'left', origin: null, bad: false });
  assert.deepEqual(Plan.parseTransition('zoom@960,540').origin, [960, 540]);
  assert.equal(Plan.parseTransition('sparkle').bad, true);
  for (const t of Plan.TRANSITIONS) assert.equal(Plan.parseTransition(t).bad, false, t);
});

test('every transition the parser knows exists in the runtime', () => {
  const js = read('runtime/deck.js');
  const defined = [...js.matchAll(/^transition\('([a-z]+)'/gm)].map(m => m[1]).sort();
  assert.deepEqual([...Plan.TRANSITIONS].sort(), defined);
});

test('the verb heuristic separates claims from topics', () => {
  for (const t of ['Restaurants throw away a tenth of the food they buy', 'Costs flattened after the switch', 'Every request passes one gateway, so we can meter it',
    'Revenue beat plan by 8%; margin missed by 2 points', 'The only tool that weighs waste and changes the prep', 'A scale that knows what it is weighing',
    'Room to grow: 1.1 million kitchens', 'Weigh it. Waste less.', 'Raising $4M', 'Most of it is binned before it reaches a plate']) assert.ok(Plan.hasVerb(t), t);
  for (const t of ['Market', 'Team', 'Q3 results', 'Architecture', 'Three steps, one loop', 'Competition overview']) assert.ok(!Plan.hasVerb(t), t);
});

test('lint: topic and short titles, duplicates, long titles', () => {
  const rows = GOOD.map(r => r.slice());
  rows[2][1] = 'Insight'; rows[4][1] = 'Why now'; rows[3][1] = rows[1][1]; rows[1][1] = 'Most of it is binned before it reaches a plate';
  const s = script(rows);
  const topics = has(s, 'title-topic').map(f => f.slide);
  assert.deepEqual(topics, [3, 5]);
  assert.equal(has(s, 'title-dup').length, 1);
  rows[0][1] = 'word '.repeat(20).trim();
  assert.equal(has(script(rows), 'title-long').length, 1);
  rows[0][1] = 'Sales grew';
  assert.equal(has(script(rows), 'title-short')[0].slide, 1, 'a 2-word claim with a verb is short, not a topic');
});

test('lint: more than three transition types, unknown transitions', () => {
  const rows = GOOD.map(r => r.slice());
  assert.equal(has(script(rows), 'transitions').length, 0);
  rows[1][4] = 'zoom'; rows[2][4] = 'dip';       // camera, tear, morph, zoom, dip
  const f = has(script(rows), 'transitions');
  assert.equal(f.length, 1); assert.match(f[0].msg, /5 transition types/);
  rows[1][4] = 'sparkle';
  const bad = has(script(rows), 'transition-unknown');
  assert.equal(bad[0].level, 'error'); assert.equal(bad[0].slide, 2);
  // the first slide's transition never plays and is not counted
  const r2 = GOOD.map(r => r.slice()); r2[0][4] = 'cube';
  assert.equal(has(script(r2), 'transitions').length, 0);
});

test('lint: the closing ask, by type', () => {
  const rows = GOOD.map(r => r.slice());
  assert.equal(has(script(rows), 'no-close').length, 0);
  rows[6][1] = 'Thank you'; assert.match(has(script(rows), 'no-close')[0].msg, /thanks or questions/);
  rows[6][1] = 'Questions?'; assert.equal(has(script(rows), 'no-close').length, 1);
  rows[6][1] = 'Our market is large and growing quickly'; rows[6][0] = 'Market';
  assert.equal(has(script(rows), 'no-close').length, 1);
  // a launch ends on availability, a tech talk on how to adopt: the same words do not pass for both
  const launch = script([['Before', 'Kitchens weigh nothing today', 0, 'none', '-', 'x'], ['Availability', 'Tare ships in November from $249', 0, 'number', 'camera', 'x']], { type: 'product-launch' });
  assert.equal(has(launch, 'no-close').length, 0);
  const tech = script([['Problem', 'Builds take forty minutes', 0, 'none', '-', 'x'], ['Adopt', 'Try it on one repo this week: npm install cachey', 0, 'code', 'camera', 'x']], { type: 'tech-talk' });
  assert.equal(has(tech, 'no-close').length, 0);
  const tech2 = script([['Problem', 'Builds take forty minutes', 0, 'none', '-', 'x'], ['Adopt', 'Caching is a good idea in general', 0, 'code', 'camera', 'x']], { type: 'tech-talk' });
  assert.equal(has(tech2, 'no-close').length, 1);
});

test('lint: charts, missing visuals, text runs, steps, words', () => {
  const rows = GOOD.map(r => r.slice());
  rows[1][3] = '2 charts'; rows[2][3] = ''; rows[3][2] = 7;
  rows[4][2] = '1: ' + 'word '.repeat(45).trim();
  const s = script(rows);
  assert.equal(has(s, 'multi-chart')[0].slide, 2);
  assert.equal(has(s, 'no-visual')[0].slide, 3);
  assert.equal(has(s, 'steps-many')[0].slide, 4);
  assert.equal(has(s, 'words-screen')[0].slide, 5);
  const runs = GOOD.map(r => r.slice()); for (const k of [0, 1, 2]) runs[k][3] = 'none';
  assert.equal(has(script(runs), 'text-run').length, 1);
});

test('lint: the spine of each type', () => {
  assert.equal(has(script(GOOD), 'spine-missing').length, 0);
  const rows = GOOD.filter(r => r[0] !== 'Traction' && r[0] !== 'Why now');
  const missing = has(script(rows), 'spine-missing').map(f => f.msg);
  assert.equal(missing.length, 2);
  assert.ok(missing.some(m => /why now/.test(m)) && missing.some(m => /traction/.test(m)));
  const noChapters = GOOD.map(r => ['', ...r.slice(1)]);
  assert.equal(has(script(noChapters), 'spine').length, 1);
  // a technical talk needs a chart or number in the proof chapter and a diagram or code in the mechanism chapter
  const t = script([['The problem', 'Builds take forty minutes on every push', 0, 'none', '-', 'x'], ['What failed', 'Caching by file made it slower', 0, 'none', 'camera', 'x'],
    ['Mechanism', 'Content hashes decide what to rebuild', 0, 'none', 'camera', 'x'], ['Benchmark', 'Builds now finish in four minutes', 0, 'none', 'tear', 'x'],
    ['How to adopt', 'Try it on one repository this week', 0, 'code', 'tear', 'x']], { type: 'tech-talk' });
  assert.equal(has(t, 'spine-visual').length, 2);
  assert.equal(has(t, 'spine-missing').length, 0);
});

test('lint: header checks, length, word budget, through-line and bookend', () => {
  assert.equal(has(script(GOOD, { thesis: null }), 'thesis').length, 1);
  assert.equal(has(script(GOOD, { type: 'nonsense' }), 'parse')[0].level, 'error');
  assert.equal(has(script(GOOD, { length: null }), 'no-length').length, 1);
  assert.equal(has(script(GOOD, { length: 'soon' }), 'parse').length, 1);
  // 7 slides in 30 minutes: far below the band of a pitch
  assert.equal(has(script(GOOD, { length: '30 min' }), 'slide-count').length, 1);
  assert.equal(has(script(GOOD, { length: '1 min' }), 'slide-count').length, 1);
  // notes: 120 words per slide, 840 in all, against the 560 that 4 minutes fit at 140 wpm
  const long = GOOD.map(r => [...r.slice(0, 5), 'word '.repeat(120).trim()]);
  const f = has(script(long, { length: '4 min', rate: '140 wpm' }), 'word-budget');
  assert.equal(f.length, 1); assert.match(f[0].msg, /cut \d+ words/);

  const eight = [...GOOD, ['Ask', 'Join us as we raise the round', 0, 'none', 'camera', 'x']];
  assert.equal(has(script(eight), 'through-line-missing').length, 1);
  assert.equal(has(script(eight, { 'through-line': 'waste in kg', bookend: 'the read-out' }), 'through-line-missing').length, 0);
  assert.equal(has(script(eight), 'bookend-missing').length, 1);
  assert.equal(has(script(eight, { bookend: 'the read-out' }), 'bookend-missing').length, 0);
});

test('lint: the through-line column must change and reverse', () => {
  const withState = states => Plan.parseScript(
    '---\ntitle: T\ntype: pitch\nlength: 8 min\nthesis: x\n---\n| # | Chapter | Title | Steps | Visual | Transition | Through-line | Note |\n|---|---|---|---|---|---|---|---|\n' +
    states.map((v, i) => `| ${i + 1} | Ch | Slide number ${i + 1} grows the score | 0 | none | - | ${v} | x |`).join('\n'));
  assert.equal(has(withState(['5', '5', '5', '4']), 'through-line-flat').length, 1);
  assert.equal(has(withState(['9', '7', '5', '3', '1']), 'through-line-no-reversal').length, 1, 'only ever falling: no reversal');
  assert.equal(has(withState(['9', '5', '7', '2', '1']), 'through-line-no-reversal').length, 0);
  assert.equal(has(withState(['9', '5', '7', '2', '1']), 'through-line-flat').length, 0);
  // a motif that is not a number is checked for change only
  assert.equal(has(withState(['match', 'torch', 'reactor', 'sun']), 'through-line-no-reversal').length, 0);
  assert.equal(has(withState(['match', 'match', 'match']), 'through-line-flat').length, 1);
});

test('a script with no header, no table or bad rows reports errors', () => {
  const none = Plan.parseScript('# just prose\n');
  assert.ok(none.errors.length >= 2);
  const bad = Plan.parseScript('---\ntype: pitch\n---\n| # | Title |\n|---|---|\n| one | A claim that has some words |\n| 2 |  |\n');
  assert.equal(bad.errors.filter(e => /not a slide number/.test(e)).length, 1);
  assert.equal(bad.errors.filter(e => /empty title/.test(e)).length, 1);
  assert.ok(Plan.lint(bad).some(f => f.level === 'error'));
});

test('animatic: per-slide time, cumulative timeline, chapters, overrides', () => {
  const rows = GOOD.map(r => r.slice());
  rows[0][5] = 'word '.repeat(70).trim();                       // 70 words at 140 wpm = 30 s
  const s = script(rows, { length: '4 min', rate: '140 wpm' });
  const a = Plan.animatic(s);
  assert.equal(a.slides.length, 7);
  assert.ok(Math.abs(a.slides[0].sec - 30) < 1e-9); assert.equal(a.slides[0].why, 'speech');
  assert.equal(a.slides[0].start, 0); assert.ok(Math.abs(a.slides[1].start - 30) < 1e-9);
  assert.ok(Math.abs(a.total - a.slides.reduce((x, y) => x + y.sec, 0)) < 1e-9);
  assert.equal(a.slides[3].why, 'steps', 'a 2-step slide with a stub note is paced by its clicks: 3 + 2 x 2.5 s');
  assert.equal(a.slides[3].sec, 8);
  assert.deepEqual(a.chapters.map(c => c.name), ['Problem', 'Insight', 'Product', 'Why now', 'Traction', 'Ask']);
  assert.equal(a.chapters[0].count, 2);
  const set = script([['A', 'This slide has a fixed time of one minute', 1, 'none', '-', 'x'], ['A', 'Sales grew sharply in the last quarter', 0, 'none', 'camera', 'x']]);
  set.rows[0].sec = 60;
  assert.equal(Plan.animatic(set).slides[0].sec, 60);
  assert.equal(Plan.animatic(set).slides[0].why, 'set');
});

test('animatic: off-target totals warn, stub notes downgrade to a note', () => {
  const full = GOOD.map(r => [...r.slice(0, 5), 'word '.repeat(90).trim()]);        // 7 x 90 words at 140 wpm = 270 s
  const on = Plan.animatic(script(full, { length: '4.5 min', rate: '140 wpm' }));
  assert.ok(on.findings.every(f => f.code !== 'length'), 'within 10%');
  const over = Plan.animatic(script(full, { length: '3 min', rate: '140 wpm' })).findings.find(f => f.code === 'length');
  assert.equal(over.level, 'warn'); assert.match(over.msg, /cut about \d+ slide/);
  const under = Plan.animatic(script(full, { length: '7 min', rate: '140 wpm' })).findings.find(f => f.code === 'length');
  assert.equal(under.level, 'warn'); assert.match(under.msg, /add about \d+ slide/);
  const stub = Plan.animatic(script(GOOD, { length: '8 min' })).findings.find(f => f.code === 'length');
  assert.equal(stub.level, 'note'); assert.match(stub.msg, /floor/);
  assert.ok(Plan.animatic(script(GOOD, { length: null })).findings.every(f => f.level !== 'warn'));
});

test('reports print the titles alone, in order, and the timeline', () => {
  const s = Plan.parseScript(TEMPLATE);
  const c = Plan.reportCheck(s);
  const titles = c.text.split('\n').filter(l => /^\s+\d+\. /.test(l)).map(l => l.replace(/^\s+\d+\. /, ''));
  assert.deepEqual(titles, s.rows.map(r => r.title));
  assert.equal(c.errors, 0);
  const a = Plan.reportAnimatic(s).text;
  assert.match(a, /Total \d+:\d\d against a target of 8:00/);
  assert.equal(a.split('\n').filter(l => /█/.test(l)).length, 12);
});

test('skeleton: one section per row, in the template markup, with TODO markers', () => {
  const s = Plan.parseScript(TEMPLATE), tpl = read('template/deck.html');
  const html = Plan.skeleton(s, tpl);
  const sections = html.match(/<section class="slide"[^>]*>/g);
  assert.equal(sections.length, 12);
  assert.equal((html.match(/<aside class="notes">/g) || []).length, 12);
  assert.equal((html.match(/class="todo"/g) || []).length, 11, 'every slide with a Visual other than none');
  const ids = sections.map(x => x.match(/id="([^"]+)"/)[1]);
  assert.equal(new Set(ids).size, 12);
  assert.ok(ids.every(x => /^s\d\d-[a-z0-9-]+$/.test(x)), ids.join());
  assert.match(sections[1], /data-title="A tenth of what a kitchen buys goes in the bin"/);
  assert.doesNotMatch(sections[1], /data-transition/, 'the default transition (camera) is on .deck');
  assert.match(sections[4], /data-transition="tear"/);
  assert.match(sections[5], /data-transition="morph"/);
  assert.match(html, /<div class="deck" data-transition="camera"/);
  assert.equal((html.match(/data-step="\d+"/g) || []).length, 2 * s.rows.reduce((a, r) => a + r.steps, 0), 'each click is a build on the slide and a note stub for the presenter view');
  assert.match(html, /<h1 class="sk"[^>]*>Restaurants/); assert.match(html, /<h1 class="sk"[^>]*>We are raising/);
  assert.match(html, /<title>Tare, a seed pitch/);
  assert.match(html, /Source: TODO/);
  assert.match(html, /\/\/ Deck\.slide\('s02-/);
  // the runtime is untouched and the template's own demo slides are gone
  const jsOf = h => h.slice(h.indexOf('<script id="deck-kit-js">'), h.indexOf('</script>', h.indexOf('<script id="deck-kit-js">')));
  assert.equal(jsOf(html), jsOf(tpl));
  assert.doesNotMatch(html, /id="morph-a"/);
  assert.equal((html.match(/<script>/g) || []).length, (tpl.match(/<script>/g) || []).length);
  assert.ok(html.indexOf('.todo {') < html.indexOf('</head>'));
});

test('skeleton: text is escaped, step texts and directions carry over', () => {
  const s = Plan.parseScript('---\ntitle: A & B <deck>\ntype: pitch\nlength: 1 min\n---\n| # | Title | Steps | Visual | Transition |\n|---|---|---|---|---|\n' +
    '| 1 | Costs <fell> "fast" after the switch | 2 | chart | - |\n| 2 | We ask you to join us | one; two | none | push:up |\n| 3 | Sources beat opinions when we decide | 0 | | zoom@960,540 |\n');
  const html = Plan.skeleton(s, read('template/deck.html'));
  assert.match(html, /<title>A &amp; B &lt;deck&gt;<\/title>/);
  assert.match(html, /Costs &lt;fell&gt; &quot;fast&quot; after the switch/);
  assert.match(html, /data-step="1"[^>]*>one</); assert.match(html, /data-step="2"[^>]*>two</);
  assert.match(html, /data-transition="push" data-dir="up"/);
  assert.match(html, /data-transition="zoom" data-origin="960 540"/);
  assert.match(html, /TODO visual<\/b> · decide the visual/, 'an empty Visual is a visible decision to make');
});

test('cli: --check, --animatic, --new, exit codes', () => {
  const run = (...args) => spawnSync(process.execPath, [path.join(root, 'scripts/plan.mjs'), ...args], { encoding: 'utf8' });
  const tpl = path.join(root, 'template/SCRIPT.md');
  const c = run(tpl, '--check');
  assert.equal(c.status, 0, c.stderr); assert.match(c.stdout, /The title test/);
  assert.equal(run(tpl, '--animatic').status, 0);
  assert.equal(run().status, 0, 'help');
  assert.equal(run('nope.md', '--check').status, 1);
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'plan-'));
  try {
    const out = path.join(dir, 'deck.html');
    const n = run(tpl, '--new', out);
    assert.equal(n.status, 0, n.stderr); assert.ok(fs.existsSync(out));
    assert.equal(run(tpl, '--new', out).status, 1, 'never overwrites a deck');
    const bad = path.join(dir, 'bad.md'); fs.writeFileSync(bad, '# nothing here\n');
    assert.equal(run(bad, '--check').status, 1);
    assert.equal(run(bad, '--new', path.join(dir, 'x.html')).status, 1);
    assert.ok(!fs.existsSync(path.join(dir, 'x.html')));
    // --strict: a warning fails
    const warn = path.join(dir, 'warn.md');
    fs.writeFileSync(warn, TEMPLATE.replace('| I · Problem | Restaurants throw away a tenth of the food they buy', '| I · Problem | Market'));
    assert.equal(run(warn, '--check').status, 0);
    assert.equal(run(warn, '--check', '--strict').status, 1);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});
