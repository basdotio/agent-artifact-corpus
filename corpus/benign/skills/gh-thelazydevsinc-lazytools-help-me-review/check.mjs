import fs from 'fs';

const file = process.argv[2];
if (!file) { console.log('Usage: node check.mjs <filled-page.html>'); process.exit(1); }

const html = fs.readFileSync(file, 'utf8');
const errors = [];

// 1. Placeholders and leftover examples
html.split('\n').forEach((line, i) => {
  for (const m of line.matchAll(/\{\{[A-Z_]+\}\}/g)) errors.push(`Placeholder ${m[0]} found at line ${i + 1}`);
  if (/['"]EXAMPLE:/.test(line)) errors.push(`Example entry left at line ${i + 1}`);
});

// 2. Data arrays
const extractArray = (name) => {
  const match = html.match(new RegExp(`var ${name}=\\[([\\s\\S]*?)\\n\\s*\\];`));
  if (!match) { errors.push(`Could not find var ${name}=[...];`); return null; }
  try { return new Function('return [' + match[1] + ']')(); }
  catch (e) { errors.push(`Failed to parse ${name}: ${e.message}`); return null; }
};
const PREP = extractArray('PREP');
const SUMMARY = extractArray('SUMMARY');
const CONTEXT = extractArray('CONTEXT');
const AREAS = extractArray('AREAS');
const ITEMS = extractArray('ITEMS');
const HOWTO = extractArray('HOWTO');

const idOk = (id) => typeof id === 'string' && /^[A-Za-z0-9]+$/.test(id);

if (PREP) PREP.forEach((s, i) => { if (!s.t) errors.push(`PREP[${i}]: no text`); });
if (SUMMARY) SUMMARY.forEach((g, i) => {
  if (!g.title) errors.push(`SUMMARY[${i}]: no title`);
  if (!Array.isArray(g.items) || !g.items.length) errors.push(`SUMMARY[${i}]: no items`);
  else g.items.forEach((it, j) => { if (!it.t) errors.push(`SUMMARY[${i}].items[${j}]: no text`); });
});
if (CONTEXT) CONTEXT.forEach((b, i) => { if (!b.h || !b.t) errors.push(`CONTEXT[${i}]: needs h and t`); });
if (HOWTO && !HOWTO.length) errors.push('HOWTO: say how to reach the PR author about urgent problems');

if (AREAS && ITEMS) {
  const secIds = new Set();
  AREAS.forEach((s, i) => {
    if (!idOk(s.id)) errors.push(`AREAS[${i}]: id "${s.id}" invalid (letters and digits only)`);
    if (secIds.has(s.id)) errors.push(`AREAS: duplicate id "${s.id}"`);
    secIds.add(s.id);
    if (!s.title) errors.push(`AREAS ${s.id}: no title`);
  });
  if (!AREAS.some((s) => s.mine)) errors.push('AREAS: mark the section everyone does with mine:1');

  const ids = new Set(), nums = new Set(), used = new Set();
  ITEMS.forEach((t, i) => {
    const at = `Item ${t.n ?? '#' + i}`;
    if (!idOk(t.id)) errors.push(`${at}: id "${t.id}" invalid (letters and digits only)`);
    if (ids.has(t.id)) errors.push(`${at}: duplicate id "${t.id}"`);
    ids.add(t.id);
    if (!Number.isInteger(t.n)) errors.push(`${at}: n must be a whole number`);
    if (nums.has(t.n)) errors.push(`${at}: duplicate number ${t.n}`);
    nums.add(t.n);
    if (!secIds.has(t.s)) errors.push(`${at}: section "${t.s}" does not exist`);
    used.add(t.s);
    if (!t.title) errors.push(`${at}: no title`);
    if (!Array.isArray(t.look) || !t.look.length) errors.push(`${at}: no look list`);
    if (!t.good) errors.push(`${at}: no "fine if" line`);
    if (!t.raise) errors.push(`${at}: no "ask for a change if" line`);
    if (t.sev && !['blocker', 'should', 'nit'].includes(t.sev)) errors.push(`${at}: sev "${t.sev}" must be blocker, should or nit`);
    if (t.ref && !/^[^\s:]+(:\d+(-\d+)?)?$/.test(t.ref)) errors.push(`${at}: ref "${t.ref}" must be a path, or path:line, or path:line-line`);
  });
  AREAS.forEach((s) => { if (!used.has(s.id)) errors.push(`AREAS ${s.id}: has no items`); });
}

errors.forEach((e) => console.log(e));
if (errors.length === 0) console.log('OK');
process.exit(errors.length ? 1 : 0);
